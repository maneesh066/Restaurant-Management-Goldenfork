from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import MenuItem, Order, OrderItem, Payment, Category, Expense, Stock, RestaurantStatus, Complaint, Review
from django.db.models import Q
import random
import os
from django.core.mail import send_mail
from django.conf import settings
import threading
from django.utils import timezone
from datetime import timedelta

# HOME
def home(request):
    request.session.pop('manager', None)
    status = RestaurantStatus.objects.first()
    complaint_ids = request.session.get('complaint_ids', [])
    user_complaints = Complaint.objects.filter(id__in=complaint_ids).order_by('-created_at')
    return render(request, 'home.html', {'status': status, 'user_complaints': user_complaints})

# MENU PAGE
def menu(request):
    items = MenuItem.objects.filter(is_available=True)
    # Only show categories that have at least one available item
    categories = Category.objects.filter(menu_items__in=items).distinct()
    status = RestaurantStatus.objects.first()
    return render(request, 'menu.html', {'items': items, 'categories': categories, 'status': status})

# ADD TO CART
def add_to_cart(request, item_id):
    cart = request.session.get('cart', {})
    if str(item_id) in cart:
        cart[str(item_id)] += 1
    else:
        cart[str(item_id)] = 1
    request.session['cart'] = cart
    return redirect('menu')

# UPDATE CART API
def update_cart(request):
    if request.method == 'POST':
        try:
            item_id = request.POST.get('item_id')
            action = request.POST.get('action')
            cart = request.session.get('cart', {})
            
            # Ensure all keys are strings for consistency
            cart = {str(k): int(v) for k, v in cart.items()}
            
            if not item_id:
                return JsonResponse({'status': 'error', 'message': 'Invalid Item ID'})
                
            item = get_object_or_404(MenuItem, id=item_id)
            item_id_str = str(item.id)
            
            force = request.POST.get('force') == 'true'
            
            if action == 'add':
                current_qty = cart.get(item_id_str, 0)
                if current_qty + 1 > item.stock_quantity and not force:
                    return JsonResponse({'status': 'stock_exceeded', 'message': 'You ordered excess limit of stocks if you want to order these quantity press continue', 'item_id': item_id})
                cart[item_id_str] = current_qty + 1
            elif action == 'remove':
                if item_id_str in cart:
                    cart[item_id_str] -= 1
                    if cart[item_id_str] <= 0:
                        del cart[item_id_str]
            elif action == 'set':
                try:
                    new_qty = int(request.POST.get('quantity', 0))
                except (ValueError, TypeError):
                    new_qty = 0
                if new_qty > item.stock_quantity and not force:
                    return JsonResponse({'status': 'stock_exceeded', 'message': 'You ordered excess limit of stocks if you want to order these quantity press continue', 'item_id': item_id})
                if new_qty > 0:
                    cart[item_id_str] = new_qty
                elif item_id_str in cart:
                    del cart[item_id_str]
            
            request.session['cart'] = cart
            request.session.modified = True
            return JsonResponse({'status': 'success', 'cart': cart})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'failed'})

# VIEW CART
def view_cart(request):
    cart = request.session.get('cart', {})
    items = []
    total = 0

    for item_id, quantity in cart.items():
        try:
            item = MenuItem.objects.get(id=item_id)
            subtotal = item.price * quantity
            total += subtotal
            items.append({
                'item': item,
                'quantity': quantity,
                'subtotal': subtotal
            })
        except MenuItem.DoesNotExist:
            continue

    gst = total * 0.05
    grand_total = total + gst
    status = RestaurantStatus.objects.first()

    return render(request, 'cart.html', {
        'items': items,
        'total': total,
        'gst': gst,
        'grand_total': grand_total,
        'status': status
    })

# REMOVE ITEM
def remove_from_cart(request, item_id):
    cart = request.session.get('cart', {})
    if str(item_id) in cart:
        del cart[str(item_id)]
    request.session['cart'] = cart
    return redirect('cart')

# PLACE ORDER
def place_order(request):
    cart = request.session.get('cart', {})
    if not cart:
        return redirect('cart')
        
    updating_order_id = request.session.get('updating_order_id')
    
    is_excess = False
    for item_id, quantity in cart.items():
        try:
            item = MenuItem.objects.get(id=item_id)
            if quantity > item.stock_quantity:
                is_excess = True
                break
        except MenuItem.DoesNotExist:
            continue

    if updating_order_id:
        order = get_object_or_404(Order, id=updating_order_id)
        OrderItem.objects.filter(order=order).delete()
        order.is_updated = True
    else:
        order = Order.objects.create(token_number=0)
        order.token_number = order.id
    
    order.is_excess_stock = is_excess
    if is_excess:
        order.kitchen_acceptance_status = 'Pending'
        order.excess_order_expiry = timezone.now() + timedelta(minutes=1)
    else:
        order.kitchen_acceptance_status = 'Accepted'
        order.excess_order_expiry = None
    
    total = 0
    for item_id, quantity in cart.items():
        try:
            item = MenuItem.objects.get(id=item_id)
            subtotal = item.price * quantity
            total += subtotal
            OrderItem.objects.create(
                order=order,
                item=item,
                quantity=quantity
            )
        except MenuItem.DoesNotExist:
            continue

    order.total_amount = total + (total * 0.05)
    order.save()

    # clear cart and updating flag
    request.session['cart'] = {}
    request.session.pop('updating_order_id', None)
    
    # store orders in session list
    order_ids = request.session.get('order_ids', [])
    if order.id not in order_ids:
        order_ids.append(order.id)
    request.session['order_ids'] = order_ids
    request.session['current_order_id'] = order.id

    return redirect('order_status')

# KITCHEN VIEW
def kitchen(request):
    if not request.session.get('manager'):
        return redirect('manager_login')
    
    # Grouping orders for the new 3-section UI
    new_orders = Order.objects.filter(status='Pending', is_served=False).exclude(status='Cancelled').order_by('-created_at')
    
    # In Progress includes Cooking and Ready (but not served)
    in_progress = Order.objects.filter(status__in=['Cooking', 'Ready'], is_served=False).exclude(status='Cancelled').order_by('-created_at')
    
    # Served Orders
    served_orders = Order.objects.filter(is_served=True).exclude(status='Cancelled').order_by('-created_at')
    
    menu_items = MenuItem.objects.all()
    
    context = {
        'new_orders': new_orders,
        'in_progress': in_progress,
        'served_orders': served_orders,
        'menu_items': menu_items,
        'total_served': served_orders.count()
    }
    return render(request, 'kitchen.html', context)

def update_stock(request, item_id):
    if not request.session.get('manager'):
        return redirect('manager_login')
    item = get_object_or_404(MenuItem, id=item_id)
    if request.method == 'POST':
        stock = request.POST.get('stock')
        if stock is not None:
            item.stock_quantity = int(stock)
            item.save()
    return redirect('kitchen')

def submit_complaint(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        description = request.POST.get('description')
        image = request.FILES.get('image')

        if name and email and phone and description:
            otp = str(random.randint(100000, 999999))
            complaint = Complaint.objects.create(
                name=name, email=email, phone=phone, 
                address=address, description=description, 
                image=image, is_verified=True
            )
            
            # Store in session
            complaint_ids = request.session.get('complaint_ids', [])
            complaint_ids.append(complaint.id)
            request.session['complaint_ids'] = complaint_ids

            return JsonResponse({'status': 'success', 'message': 'Your complaint successfully registered and the response sents your mail'})
    return JsonResponse({'status': 'failed', 'message': 'Missing mandatory fields.'})

def verify_complaint_otp(request):
    if request.method == 'POST':
        complaint_id = request.POST.get('complaint_id')
        otp = request.POST.get('otp')
        complaint = get_object_or_404(Complaint, id=complaint_id)
        
        if complaint.otp == otp:
            complaint.is_verified = True
            complaint.save()
            
            # Store in session
            complaint_ids = request.session.get('complaint_ids', [])
            complaint_ids.append(complaint.id)
            request.session['complaint_ids'] = complaint_ids
            
            return JsonResponse({'status': 'success', 'message': 'Complaint registered successfully!'})
        else:
            return JsonResponse({'status': 'failed', 'message': 'Invalid OTP.'})
    return JsonResponse({'status': 'failed'})

def view_complaint_status(request):
    complaints = []
    error = None
    if request.method == 'POST':
        email = request.POST.get('email')
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        otp_input = request.POST.get('otp')
        
        if not otp_input:
            # First step: Send OTP
            user_complaints = Complaint.objects.filter(email=email, name=name, phone=phone)
            if user_complaints.exists():
                otp = str(random.randint(100000, 999999))
                request.session['login_otp'] = otp
                request.session['login_email'] = email
                
                def send_otp_email(to_email, otp_code):
                    message = (
                        "GOLDEN FORK\n\n"
                        "Dear Guest,\n\n"
                        "To securely review the status of your complaint request, please use the verification code below:\n\n"
                        f"OTP: {otp_code}\n\n"
                        "This code will remain valid for 10 minutes. For your privacy and security, kindly do not share this code with anyone.\n\n"
                        "If you did not request this verification, no further action is required.\n\n"
                        "Warm regards,\n"
                        "GOLDEN FORK Guest Relations"
                    )
                    send_mail(
                        'GoldenFork - Verification Code',
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [to_email],
                        fail_silently=False,
                    )
                threading.Thread(target=send_otp_email, args=(email, otp)).start()
                
                return JsonResponse({'status': 'otp_sent'})
            else:
                return JsonResponse({'status': 'not_found', 'message': "You don't have any registered complaints with these details."})
        else:
            # Second step: Verify OTP
            if otp_input == request.session.get('login_otp') and email == request.session.get('login_email'):
                complaints = Complaint.objects.filter(email=email).order_by('-created_at')
                return render(request, 'view_complaint_status.html', {'complaints': complaints})
            else:
                return render(request, 'view_complaint_status.html', {'error': 'Invalid OTP'})
                
    return render(request, 'view_complaint_status.html')

def complaint_page(request):
    return render(request, 'complaint_register.html')

# UPDATE STATUS
def update_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    status = request.GET.get('status')
    old_status = order.status

    if status in dict(Order.STATUS_CHOICES):
        order.status = status
    else:
        if order.status == 'Pending':
            order.status = 'Cooking'
        elif order.status == 'Cooking':
            order.status = 'Ready'
    
    # STOCK REDUCTION LOGIC: Reduce stock when order moves to 'Cooking' (accepted)
    if order.status == 'Cooking' and old_status == 'Pending':
        order_items = OrderItem.objects.filter(order=order)
        for oi in order_items:
            item = oi.item
            item.stock_quantity -= oi.quantity
            if item.stock_quantity < 0:
                item.stock_quantity = 0
            item.save()
            
    order.save()
    return redirect('kitchen')

def accept_order(request, order_id):
    if not request.session.get('manager'):
        return redirect('manager_login')
    order = get_object_or_404(Order, id=order_id)
    if request.method == 'POST':
        message = request.POST.get('message')
        if message:
            order.kitchen_reply = message
        order.kitchen_acceptance_status = 'Accepted'
        order.save()
    return redirect('kitchen')

def reject_order(request, order_id):
    if not request.session.get('manager'):
        return redirect('manager_login')
    order = get_object_or_404(Order, id=order_id)
    if request.method == 'POST':
        message = request.POST.get('message')
        if message:
            order.kitchen_reply = message
        order.kitchen_acceptance_status = 'Rejected'
        order.status = 'Cancelled'
        order.save()
    return redirect('kitchen')

# ORDER STATUS API
def order_status_api(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return JsonResponse({
        'status': order.status,
        'is_paid': order.is_paid,
        'is_served': order.is_served
    })

# ORDER STATUS NAVBAR
def order_status(request):
    if request.method == 'POST':
        token = request.POST.get('token_number')
        if token:
            try:
                order = Order.objects.filter(id=int(token)).order_by('-created_at').first()
                if order:
                    request.session['current_order_id'] = order.id
                    return redirect('order_status')
            except ValueError:
                pass
            return render(request, 'order_status.html', {'error': 'Invalid Order ID'})

    order_ids = request.session.get('order_ids', [])
    orders = Order.objects.filter(id__in=order_ids, is_served=False).exclude(status='Cancelled').order_by('-created_at')
    
    from django.utils import timezone
    for order in orders:
        # Kitchen Acceptance Timer Logic (now for all orders)
        if order.kitchen_acceptance_status == 'Pending':
            if order.excess_order_expiry:
                elapsed_excess = (order.excess_order_expiry - timezone.now()).total_seconds()
                if elapsed_excess > 0:
                    order.time_left_excess = int(elapsed_excess)
                else:
                    order.time_left_excess = 0
                    order.kitchen_acceptance_status = 'Rejected'
                    order.status = 'Cancelled'
                    order.kitchen_reply = "Order cancelled due to no response from kitchen."
                    order.save()
            else:
                order.time_left_excess = 0
        else:
            order.time_left_excess = 0

        # Regular Confirmation Timer Logic
        if order.status == 'Pending' and not order.is_confirmed and not order.is_excess_stock:
            elapsed = (timezone.now() - order.created_at).total_seconds()
            if elapsed < 60:
                order.time_left = int(60 - elapsed)
            else:
                order.time_left = 0
                order.is_confirmed = True
                order.save()
        else:
            order.time_left = 0
            
    return render(request, 'order_status.html', {'orders': orders})

# PAYMENT PAGE
def payment_page(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if order.status == 'Cancelled':
        return redirect('order_status')
    payment = order.payment_set.first()
    return render(request, 'payment.html', {'order': order, 'payment': payment})

# PAYMENT NAVBAR
def payment_nav(request):
    order_ids = request.session.get('order_ids', [])
    all_orders = Order.objects.filter(id__in=order_ids).order_by('-created_at')
    
    pending_payments = all_orders.filter(is_paid=False).exclude(status='Cancelled')
    paid_orders = all_orders.filter(is_paid=True).exclude(status='Cancelled')
    cancelled_orders = all_orders.filter(status='Cancelled')
    
    return render(request, 'payment.html', {
        'pending_payments': pending_payments,
        'paid_orders': paid_orders,
        'cancelled_orders': cancelled_orders,
        'list_mode': True
    })

# CONFIRM PAYMENT
def confirm_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if request.method == 'POST':
        method = request.POST.get('method')
        screenshot = request.FILES.get('screenshot')

        is_paid = True if method == 'UPI' else False

        Payment.objects.create(
            order=order,
            method=method,
            screenshot=screenshot,
            is_paid=is_paid
        )
        order.is_paid = is_paid
        order.save()

    return redirect('payment', order_id=order.id)

# COUNTER PAYMENT
def counter_payment(request, order_id):
    if not request.session.get('manager'):
        return redirect('manager_login')
        
    order = get_object_or_404(Order, id=order_id)
    Payment.objects.create(
        order=order,
        method='Counter Cash',
        is_paid=True
    )
    order.is_paid = True
    order.save()
    return redirect('manager_dashboard')

# MANAGER LOGIN
def manager_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        if username == 'goldenfork066' and password == 'goldenforkmanager@066':
            request.session['manager'] = True
            return redirect('manager_dashboard')
        else:
            return render(request, 'manager_login.html', {'error': 'Invalid credentials'})

    return render(request, 'manager_login.html')

def manager_logout(request):
    request.session.pop('manager', None)
    return redirect('home')

# MANAGER DASHBOARD
def manager_dashboard(request):
    if not request.session.get('manager'):
        return redirect('manager_login')

    sales_filter = request.GET.get('filter', 'all')
    specific_date = request.GET.get('date')
    
    from django.utils import timezone
    from datetime import datetime
    now = timezone.now()
    
    orders = Order.objects.all().order_by('-created_at')
    
    if specific_date:
        try:
            date_obj = datetime.strptime(specific_date, '%Y-%m-%d').date()
            orders = orders.filter(created_at__date=date_obj)
            sales_filter = 'custom'
        except ValueError:
            pass
    elif sales_filter == 'day':
        orders = orders.filter(created_at__date=now.date())
    elif sales_filter == 'month':
        orders = orders.filter(created_at__year=now.year, created_at__month=now.month)
    elif sales_filter == 'year':
        orders = orders.filter(created_at__year=now.year)
        
    total_sales = sum([o.total_amount for o in orders if o.is_paid])
    status = RestaurantStatus.objects.first()
    pending_cash = Payment.objects.filter(method='Cash', is_paid=False)

    return render(request, 'manager_dashboard.html', {
        'total_sales': total_sales,
        'orders': orders,
        'status': status,
        'pending_cash': pending_cash,
        'sales_filter': sales_filter,
        'specific_date': specific_date
    })

# TOGGLE RESTAURANT STATUS
def toggle_status(request):
    if not request.session.get('manager'):
        return redirect('manager_login')
        
    status = RestaurantStatus.objects.first()

    if not status:
        status = RestaurantStatus.objects.create(is_open=True)
    else:
        status.is_open = not status.is_open
        status.save()

    return redirect('manager_dashboard')

# ADD MENU
def add_menu(request):
    if not request.session.get('manager'):
        return redirect('manager_login')
        
    if request.method == 'POST':
        name = request.POST.get('name')
        price = request.POST.get('price')
        category_ids = request.POST.getlist('categories')
        image = request.FILES.get('image')
        image2 = request.FILES.get('image2')
        quantity = request.POST.get('quantity', 1)
        dietary_preference = request.POST.get('dietary_preference', 'Veg')
        
        item = MenuItem.objects.create(
            name=name,
            price=price,
            image=image,
            image2=image2,
            quantity=quantity,
            dietary_preference=dietary_preference
        )
        
        # Handle new category if provided (case-insensitive check)
        new_category_name = request.POST.get('new_category')
        if new_category_name:
            cat, _ = Category.objects.get_or_create(name__iexact=new_category_name, defaults={'name': new_category_name})
            item.categories.add(cat)
            
        # Add selected categories
        if category_ids:
            item.categories.add(*category_ids)
            
        return redirect('product_management')
        
    categories = Category.objects.all()
    
    categories = Category.objects.all()

    # Ensure default categories including Combo Section exist
    if not Category.objects.filter(name='Combo Section').exists():
        Category.objects.get_or_create(name='Combo Section')
    
    if not categories.exists():
        for cat in ['Breakfast', 'Lunch', 'Dinner', 'Tea/Snacks', 'Juices']:
            Category.objects.get_or_create(name=cat)
        categories = Category.objects.all()
        
    return render(request, 'add_menu.html', {'categories': categories})

def product_management(request):
    if not request.session.get('manager'):
        return redirect('manager_login')
        
    query = request.GET.get('search', '')
    if query:
        items = MenuItem.objects.filter(Q(name__icontains=query) | Q(categories__name__icontains=query)).distinct()
    else:
        items = MenuItem.objects.all()
        
    categories = Category.objects.all()
    return render(request, 'product_management.html', {'items': items, 'categories': categories, 'query': query})

def toggle_availability(request, item_id):
    if not request.session.get('manager'): return redirect('manager_login')
    item = get_object_or_404(MenuItem, id=item_id)
    item.is_available = not item.is_available
    item.save()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'is_available': item.is_available})
        
    return redirect('product_management')

def delete_category(request, category_id):
    if not request.session.get('manager'): return redirect('manager_login')
    Category.objects.filter(id=category_id).delete()
    return redirect('add_menu')

def update_category(request, category_id):
    if not request.session.get('manager'): return redirect('manager_login')
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            Category.objects.filter(id=category_id).update(name=name)
    return redirect('add_menu')

def approve_cash(request, payment_id):
    if not request.session.get('manager'): return redirect('manager_login')
    payment = get_object_or_404(Payment, id=payment_id)
    payment.is_paid = True
    payment.save()
    payment.order.is_paid = True
    payment.order.save()
    return redirect('manager_dashboard')

def print_bill(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    # Allow access if manager is logged in OR if the order is Paid
    if not request.session.get('manager') and not order.is_paid:
        return redirect('order_status')
    items = OrderItem.objects.filter(order=order)
    return render(request, 'print_bill.html', {'order': order, 'items': items})

# VIEW QRS
def view_qrs(request):
    if not request.session.get('manager'):
        return redirect('manager_login')
    
    table_qrs = []
    review_qrs = []
    
    # Check static directory for existing QRs
    table_path = os.path.join(settings.BASE_DIR, 'core/static/qr_codes')
    review_path = os.path.join(settings.BASE_DIR, 'core/static/review_qrs')
    
    if os.path.exists(table_path):
        table_qrs = [f for f in os.listdir(table_path) if f.endswith('.png')]
    if os.path.exists(review_path):
        review_qrs = [f for f in os.listdir(review_path) if f.endswith('.png')]
        
    return render(request, 'qrs.html', {
        'table_qrs': table_qrs,
        'review_qrs': review_qrs
    })

# MANAGER COMPLAINTS
def manager_complaints(request):
    if not request.session.get('manager'):
        return redirect('manager_login')
    
    pending = Complaint.objects.filter(status='Pending').order_by('-created_at')
    resolved = Complaint.objects.filter(status='Resolved').order_by('-created_at')
    closed = Complaint.objects.filter(status='Closed').order_by('-created_at')
    
    return render(request, 'manager_complaints.html', {
        'pending': pending,
        'resolved': resolved,
        'closed': closed
    })

def update_complaint_status(request, complaint_id):
    if not request.session.get('manager'):
        return redirect('manager_login')
    complaint = get_object_or_404(Complaint, id=complaint_id)
    if request.method == 'POST':
        status = request.POST.get('status')
        reply = request.POST.get('reply')
        if status:
            complaint.status = status
        if reply:
            complaint.manager_reply = reply
            # Send email to customer asynchronously
            def send_reply_email(to_email, c_id, c_status, m_reply):
                message = (
                    "GOLDEN FORK\n\n"
                    "Dear Guest,\n\n"
                    "Thank you for bringing your concern to our attention. Your complaint has been carefully reviewed by our management team.\n\n"
                    f"Complaint Status: {c_status}\n\n"
                    "Manager Response:\n\n"
                    "---\n"
                    f"{m_reply}\n"
                    "---\n\n"
                    "We sincerely value your feedback, as it helps us enhance the experience we provide at GOLDEN FORK.\n\n"
                    "Should you require any further assistance, please feel free to contact us.\n\n"
                    "Warm regards,\n"
                    "Restaurant Manager\n"
                    "GOLDEN FORK"
                )
                send_mail(
                    f'GoldenFork - Update on Complaint #{c_id}',
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [to_email],
                    fail_silently=True,
                )
            threading.Thread(target=send_reply_email, args=(complaint.email, complaint.id, complaint.status, reply)).start()
            
        elif status:
             # Send email automatically if status changed but no manual reply
             def send_status_email(to_email, c_id, c_status):
                 send_mail(
                    f'GoldenFork - Update on Complaint #{c_id}',
                    f'The status of your complaint has been updated to: {c_status}',
                    settings.DEFAULT_FROM_EMAIL,
                    [to_email],
                    fail_silently=True,
                )
             threading.Thread(target=send_status_email, args=(complaint.email, complaint.id, complaint.status)).start()
             
        complaint.save()
    return redirect('manager_complaints')

# CUSTOMER REVIEWS
def submit_review(request):
    if request.method == 'POST':
        rating = request.POST.get('rating')
        opinion = request.POST.get('opinion')
        if rating and opinion:
            Review.objects.create(rating=rating, opinion=opinion)
            return render(request, 'submit_review.html', {'success': True})
    return render(request, 'submit_review.html')

def manager_reviews(request):
    if not request.session.get('manager'):
        return redirect('manager_login')
    reviews = Review.objects.all().order_by('-created_at')
    return render(request, 'manager_reviews.html', {'reviews': reviews})

# ORDER CANCELLATION
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if order.status == 'Pending':
        order.status = 'Cancelled'
        order.is_cancelled_by_customer = True
        order.save()
        return JsonResponse({'status': 'success', 'message': 'Order cancelled successfully.'})
    return JsonResponse({'status': 'failed', 'message': 'Cannot cancel order once preparation starts.'})

def change_food(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if order.status == 'Pending' and not order.is_confirmed: # Re-added is_confirmed check
        # Actually user said "confirmed by customer ... make payment portal open"
        # If they already confirmed and paid, they shouldn't change.
        if order.status == 'Paid': return redirect('order_status')
        
        cart = {}
        for oi in order.orderitem_set.all():
            cart[str(oi.item.id)] = oi.quantity
        request.session['cart'] = cart
        request.session['updating_order_id'] = order.id
        return redirect('menu')
    return redirect('order_status')

def confirm_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if order.status == 'Pending':
        order.is_confirmed = True
        order.save()
        return JsonResponse({'status': 'success', 'message': 'Order confirmed successfully.'})
    return JsonResponse({'status': 'failed', 'message': 'Cannot confirm.'})

def mark_served(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    # They can only mark as served if it's Ready
    if order.status == 'Ready':
        order.is_served = True
        order.save()
        return JsonResponse({'status': 'success', 'message': 'Order completed! Enjoy your meal.'})
    return JsonResponse({'status': 'error', 'message': 'Order is not ready yet.'})

# KITCHEN ALERT
def alert_kitchen(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order.kitchen_alert = True
    order.save()
    return JsonResponse({'status': 'success'})

def kitchen_reply(request, order_id):
    if not request.session.get('manager'):
        return redirect('manager_login')
    order = get_object_or_404(Order, id=order_id)
    if request.method == 'POST':
        message = request.POST.get('message')
        if message:
            order.kitchen_reply = message
            order.kitchen_alert = False # Clear alert after reply
            order.save()
    return redirect('kitchen')

def update_item(request, item_id):
    if not request.session.get('manager'):
        return redirect('manager_login')
    item = get_object_or_404(MenuItem, id=item_id)
    if request.method == 'POST':
        item.name = request.POST.get('name')
        item.price = request.POST.get('price')
        item.stock_quantity = request.POST.get('stock_quantity')
        
        dietary = request.POST.get('dietary_preference')
        if dietary:
            item.dietary_preference = dietary
            
        category_ids = request.POST.getlist('categories')
        if category_ids:
            item.categories.set(category_ids)
            
        item.save()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success'})
            
    return redirect('product_management')

def delete_item(request, item_id):
    if not request.session.get('manager'):
        return redirect('manager_login')
    item = get_object_or_404(MenuItem, id=item_id)
    item.delete()
    return redirect('product_management')
from django.db import models


# CATEGORY
class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


# MENU ITEM
class MenuItem(models.Model):
    name = models.CharField(max_length=100)
    price = models.FloatField()
    categories = models.ManyToManyField(Category, related_name='menu_items')
    image = models.ImageField(upload_to='food_images/', null=True, blank=True)
    image2 = models.ImageField(upload_to='food_images/', null=True, blank=True)
    quantity = models.CharField(max_length=50, default='1')
    stock_quantity = models.IntegerField(default=0)
    is_available = models.BooleanField(default=True)
    dietary_preference = models.CharField(max_length=20, choices=[('Veg', 'Veg'), ('Non-Veg', 'Non-Veg')], default='Veg')

    def __str__(self):
        return self.name

    @property
    def is_combo(self):
        return self.categories.filter(name='Combo Section').exists()


# ORDER
class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Cooking', 'Cooking'),
        ('Ready', 'Ready'),
        ('Paid', 'Paid'),
        ('Cancelled', 'Cancelled'),
    ]

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    total_amount = models.FloatField(default=0)
    token_number = models.IntegerField(null=True, blank=True)
    kitchen_alert = models.BooleanField(default=False)
    kitchen_reply = models.TextField(null=True, blank=True)
    is_cancelled_by_customer = models.BooleanField(default=False)
    is_confirmed = models.BooleanField(default=False)
    is_updated = models.BooleanField(default=False)
    
    # New fields for excess stock orders
    is_excess_stock = models.BooleanField(default=False)
    kitchen_acceptance_status = models.CharField(max_length=20, choices=[('Pending', 'Pending'), ('Accepted', 'Accepted'), ('Rejected', 'Rejected')], default='Pending')
    excess_order_expiry = models.DateTimeField(null=True, blank=True)
    is_paid = models.BooleanField(default=False)
    is_served = models.BooleanField(default=False)

    def __str__(self):
        return f"Order #{self.id} (Token: {self.token_number})"

    @property
    def total_quantity(self):
        return sum(item.quantity for item in self.orderitem_set.all())

    @property
    def is_high_order(self):
        return self.total_quantity >= 5


# ORDER ITEMS
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.item.name} x {self.quantity}"


# PAYMENT
class Payment(models.Model):
    PAYMENT_METHODS = [
        ('UPI', 'UPI'),
        ('Cash', 'Cash'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    method = models.CharField(max_length=50, choices=PAYMENT_METHODS)
    screenshot = models.ImageField(upload_to='payment_screenshots/', null=True, blank=True)
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.method} - Order #{self.order.id}"


# EXPENSE
class Expense(models.Model):
    CATEGORY_CHOICES = [
        ('Electricity', 'Electricity'),
        ('Salary', 'Salary'),
        ('Others', 'Others'),
    ]

    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    amount = models.FloatField()
    date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.category} - ₹{self.amount}"


# STOCK
class Stock(models.Model):
    item_name = models.CharField(max_length=100)
    quantity = models.IntegerField()

    def __str__(self):
        return f"{self.item_name} ({self.quantity})"


# RESTAURANT STATUS
class RestaurantStatus(models.Model):
    is_open = models.BooleanField(default=True)

    def __str__(self):
        return "Open" if self.is_open else "Closed"


# CUSTOMER COMPLAINT
class Complaint(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField(null=True, blank=True)
    description = models.TextField()
    image = models.ImageField(upload_to='complaints/', null=True, blank=True)
    status = models.CharField(max_length=50, default='Pending')
    otp = models.CharField(max_length=6, null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    manager_reply = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Complaint {self.id} - {self.created_at.strftime('%d-%m-%Y %H:%M')}"

# CUSTOMER REVIEW
class Review(models.Model):
    rating = models.IntegerField(default=5)
    opinion = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Review {self.rating} stars - {self.created_at.strftime("%d-%m-%Y")}'

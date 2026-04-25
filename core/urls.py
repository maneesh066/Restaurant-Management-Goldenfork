from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    # MENU
    path('menu/', views.menu, name='menu'),

    # CART
    path('add-to-cart/<int:item_id>/', views.add_to_cart, name='add_to_cart'),
    path('update-cart/', views.update_cart, name='update_cart'),
    path('cart/', views.view_cart, name='cart'),
    path('remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    
    # ORDER
    path('place-order/', views.place_order, name='place_order'),
    path('order-status-api/<int:order_id>/', views.order_status_api, name='order_status_api'),
    path('order-status/', views.order_status, name='order_status'),
    path('mark-served/<int:order_id>/', views.mark_served, name='mark_served'),

    # KITCHEN PANEL
    path('kitchen/', views.kitchen, name='kitchen'),
    path('update-status/<int:order_id>/', views.update_status, name='update_status'),
    path('update-stock/<int:item_id>/', views.update_stock, name='update_stock'),
    path('accept-order/<int:order_id>/', views.accept_order, name='accept_order'),
    path('reject-order/<int:order_id>/', views.reject_order, name='reject_order'),
    # COMPLAINTS
    path('complaint/', views.complaint_page, name='complaint_page'),
    path('submit-complaint/', views.submit_complaint, name='submit_complaint'),
    path('verify-complaint/', views.verify_complaint_otp, name='verify_complaint_otp'),
    path('complaint-status/', views.view_complaint_status, name='view_complaint_status'),
    
    # REVIEWS
    path('review/', views.submit_review, name='submit_review'),
    path('manager/reviews/', views.manager_reviews, name='manager_reviews'),

    # CANCELLATION & ALERTS
    path('cancel-order/<int:order_id>/', views.cancel_order, name='cancel_order'),
    path('change-food/<int:order_id>/', views.change_food, name='change_food'),
    path('confirm-order/<int:order_id>/', views.confirm_order, name='confirm_order'),
    path('alert-kitchen/<int:order_id>/', views.alert_kitchen, name='alert_kitchen'),
    path('kitchen-reply/<int:order_id>/', views.kitchen_reply, name='kitchen_reply'),
    # PAYMENT
    path('payment/<int:order_id>/', views.payment_page, name='payment'),
    path('payment/', views.payment_nav, name='payment_nav'),
    path('confirm-payment/<int:order_id>/', views.confirm_payment, name='confirm_payment'),
    path('counter-payment/<int:order_id>/', views.counter_payment, name='counter_payment'),
    
    # MANAGER
    path('manager/login/', views.manager_login, name='manager_login'),
    path('manager/logout/', views.manager_logout, name='manager_logout'),
    path('manager/dashboard/', views.manager_dashboard, name='manager_dashboard'),
    path('manager/add-menu/', views.add_menu, name='add_menu'),
    path('manager/toggle-availability/<int:item_id>/', views.toggle_availability, name='toggle_availability'),
    path('manager/delete-category/<int:category_id>/', views.delete_category, name='delete_category'),
    path('manager/update-category/<int:category_id>/', views.update_category, name='update_category'),
    path('manager/approve-cash/<int:payment_id>/', views.approve_cash, name='approve_cash'),
    path('manager/qrs/', views.view_qrs, name='view_qrs'),
    path('manager/print-bill/<int:order_id>/', views.print_bill, name='print_bill'),
    path('toggle-status/', views.toggle_status, name='toggle_status'),
    path('manager/complaints/', views.manager_complaints, name='manager_complaints'),
    path('manager/update-complaint-status/<int:complaint_id>/', views.update_complaint_status, name='update_complaint_status'),
    path('manager/update-item/<int:item_id>/', views.update_item, name='update_item'),
    path('manager/delete-item/<int:item_id>/', views.delete_item, name='delete_item'),
    path('manager/product-management/', views.product_management, name='product_management'),
]
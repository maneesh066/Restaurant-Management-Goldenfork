from django.contrib import admin
from .models import *

admin.site.register(Category)
admin.site.register(MenuItem)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Payment)
admin.site.register(Expense)
admin.site.register(Stock)
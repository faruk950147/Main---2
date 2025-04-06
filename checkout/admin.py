from django.contrib import admin
from unfold.admin import ModelAdmin
from checkout.models import Checkout, CheckoutItem

# Register your models here.

class CheckoutAdmin(ModelAdmin):
    list_display = ['id', 'user', 'status', 'payment_method', 'total', 'shipping_date', 'payment', 'payment_id', 'invoice_id', 'tracking_no', 'created_date', 'updated_date']
    list_editable = ['status', 'payment', 'shipping_date']
    
admin.site.register(Checkout, CheckoutAdmin)
class CheckoutItemAdmin(ModelAdmin):
    list_display = ['id', 'checkout', 'cart', 'product', 'variant', 'quantity', 'total_amount', 'created_date', 'updated_date']

    def cart(self, obj):
        return obj.checkout.cart if obj.checkout else None
    cart.admin_order_field = 'checkout__cart'
    cart.short_description = 'Cart'

admin.site.register(CheckoutItem, CheckoutItemAdmin)


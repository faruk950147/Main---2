from django.contrib import admin
from unfold.admin import ModelAdmin
import admin_thumbnails

from cart.models import Coupon, Cart, CartItem

# Register your models here.
class CouponAdmin(ModelAdmin):
    list_display = ['id', 'coupon_code', 'coupon_discount', 'is_expired', 'minimum_amount']
    search_fields = ['coupon_code']
    list_filter = ['is_expired']
    list_editable = ['is_expired']
admin.site.register(Coupon, CouponAdmin)

class CartAdmin(ModelAdmin):
    list_display = ['id', 'user', 'coupon', 'paid', 'total_amount', 'created_date', 'update_date']
    search_fields = ['user__username', 'coupon__coupon_code']
    list_filter = ['paid']  
    list_editable = ['paid', 'coupon']
admin.site.register(Cart, CartAdmin)

class CartItemAdmin(ModelAdmin):
    list_display = ['id', 'cart', 'product', 'variant', 'quantity', 'total_price_of_items', 'created_date', 'update_date']
    search_fields = ['cart__user__username', 'product__title', 'variant__title']
    list_filter = ['cart__paid']
    list_editable = ['cart', 'product', 'variant', 'quantity']
admin.site.register(CartItem, CartItemAdmin)


from django.shortcuts import redirect, get_object_or_404
from django.db.models import Min, Max, Sum
from django.utils import timezone
from cart.models import Cart, CartItem
from stories.models import (
    Category, Brand, Product, Images, Color, Size, Variants,
)

def get_filters(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user, paid=False)
        cart_items = CartItem.objects.filter(cart=cart)
        
        # Count the number of cart items
        cart_count = cart_items.count()  
        
        # Calculate cart totals without discount first
        cart_totals = sum(item.quantity * (item.variant.price if item.variant else item.product.price) for item in cart_items)
        
        # Apply coupon discount if applicable
        if cart.coupon and cart.coupon.is_valid(cart_totals):
            # Apply coupon discount percentage if valid
            cart_totals -= cart_totals * (cart.coupon.coupon_discount / 100)
        
        # Adding extra charge (e.g., shipping fee)
        payable_price = cart_totals + 150  # Add extra charge for payable price
        
        return {
            'cart_items': cart_items,
            'cart_count': cart_count,
            'cart_totals': cart_totals,
            'payable_price': payable_price 
        }
    else:
        return {
            'cart_items': [],
            'cart_count': 0,
            'cart_totals': 0,
            'payable_price': 0
        }
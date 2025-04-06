from decimal import Decimal
from django.shortcuts import render,redirect, get_object_or_404
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.views import generic
from django.utils import timezone
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.db.models import Min, Max, Sum
import json
from cart.forms import (
    CartItemForm
)
from stories.models import (
    Product, Variants
)
from cart.models import (
    Coupon, Cart, CartItem
)

# create your views here
@method_decorator(never_cache, name='dispatch')
class AddToCart(LoginRequiredMixin, generic.View):
    login_url = reverse_lazy('sign')

    def post(self, request):
        if request.method == "POST":
            try:
                # Request to JSON data
                data = json.loads(request.body)
                size_id = data.get("size_id")
                color_id = data.get("color_id")
                quantity = data.get("quantity")
                product_id = data.get("product_id")

                # Quantity validation
                if quantity is None or int(quantity) <= 0:
                    return JsonResponse({"status": 400, "messages": "Quantity must be greater than 0!"})
                quantity = int(quantity)

                # Product validation
                if not product_id:
                    return JsonResponse({"status": 400, "messages": "Item ID is required!"})
                product = get_object_or_404(Product, id=product_id)

                # Get variant if applicable (Optimized Query)
                variant_qs = Variants.objects.filter(
                    product=product,
                    size_id=size_id if size_id else None,
                    color_id=color_id if color_id else None
                )
                
                variant = list(variant_qs)[0] if variant_qs.exists() else None  # No IndexError

                if (size_id or color_id) and not variant:
                    return JsonResponse({"status": 400, "messages": "Variant not found!"})

                # Stock validation
                max_stock = variant.quantity if variant else (product.in_stock_max or 0)
                if max_stock <= 0:
                    return JsonResponse({"status": 400, "messages": "Item out of stock!"})

                # Get or create cart (Optimized Query)
                cart_qs = Cart.objects.filter(user=request.user, paid=False).prefetch_related('items__product', 'items__variant')
                cart = list(cart_qs)[0] if cart_qs.exists() else Cart.objects.create(user=request.user, paid=False)  # No IndexError

                # Check if product already exists in cart
                cart_item_qs = cart.items.filter(product=product, variant=variant)
                if cart_item_qs.exists():
                    existing_cart_item = list(cart_item_qs)[0]  # No IndexError
                    new_quantity = existing_cart_item.quantity + quantity
                    if new_quantity <= max_stock:
                        existing_cart_item.quantity = new_quantity
                        existing_cart_item.save()
                        messages = "Quantity updated successfully!"
                    else:
                        return JsonResponse({"status": 400, "messages": f"You can't add more than {max_stock} units!"})
                else:
                    if quantity <= max_stock:
                        CartItem.objects.create(cart=cart, product=product, variant=variant, quantity=quantity)
                        messages = "Item added to cart successfully!"
                    else:
                        return JsonResponse({"status": 400, "messages": f"You can't add more than {max_stock} units!"})

                # Update cart count & total price (Optimized)
                cart_count = cart.items.count()
                cart_totals = sum(item.quantity * (item.variant.price if item.variant else item.product.price) for item in cart.items.all())

                # Apply coupon discount if valid
                if cart.coupon and cart.coupon.is_valid(cart_totals):
                    cart_totals -= cart_totals * (cart.coupon.coupon_discount / 100)

                return JsonResponse({
                    'status': 200, 
                    'messages': messages, 
                    'cart_count': cart_count, 
                    'cart_totals': cart_totals,
                })

            except (ValueError, TypeError, json.JSONDecodeError) as e:
                return JsonResponse({"status": 400, "messages": f"Invalid input: {str(e)}"})
            except Exception as e:
                return JsonResponse({"status": 400, "messages": f"Something went wrong: {str(e)}"})

        return JsonResponse({'status': 400, 'messages': 'Invalid request'})

@method_decorator(never_cache, name='dispatch')
class QuantityIncDec(LoginRequiredMixin, generic.View):
    login_url = reverse_lazy('sign')
    
    def post(self, request):
        if request.method == "POST":
            try:
                # Request to JSON data
                data = json.loads(request.body)
                cart_item_id = data.get("id")
                action = data.get("action")

                # Validate input
                if not cart_item_id or not action:
                    return JsonResponse({"status": 400, "messages": "Cart item ID and action are required!"})

                # Get the cart item
                cart_item = get_object_or_404(CartItem, id=cart_item_id)

                # Get product and variant details
                product = cart_item.product
                variant = cart_item.variant
                
                # Determine max stock
                max_stock = variant.quantity if variant else product.in_stock_max

                # Increase or decrease quantity
                if action == "increase":
                    if cart_item.quantity < max_stock:
                        cart_item.quantity += 1
                        cart_item.save()
                        message = "Quantity increased successfully!"
                    else:
                        return JsonResponse({"status": 400, "messages": f"Cannot increase beyond {max_stock} units!"})
                
                elif action == "decrease":
                    if cart_item.quantity > 1:
                        cart_item.quantity -= 1
                        cart_item.save()
                        message = "Quantity decreased successfully!"
                    else:
                        return JsonResponse({"status": 400, "messages": "Quantity cannot be less than 1!"})
                
                else:
                    return JsonResponse({"status": 400, "messages": "Invalid action!"})

                # Update cart details
                cart = cart_item.cart
                cart_items = list(cart.items.prefetch_related('product', 'variant').all())

                # Calculate cart totals
                cart_totals = sum(item.quantity * (item.variant.price if item.variant else item.product.price) for item in cart_items)

                # Apply coupon discount if valid
                if cart.coupon and cart.coupon.is_valid(cart_totals):
                    cart_totals -= cart_totals * (cart.coupon.coupon_discount / 100)


                return JsonResponse({
                    'status': 200,
                    'messages': message, 
                    'quantity': cart_item.quantity,
                    'item_total_price': cart_item.quantity * (cart_item.variant.price if cart_item.variant else cart_item.product.price),
                    'cart_count': cart.items.count(),  
                    'cart_totals': cart_totals,
                    'payable_price': cart_totals + 150,  
                    'id': cart_item.id
                })

            except (ValueError, TypeError, json.JSONDecodeError) as e:
                return JsonResponse({"status": 400, "messages": f"Invalid input: {str(e)}"})
            except Exception as e:
                return JsonResponse({"status": 400, "messages": f"Something went wrong: {str(e)}"})

        return JsonResponse({"status": 400, "messages": "Invalid request"})

@method_decorator(never_cache, name='dispatch')
class RemoveToCart(LoginRequiredMixin, generic.View):
    login_url = reverse_lazy('sign')

    def post(self, request):
        if request.method == "POST":
            try:
                data = json.loads(request.body)
                cart_item_id = data.get("id")

                if not cart_item_id:
                    return JsonResponse({"status": 400, "messages": "Missing cart item ID"})

                # Get and delete the cart item
                cart_item = get_object_or_404(CartItem, id=cart_item_id, cart__user=request.user, cart__paid=False)
                cart = cart_item.cart  # Store cart before deleting item
                cart_item.delete()  

                # Update cart details
                cart_items = list(cart.items.prefetch_related('product', 'variant').all())  # Optimized Query
                cart_totals = sum(item.quantity * (item.variant.price if item.variant else item.product.price) for item in cart_items)
                
                # Apply coupon discount if valid
                if cart.coupon and cart.coupon.is_valid(cart_totals):
                    cart_totals -= cart_totals * (cart.coupon.coupon_discount / 100)    

                return JsonResponse({
                    "status": 200, 
                    "messages": "Item removed from cart",
                    "cart_count": cart.items.count(),  
                    "cart_totals": cart_totals,
                    "payable_price": cart_totals + 150,
                    "id": cart_item_id  # Using stored ID instead of deleted object
                })

            except (ValueError, TypeError, json.JSONDecodeError) as e:
                return JsonResponse({"status": 400, "messages": f"Invalid input: {str(e)}"})
            except Exception as e:
                return JsonResponse({"status": 400, "messages": f"Something went wrong: {str(e)}"})

        return JsonResponse({"status": 400, "messages": "Invalid request"})

@method_decorator(never_cache, name='dispatch')
class CouponApplyView(LoginRequiredMixin, generic.View):
    login_url = reverse_lazy('sign')
    def post(self, request):
        if request.method == "POST":
            try:
                data = json.loads(request.body)
                coupon_code = data.get("coupon_code")

                if not coupon_code:
                    return JsonResponse({"status": 400, "messages": "Coupon code is required!"})

                # Coupon check 
                coupon_qs = Coupon.objects.filter(coupon_code=coupon_code, is_expired=False)
                if not coupon_qs.exists():
                    return JsonResponse({"status": 400, "messages": "Invalid or expired coupon!"})
                coupon = list(coupon_qs)[0]  # IndexError ignored using list()

                # Cart check 
                cart_qs = Cart.objects.filter(user=request.user, paid=False)
                if not cart_qs.exists():
                    return JsonResponse({"status": 400, "messages": "Cart not found!"})
                cart = list(cart_qs)[0]  # IndexError ignored using list()

                # Coupon valid check 
                if not coupon.is_valid(cart.total_amount):
                    return JsonResponse({"status": 400, "messages": "Coupon cannot be applied!"})

                # Coupon apply 
                cart.coupon = coupon
                cart.save()

                return JsonResponse({
                    "status": 200,
                    "messages": "Coupon applied successfully!",
                    "cart_totals": cart.total_amount,
                    "payable_price": cart.total_amount + 150
                })
                
            except (ValueError, TypeError, json.JSONDecodeError) as e:
                return JsonResponse({"status": 400, "messages": f"Invalid input: {str(e)}"})

            except Exception as e:
                return JsonResponse({"status": 400, "messages": f"Something went wrong: {str(e)}"})

        return JsonResponse({"status": 400, "messages": "Invalid request"})

@method_decorator(never_cache, name='dispatch')
class CartView(LoginRequiredMixin, generic.View):
    login_url = reverse_lazy('sign')

    def get(self, request):
        # Get the user's existing cart

        # Render the cart page
        return render(request, 'cart/cart.html', {})    

import uuid
import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from paypal.standard.forms import PayPalPaymentsForm
from django.conf import settings
from django.urls import reverse
from paypal.standard.ipn.models import PayPalIPN
from checkout.models import Checkout, CheckoutItem
from cart.models import Cart, CartItem

@method_decorator(never_cache, name='dispatch')
class CheckoutView(LoginRequiredMixin, generic.View):
    def get(self, request):
        carts = list(Cart.objects.filter(user=request.user, paid=False))

        if not carts:
            return redirect("cartview")

        cart = carts[0]
        cart_items = list(CartItem.objects.filter(cart=cart))

        # Calculate total cart price
        cart_totals = sum(item.quantity * (item.variant.price if item.variant else item.product.price) for item in cart_items)

        # Apply coupon if available
        if cart.coupon and cart.coupon.is_valid(cart_totals):
            cart_totals -= cart_totals * (cart.coupon.coupon_discount / 100)

        shipping_cost = 150
        payable_price = cart_totals + shipping_cost  

        payment_methods = Checkout._meta.get_field('payment_method').choices  

        context = {
            "cart_totals": cart_totals,
            "payable_price": payable_price,
            "cart_items": cart_items,
            "payment_methods": payment_methods
        }

        return render(request, "checkout/checkout.html", context)
    
    def post(self, request):
        if request.method == "POST":
            try:
                # Load data from request body
                data = json.loads(request.body)
                full_name = data.get("full_name")
                email = data.get("email")
                country = data.get("country")
                city = data.get("city")
                home_city = data.get("home_city")
                zip_code = data.get("zip_code")
                phone = data.get("phone")
                address = data.get("address")
                payment_method = data.get("payment_method")

                # Validate payment method
                valid_payment_methods = dict(Checkout._meta.get_field('payment_method').choices).keys()
                if payment_method not in valid_payment_methods:
                    return JsonResponse({'status': 400, 'messages': "Invalid payment method!"})

                # Get user's active cart
                carts = list(Cart.objects.filter(user=request.user, paid=False))
                if not carts:
                    return JsonResponse({'status': 400, 'messages': "Your cart is empty!"})

                cart = carts[0]
                cart_items = list(CartItem.objects.filter(cart=cart))
                if not cart_items:
                    return JsonResponse({'status': 400, 'messages': "No items in cart!"})

                # Calculate total price
                cart_totals = sum(item.quantity * (item.variant.price if item.variant else item.product.price) for item in cart_items)

                # Apply coupon if available
                if cart.coupon and cart.coupon.is_valid(cart_totals):
                    cart_totals -= cart_totals * (cart.coupon.coupon_discount / 100)

                shipping_cost = 150
                payable_price = cart_totals + shipping_cost  

                # Determine if the checkout is paid (only for online payments)
                if payment_method == 'Cash':
                    paid = False  # Cash on delivery, no immediate payment
                elif payment_method == 'Paypal':
                    paid = True  # For other online payments (like PayPal, Card)
                    paypal_dict = {
                        "business": settings.PAYPAL_RECEIVER_EMAIL,
                        "amount": f"{payable_price:.2f}",
                        "item_name": "Checkout Payment",
                        "invoice": f"INV-{uuid.uuid4().hex[:10].upper()}",
                        "currency_code": "USD",
                        "notify_url": request.build_absolute_uri(reverse('paypal-ipn')),
                        "return": request.build_absolute_uri(reverse('payment_success')),
                        "cancel_return": request.build_absolute_uri(reverse('payment_cancel')),
                    }
                    form = PayPalPaymentsForm(initial=paypal_dict)
                    return JsonResponse({'status': 200, 'messages': "Redirecting to PayPal", 'form': form.render()})    
                # Create checkout record
                checkout = Checkout.objects.create(
                    user=request.user,
                    cart=cart,
                    total=payable_price,
                    payment_method=payment_method,
                    payment=paid,  
                    full_name=full_name,
                    email=email,
                    country=country,
                    city=city,
                    home_city=home_city,
                    zip_code=zip_code,
                    phone=phone,
                    address=address,
                    created_date=timezone.now()
                )

                # Generate unique payment and tracking IDs
                checkout.payment_id = f"PAY-{uuid.uuid4().hex[:10].upper()}"
                checkout.shipping_date = timezone.now()  
                checkout.invoice_no = f"INV-{uuid.uuid4().hex[:10].upper()}"
                checkout.tracking_no = f"TRK-{uuid.uuid4().hex[:10].upper()}"
                checkout.save()

                # Create checkout items
                for item in cart_items:
                    CheckoutItem.objects.create(
                        user=request.user,
                        checkout=checkout,
                        product=item.product,
                        variant=item.variant,
                        quantity=item.quantity,
                        total_amount=item.quantity * (item.variant.price if item.variant else item.product.price)
                    )

                # Update cart payment status based on payment method
                cart.paid = paid  # If Cash, remains False; otherwise, True
                cart.save()

                # Clear the cart items only after successful checkout
                CartItem.objects.filter(cart=cart).delete()

                # Success message
                messages.success(request, "Your checkout has been placed successfully!")
                return JsonResponse({'status': 200, 'messages': "Your checkout has been placed successfully!"})

            except Exception as e:
                return JsonResponse({'status': 400, 'messages': f"Error: {str(e)}"})
        return JsonResponse({'status': 400, 'messages': "Invalid request method!"})
    
class PaymentSuccessView(LoginRequiredMixin, generic.View):
    def get(self, request):
        return render(request, 'checkout/payment_success.html')

class PaymentCancelView(LoginRequiredMixin, generic.View):
    def get(self, request):
        return render(request, 'checkout/payment_cancel.html')
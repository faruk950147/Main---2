from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from cart.views import (
    AddToCart, QuantityIncDec, RemoveToCart, CartView, CouponApplyView
)
urlpatterns = [
    path('addtocart/', AddToCart.as_view(), name='addtocart'),
    path('qtyincdec/', QuantityIncDec.as_view(), name='qtyincdec'),
    path('removetocart/', RemoveToCart.as_view(), name='removetocart'),
    path('cartview/', CartView.as_view(), name='cartview'),
    path('couponapplyview/', CouponApplyView.as_view(), name='couponapplyview'),
]
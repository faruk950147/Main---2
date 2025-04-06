from django.urls import include, path
from checkout.views import (
    CheckoutView,
    PaymentSuccessView,
    PaymentCancelView,
)

urlpatterns = [
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('payment_success/', PaymentSuccessView.as_view(), name='payment_success'),
    path('payment_cancel/', PaymentCancelView.as_view(), name='payment_cancel'),
]

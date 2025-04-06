from decimal import Decimal
from django.db import models
from django.contrib.auth import get_user_model
from cart.models import Cart
from stories.models import Product, Variants

User = get_user_model()

class Checkout(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    cart = models.OneToOneField(Cart, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=10,
        choices=(
            ('Pending', 'Pending'),
            ('Confirmed', 'Confirmed'),
            ('Shipped', 'Shipped'),
            ('Delivered', 'Delivered'),
            ('Cancelled', 'Cancelled'),
        ),
        default='Pending'
    )
    payment_method = models.CharField(
        max_length=15,
        choices=(
            ('Cash', 'Cash'),
            ('Paypal', 'Paypal'),
            ('SSLCommerz', 'SSLCommerz'),
        ),
        default='Cash'
    )
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))  # Total price of the checkout
    full_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=254)
    country = models.CharField(max_length=150)
    city = models.CharField(max_length=150)
    home_city = models.CharField(max_length=150)
    zip_code = models.CharField(max_length=15)
    phone = models.CharField(max_length=16)
    address = models.TextField(max_length=500)
    shipping_date = models.DateTimeField(null=True, blank=True)
    payment = models.BooleanField(default=False)
    payment_id = models.CharField(max_length=15, null=True, blank=True, unique=True)  
    invoice_no = models.CharField(max_length=15, null=True, blank=True, unique=True)  
    tracking_no = models.CharField(max_length=15, null=True, blank=True, unique=True)  
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']
        verbose_name_plural = '01. Checkouts'

    def __str__(self):
        return self.user.username if self.user else "Guest Checkout"


class CheckoutItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    checkout = models.ForeignKey(Checkout, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    variant = models.ForeignKey(Variants, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, editable=False)  
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = '02. Checkout Items'
        ordering = ['id']

    def save(self, *args, **kwargs):
        """Save the Checkout Item with updated total amount."""
        if self.variant and self.variant.price:
            self.total_amount = self.quantity * self.variant.price  # If variant exists, calculate price
        elif self.product and self.product.price:
            self.total_amount = self.quantity * self.product.price  # If product exists, calculate price
        else:
            self.total_amount = Decimal('0.00')  # If no price, set total amount to zero

        super().save(*args, **kwargs)
        self.update_checkout_total()  # Update the total amount of the checkout

    def delete(self, *args, **kwargs):
        """Update checkout total when an item is deleted."""
        super().delete(*args, **kwargs)
        self.update_checkout_total()  # Update checkout total after deletion

    def update_checkout_total(self):
        """Recalculate the total price of the checkout."""
        checkout_total = self.checkout.items.aggregate(models.Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
        self.checkout.total = checkout_total
        self.checkout.save()

    def __str__(self):
        product_title = self.product.title if self.product else "Unknown Product"
        return f"{product_title} (x{self.quantity}) in Checkout #{self.checkout.id}"

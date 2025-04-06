from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from stories.models import Product, Variants

# Custom User model import
User = get_user_model()


class Coupon(models.Model):
    coupon_code = models.CharField(max_length=10, unique=True)
    coupon_discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    is_expired = models.BooleanField(default=False)
    minimum_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']
        verbose_name_plural = '01. Coupons'

    def is_valid(self, total_amount):
        """Check if the coupon is valid based on expiration, minimum amount, and date range."""
        now = timezone.now()
        if self.is_expired or (self.start_date and now < self.start_date) or (self.end_date and now > self.end_date):
            return False
        return total_amount >= self.minimum_amount

    def __str__(self):
        return self.coupon_code

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    paid = models.BooleanField(default=False)
    created_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']
        verbose_name_plural = '02. Carts'

    @property
    def total_amount(self):
        """
        Calculate total price including variants if available.
        Apply coupon discount if valid.
        """
        total = sum(
            item.total_price_of_items for item in self.items.all()
        )

        # Apply coupon discount if valid
        if self.coupon and self.coupon.is_valid(total):
            # Apply percentage discount
            total -= total * (self.coupon.coupon_discount / 100)

        return max(total, Decimal('0.00'))  # Ensure price is never negative

    def __str__(self):
        return f"Cart for {self.user.username}"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    variant = models.ForeignKey(Variants, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    created_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']
        verbose_name_plural = '03. Cart Items'

    @property
    def total_price_of_items(self):
        """Calculate total price of the item based on variant or product price."""
        if not self.product:
            return Decimal('0.00')  # If product is None, return 0 price
        price = self.variant.price if self.variant and self.variant.price else self.product.price
        return self.quantity * price

    def __str__(self):
        product_name = self.product.title if self.product else "Unknown Product"
        user_name = self.cart.user.username if self.cart and self.cart.user else "Guest"
        return f"Item {product_name} in {user_name}'s cart"

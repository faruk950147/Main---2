from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
import threading
from cart.models import CartItem

# Custom User model import
User = get_user_model()

class CartItemForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Form field styling
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

    def clean_quantity(self):
        """Ensure quantity is at least 1."""
        quantity = self.cleaned_data.get('quantity')
        if quantity < 1:
            raise ValidationError("Quantity must be at least 1.")
        return quantity

    class Meta:
        model = CartItem
        fields = ('quantity',)

from distutils.util import execute
import threading
from django import forms
from django.contrib.auth import get_user_model

from checkout.models import Checkout

User = get_user_model()

class CheckoutForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

    class Meta:
        model = Checkout
        exclude = ('user', 'cart')  
        widgets = {}
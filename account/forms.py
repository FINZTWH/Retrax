from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
import re

from .models import Category, Preference, Product, Review


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email", "password1", "password2")


class SignInForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"autofocus": True}))
    password = forms.CharField(widget=forms.PasswordInput)


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ("category", "name", "description", "price", "points", "rating", "emoji", "stock", "badge", "is_active")
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ("rating", "comment")
        widgets = {
            "rating": forms.NumberInput(attrs={"min": 1, "max": 5}),
            "comment": forms.Textarea(attrs={"rows": 4, "maxlength": 1000}),
        }


class PaymentForm(forms.Form):
    card_name = forms.CharField(max_length=100, label="Name on card")
    card_number = forms.CharField(max_length=23, label="Card number")
    expiry = forms.CharField(max_length=5, label="Expiry date")
    cvc = forms.CharField(max_length=4, min_length=3, label="CVC")

    def clean_card_number(self):
        number = re.sub(r"[^0-9]", "", self.cleaned_data["card_number"])
        if len(number) < 13 or len(number) > 19:
            raise ValidationError("Enter a valid card number.")
        total = 0
        reverse_digits = number[::-1]
        for index, digit in enumerate(reverse_digits):
            value = int(digit)
            if index % 2:
                value *= 2
                if value > 9:
                    value -= 9
            total += value
        if total % 10:
            raise ValidationError("Enter a valid card number.")
        return number

    def clean_expiry(self):
        value = self.cleaned_data["expiry"].strip()
        match = re.fullmatch(r"(0[1-9]|1[0-2])/([0-9]{2})", value)
        if not match:
            raise ValidationError("Use the MM/YY format.")
        month = int(match.group(1))
        year = 2000 + int(match.group(2))
        now = timezone.localdate()
        if year < now.year or (year == now.year and month < now.month):
            raise ValidationError("This card has expired.")
        return value

    def clean_cvc(self):
        cvc = self.cleaned_data["cvc"]
        if not re.fullmatch(r"[0-9]{3,4}", cvc):
            raise ValidationError("Enter a valid CVC.")
        return cvc


class PreferenceForm(forms.ModelForm):
    favourite_categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Preference
        fields = ("favourite_categories", "product_updates", "loyalty_updates")

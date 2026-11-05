from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import SignInForm, SignUpForm, PreferenceForm
from .models import CartItem, Favorite, LoyaltyProfile, Preference, Product


def migrate_session_data(request, user):
    cart = request.session.get("cart", {})
    if isinstance(cart, dict):
        for product_id, quantity in cart.items():
            try:
                product = Product.objects.filter(id=int(product_id), is_active=True).first()
            except (TypeError, ValueError):
                product = None
            if product and product.stock > 0 and isinstance(quantity, int) and quantity > 0:
                item, _ = CartItem.objects.get_or_create(user=user, product=product, defaults={"quantity": quantity})
                if not _:
                    item.quantity += quantity
                    item.quantity = min(item.quantity, product.stock)
                    item.save(update_fields=["quantity"])
    favorites = request.session.get("favorites", [])
    if isinstance(favorites, list):
        for product_id in favorites:
            try:
                product = Product.objects.filter(id=int(product_id), is_active=True).first()
            except (TypeError, ValueError):
                product = None
            if product:
                Favorite.objects.get_or_create(user=user, product=product)
    request.session["cart"] = {}
    request.session["favorites"] = []


def sign_up(request):
    if request.user.is_authenticated:
        return redirect("shop_products")
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.email = form.cleaned_data["email"]
            user.first_name = form.cleaned_data["first_name"]
            user.last_name = form.cleaned_data["last_name"]
            user.save()
            LoyaltyProfile.objects.create(user=user)
            Preference.objects.create(user=user)
            login(request, user)
            migrate_session_data(request, user)
            messages.success(request, "Welcome to Retrax. Your account is ready.")
            next_url = request.POST.get("next") or request.GET.get("next")
            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect("shop_products")
    else:
        form = SignUpForm()
    return render(request, "auth.html", {"form": form, "auth_mode": "register"})


def sign_in(request):
    if request.user.is_authenticated:
        return redirect("shop_products")
    if request.method == "POST":
        form = SignInForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            migrate_session_data(request, request.user)
            messages.success(request, "You are now signed in.")
            next_url = request.POST.get("next") or request.GET.get("next")
            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect("shop_products")
    else:
        form = SignInForm(request)
    return render(request, "auth.html", {"form": form, "auth_mode": "login"})


@login_required
@require_POST
def sign_out(request):
    logout(request)
    messages.success(request, "You have been signed out.")
    return redirect("shop_products")


@login_required
def user_preferences(request):
    preference, _ = Preference.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = PreferenceForm(request.POST, instance=preference)
        if form.is_valid():
            form.save()
            messages.success(request, "Your preferences have been saved.")
            return redirect("my_preferences")
    return redirect("my_preferences")

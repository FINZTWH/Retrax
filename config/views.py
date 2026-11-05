from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.db import transaction
from django.utils.http import url_has_allowed_host_and_scheme

from account.forms import PaymentForm, PreferenceForm, ProductForm, ReviewForm
from account.models import CartItem, Category, Favorite, LoyaltyProfile, Order, OrderItem, Preference, Product, Review
import uuid


CATEGORIES = [
    {"slug": "home", "name": "Home & Living"},
    {"slug": "wellness", "name": "Wellness"},
    {"slug": "food", "name": "Food & Drink"},
    {"slug": "beauty", "name": "Beauty"},
    {"slug": "accessories", "name": "Accessories"},
]

PRODUCTS = [
    {"id": 1, "name": "Ceramic Coffee Mug", "category": "Home & Living", "price": "24.00", "points": 120, "rating": "4.9", "emoji": "☕", "badge": "Bestseller", "badge_class": "badge-bestseller"},
    {"id": 2, "name": "Botanical Candle", "category": "Home & Living", "price": "32.00", "points": 160, "rating": "4.8", "emoji": "🕯️", "badge": "Just for you", "badge_class": "badge-justforyou"},
    {"id": 3, "name": "Green Tea Collection", "category": "Food & Drink", "price": "18.50", "points": 90, "rating": "4.7", "emoji": "🍵", "badge": "Trending", "badge_class": "badge-trending"},
    {"id": 4, "name": "Travel Journal", "category": "Accessories", "price": "27.00", "points": 135, "rating": "4.9", "emoji": "📔", "badge": "Top rated", "badge_class": "badge-toprated"},
    {"id": 5, "name": "Organic Face Serum", "category": "Beauty", "price": "42.00", "points": 210, "rating": "4.8", "emoji": "🧴", "badge": "Popular", "badge_class": "badge-popular"},
    {"id": 6, "name": "Lavender Bath Soak", "category": "Wellness", "price": "29.00", "points": 145, "rating": "4.6", "emoji": "🛁", "badge": "New", "badge_class": "badge-new"},
    {"id": 7, "name": "Eco Tote Bag", "category": "Accessories", "price": "21.00", "points": 105, "rating": "4.7", "emoji": "🛍️", "badge": "Editor's pick", "badge_class": "badge-pick"},
    {"id": 8, "name": "Honey Gift Box", "category": "Food & Drink", "price": "36.00", "points": 180, "rating": "5.0", "emoji": "🍯", "badge": "Bestseller", "badge_class": "badge-bestseller"},
]


def is_staff_user(user):
    return user.is_authenticated and user.is_staff


def get_product(product_id):
    product = Product.objects.filter(id=product_id).first()
    if product:
        return product
    return next((product for product in PRODUCTS if product["id"] == product_id), None)


def shop_products(request):
    category = request.GET.get("category", "all").lower()
    query = request.GET.get("q", "").strip().lower()
    sort = request.GET.get("sort", "")
    valid_category_slugs = {"all", *(item["slug"] for item in CATEGORIES)}
    if category not in valid_category_slugs:
        category = "all"

    database_products = Product.objects.filter(is_active=True).select_related("category")
    products = list(database_products) if database_products.exists() else list(PRODUCTS)
    if category != "all":
        if database_products.exists():
            products = [product for product in products if product.category.slug == category]
        else:
            category_name = next((item["name"] for item in CATEGORIES if item["slug"] == category), "")
            products = [product for product in products if product["category"] == category_name]
    if query:
        products = [
            product for product in products
            if query in (
                product.name.lower() if hasattr(product, "name") else product["name"].lower()
            ) or query in (
                product.category.name.lower() if isinstance(product, Product) else str(product["category"]).lower()
            )
        ]
    if sort == "recommended":
        products.sort(key=lambda product: float(product.rating if hasattr(product, "rating") else product["rating"]), reverse=True)

    cart = request.session.get("cart", {})
    favorites = request.session.get("favorites", [])
    if request.user.is_authenticated:
        favorite_ids = set(Favorite.objects.filter(user=request.user).values_list("product_id", flat=True))
        favorites = list(favorite_ids)
        cart_count = sum(item.quantity for item in CartItem.objects.filter(user=request.user))
    else:
        favorite_ids = set(favorites if isinstance(favorites, list) else [])
        cart_count = sum(quantity for quantity in cart.values() if isinstance(quantity, int) and quantity > 0)
    if not isinstance(cart, dict):
        cart = {}
        request.session["cart"] = cart
    if not isinstance(favorites, list):
        favorites = []
        request.session["favorites"] = favorites

    return render(request, "shop.html", {
        "products": products,
        "categories": CATEGORIES,
        "current_category": category,
        "cart_count": sum(quantity for quantity in cart.values() if isinstance(quantity, int) and quantity > 0),
        "favorite_ids": list(favorite_ids),
        "cart_count": cart_count,
    })


def redirect_back(request):
    next_url = request.POST.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect("shop_products")


def add_to_cart(request, product_id):
    product = get_product(product_id)
    if product is None:
        raise Http404("Product not found")
    if request.method == "POST":
        cart = request.session.get("cart", {})
        if not isinstance(cart, dict):
            cart = {}
        product_name = product.name if isinstance(product, Product) else product["name"]
        if isinstance(product, Product) and request.user.is_authenticated:
            if product.stock < 1:
                messages.error(request, f"{product.name} is out of stock.")
                return redirect_back(request)
            cart_item, created = CartItem.objects.get_or_create(user=request.user, product=product)
            if not created:
                cart_item.quantity += 1
                cart_item.save(update_fields=["quantity"])
            if cart_item.quantity > product.stock:
                cart_item.quantity = product.stock
                cart_item.save(update_fields=["quantity"])
                messages.error(request, f"Only {product.stock} units are available.")
                return redirect_back(request)
        elif isinstance(product, Product):
            key = str(product.pk)
            current_quantity = cart.get(key, 0)
            if not isinstance(current_quantity, int) or isinstance(current_quantity, bool) or current_quantity < 0:
                current_quantity = 0
            if product.stock < 1:
                messages.error(request, f"{product.name} is out of stock.")
                return redirect_back(request)
            if current_quantity >= product.stock:
                cart[key] = product.stock
                request.session["cart"] = cart
                messages.error(request, f"Only {product.stock} units are available.")
                return redirect_back(request)
            cart[key] = current_quantity + 1
        current_quantity = cart.get(str(product_id), 0)
        if not isinstance(current_quantity, int) or isinstance(current_quantity, bool) or current_quantity < 0:
            current_quantity = 0
        if not isinstance(product, Product):
            cart[str(product_id)] = current_quantity + 1
        request.session["cart"] = cart
        messages.success(request, f"{product_name} added to cart.")
    return redirect_back(request)


def toggle_favorite(request, product_id):
    product = get_product(product_id)
    if product is None:
        raise Http404("Product not found")
    if request.method == "POST":
        if isinstance(product, Product) and request.user.is_authenticated:
            favorite = Favorite.objects.filter(user=request.user, product=product).first()
            if favorite:
                favorite.delete()
                messages.success(request, f"{product.name} removed from favorites.")
            else:
                Favorite.objects.create(user=request.user, product=product)
                messages.success(request, f"{product.name} added to favorites.")
            return redirect_back(request)
        favorites = request.session.get("favorites", [])
        if not isinstance(favorites, list):
            favorites = []
        if product_id in favorites:
            favorites.remove(product_id)
            request.session["favorites"] = favorites
            messages.success(request, f"{product['name']} removed from favorites.")
        else:
            favorites.append(product_id)
            request.session["favorites"] = favorites
            messages.success(request, f"{product['name']} added to favorites.")
    return redirect_back(request)


@user_passes_test(is_staff_user, login_url="login")
def product_management(request):
    query = request.GET.get("q", "").strip()
    products = Product.objects.select_related("category").order_by("name")
    if query:
        products = products.filter(name__icontains=query)
    return render(request, "product.html", {
        "initial_search": request.GET.get("q", "").strip(),
        "products": products,
        "categories": Category.objects.order_by("name"),
    })


def workspace_page(request, page_key, title, eyebrow, description, sections=None, stats=None):
    return render(request, "workspace.html", {
        "page_key": page_key,
        "page_title": title,
        "page_eyebrow": eyebrow,
        "page_description": description,
        "sections": sections or [],
        "stats": stats or [],
    })


def overview(request):
    if request.user.is_authenticated:
        cart_count = sum(CartItem.objects.filter(user=request.user).values_list("quantity", flat=True))
    else:
        cart = request.session.get("cart", {})
        cart_count = sum(value for value in cart.values() if isinstance(value, int) and value > 0) if isinstance(cart, dict) else 0
    active_products = Product.objects.filter(is_active=True).count()
    published_reviews = Review.objects.filter(is_published=True).count()
    return workspace_page(
        request, "overview", "Overview", "WORKSPACE SUMMARY",
        "A clear view of your store, customers, and recent activity.",
        sections=[
            {"title": "Shopping activity", "text": f"{cart_count} item{'s' if cart_count != 1 else ''} currently in your cart.", "label": "Open cart", "url": "/orders/"},
            {"title": "Customer feedback", "text": "Review customer sentiment and publish thoughtful responses.", "label": "View reviews", "url": "/reviews/"},
            {"title": "Catalogue health", "text": "Keep product details, stock, and pricing accurate.", "label": "Manage products", "url": "/products/manage/"},
        ],
        stats=[
            {"value": str(active_products if active_products else len(PRODUCTS)), "label": "Active products", "trend": "Catalogue live"},
            {"value": str(cart_count), "label": "Items in cart", "trend": "Updated now"},
            {"value": str(published_reviews), "label": "Published reviews", "trend": "Community feedback"},
        ],
    )


def orders(request):
    cart = request.session.get("cart", {})
    order_items = []
    if request.user.is_authenticated:
        for item in CartItem.objects.filter(user=request.user).select_related("product"):
            order_items.append({
                "product": item.product,
                "quantity": item.quantity,
                "total": f"{item.total:.2f}",
            })
    elif isinstance(cart, dict):
        for product_id, quantity in cart.items():
            product = get_product(int(product_id)) if str(product_id).isdigit() else None
            if product and isinstance(quantity, int) and quantity > 0:
                order_items.append({"product": product, "quantity": quantity, "total": f"{float(product['price']) * quantity:.2f}"})
    sections = [{
        "title": "Current cart",
        "text": f"{sum(item['quantity'] for item in order_items)} items ready for checkout.",
        "label": "Continue shopping",
        "url": "/shop/",
        "items": order_items,
        "checkout_url": "/checkout/",
    }]
    if request.user.is_authenticated:
        past_orders = Order.objects.filter(user=request.user).prefetch_related("items__product")[:5]
        for order in past_orders:
            sections.append({
                "title": f"Order #{order.id}",
                "text": f"{order.status.title()} · ${order.total}",
                "label": "View shop",
                "url": "/shop/",
            })
    return render(request, "workspace.html", {
        "page_key": "orders",
        "page_title": "My orders",
        "page_eyebrow": "ORDER HISTORY",
        "page_description": "Review purchases and keep track of your current cart.",
        "sections": sections,
        "stats": [
            {"value": str(len(order_items)), "label": "Cart products", "trend": "Current session"},
            {"value": str(sum(item["quantity"] for item in order_items)), "label": "Total units", "trend": "Ready to review"},
        ],
        "payment_form": PaymentForm() if order_items else None,
        "form_action": "/checkout/",
        "cart_total": sum(float(item["total"]) for item in order_items),
    })


def rewards(request):
    loyalty = None
    if request.user.is_authenticated:
        loyalty, _ = LoyaltyProfile.objects.get_or_create(user=request.user)
    points = loyalty.points if loyalty else 0
    tier = loyalty.tier if loyalty else "Green"
    if points >= 500:
        tier = "Gold"
    elif points >= 200:
        tier = "Silver"
    next_milestone = 200 if points < 200 else (500 if points < 500 else 1000)
    return workspace_page(
        request, "rewards", "Loyalty & rewards", "MEMBER BENEFITS",
        "Earn points through purchases, reviews, and responsible shopping.",
        sections=[
            {"title": f"{tier} member", "text": f"{points} reward points available in your account.", "label": "Explore rewards", "url": "/shop/"},
            {"title": "Next milestone", "text": f"Earn {max(next_milestone - points, 0)} more points to reach the next tier.", "label": "View catalogue", "url": "/shop/"},
        ],
        stats=[
            {"value": str(points), "label": "Available points", "trend": "+10 from reviews"},
            {"value": str(next_milestone), "label": "Next tier target", "trend": f"{min(round(points / next_milestone * 100), 100)}% complete"},
        ],
    )


def preferences(request):
    if request.user.is_authenticated:
        preference, _ = Preference.objects.get_or_create(user=request.user)
        if request.method == "POST":
            form = PreferenceForm(request.POST, instance=preference)
            if form.is_valid():
                form.save()
                messages.success(request, "Your preferences have been saved.")
                return redirect("my_preferences")
        else:
            form = PreferenceForm(instance=preference)
        return render(request, "workspace.html", {
            "page_key": "preferences",
            "page_title": "My preferences",
            "page_eyebrow": "PERSONALISE RETRAX",
            "page_description": "Choose the updates, categories, and shopping experience you prefer.",
            "sections": [],
            "stats": [],
            "form": form,
        })
    return workspace_page(
        request, "preferences", "My preferences", "PERSONALISE RETRAX",
        "Sign in to save the updates, categories, and shopping experience you prefer.",
        sections=[
            {"title": "Favourite categories", "text": "Choose your favourite shopping categories after signing in.", "label": "Sign in", "url": "/login/?next=/preferences/"},
        ],
    )


@user_passes_test(is_staff_user, login_url="login")
def customers(request):
    User = get_user_model()
    customer_count = User.objects.filter(is_active=True).count()
    review_count = Review.objects.filter(is_published=True).count()
    return workspace_page(
        request, "customers", "Customers", "CUSTOMER DIRECTORY",
        "Understand your community and keep customer records organised.",
        sections=[
            {"title": "Emmanuel Adah", "text": "Green tier member · 120 loyalty points", "label": "View profile", "url": "/orders/"},
            {"title": "Recent activity", "text": f"Customers have published {review_count} reviews and added products to their carts.", "label": "Open reviews", "url": "/reviews/"},
        ],
        stats=[
            {"value": str(customer_count), "label": "Active customers", "trend": "Registered accounts"},
            {"value": "72%", "label": "Returning rate", "trend": "+4%"},
        ],
    )


@user_passes_test(is_staff_user, login_url="login")
def analytics(request):
    return workspace_page(
        request, "analytics", "Retention analytics", "PERFORMANCE INSIGHTS",
        "Track customer activity and identify retention opportunities.",
        sections=[
            {"title": "Retention trend", "text": "Returning customer engagement increased over the past 30 days.", "label": "View customers", "url": "/customers/"},
            {"title": "Reward engagement", "text": "Members who redeem points return more often.", "label": "Manage rewards", "url": "/rewards/"},
        ],
        stats=[
            {"value": "72%", "label": "Returning customers", "trend": "+4%"},
            {"value": "38%", "label": "Reward participation", "trend": "+6%"},
        ],
    )


@user_passes_test(is_staff_user, login_url="login")
def admin_dashboard(request):
    product_count = Product.objects.filter(is_active=True).count()
    customer_count = get_user_model().objects.filter(is_active=True).count()
    review_count = Review.objects.filter(is_published=True).count()
    return workspace_page(
        request, "admin", "Admin dashboard", "STORE OPERATIONS",
        "Monitor catalogue activity and manage the everyday Retrax workspace.",
        sections=[
            {"title": "Product catalogue", "text": f"{product_count} active products are available across the store.", "label": "Manage catalogue", "url": "/products/manage/"},
            {"title": "Customer feedback", "text": "Read recent reviews and keep the community informed.", "label": "Open reviews", "url": "/reviews/"},
            {"title": "Retention", "text": "Use customer trends to improve offers and engagement.", "label": "View analytics", "url": "/analytics/"},
        ],
        stats=[
            {"value": str(product_count), "label": "Products", "trend": "Catalogue live"},
            {"value": str(customer_count), "label": "Customers", "trend": "Registered accounts"},
            {"value": str(review_count), "label": "Reviews", "trend": "Published feedback"},
        ],
    )


@user_passes_test(is_staff_user, login_url="login")
def add_product(request):
    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Product added to the catalogue.")
            return redirect("product_management")
    else:
        form = ProductForm()
    return render(request, "workspace.html", {
        "page_key": "products",
        "page_title": "Add product",
        "page_eyebrow": "CATALOGUE",
        "page_description": "Create a polished product listing for the Retrax catalogue.",
        "sections": [],
        "stats": [],
        "form": form,
        "form_action": request.path,
    })


@user_passes_test(is_staff_user, login_url="login")
def edit_product(request, product_id):
    product = get_product(product_id)
    if product is None:
        raise Http404("Product not found")
    if not isinstance(product, Product):
        return workspace_page(
            request, "products", f"Edit {product['name']}", "CATALOGUE",
            "This fallback demo product is not yet stored in the database.",
            sections=[{"title": product["name"], "text": "Add it as a database product to enable editing.", "label": "Return to catalogue", "url": "/products/manage/"}],
        )
    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Product updated successfully.")
            return redirect("product_management")
    else:
        form = ProductForm(instance=product)
    return render(request, "workspace.html", {
        "page_key": "products",
        "page_title": f"Edit {product.name}",
        "page_eyebrow": "CATALOGUE",
        "page_description": "Update the product information and merchandising details.",
        "sections": [],
        "stats": [],
        "form": form,
        "form_action": request.path,
    })


def reviews_feedback(request):
    reviews = Review.objects.filter(is_published=True).select_related("user", "product")
    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect("/login/?next=/reviews/")
        product = Product.objects.filter(id=request.POST.get("product_id"), is_active=True).first()
        form = ReviewForm(request.POST)
        if product and form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.product = product
            review.save()
            loyalty, _ = LoyaltyProfile.objects.get_or_create(user=request.user)
            loyalty.points += 10
            loyalty.save(update_fields=["points"])
            messages.success(request, "Your review was published and 10 loyalty points were added.")
            return redirect("reviews_feedback")
        messages.error(request, "Please select a valid product and complete the review.")
    return render(request, "reviews.html", {
        "reviews": reviews[:20],
        "review_products": Product.objects.filter(is_active=True).order_by("name"),
        "review_count": reviews.count(),
        "loyalty_points": (
            LoyaltyProfile.objects.get_or_create(user=request.user)[0].points
            if request.user.is_authenticated else 0
        ),
    })


@login_required
def checkout(request):
    if request.method != "POST":
        return redirect("my_orders")
    payment_form = PaymentForm(request.POST)
    if not payment_form.is_valid():
        for field, errors in payment_form.errors.items():
            for error in errors:
                messages.error(request, error)
        return redirect("my_orders")
    cart_items = list(CartItem.objects.filter(user=request.user).select_related("product"))
    if not cart_items:
        messages.error(request, "Your cart is empty.")
        return redirect("my_orders")
    with transaction.atomic():
        total = 0
        points = 0
        locked_items = []
        for item in cart_items:
            product = Product.objects.select_for_update().get(pk=item.product_id)
            if item.quantity > product.stock:
                messages.error(request, f"{product.name} does not have enough stock.")
                return redirect("my_orders")
            locked_items.append((product, item.quantity))
            total += product.price * item.quantity
            points += product.points * item.quantity
        transaction_id = f"RTX-{uuid.uuid4().hex[:12].upper()}"
        order = Order.objects.create(
            user=request.user,
            total=total,
            payment_status="paid",
            payment_method="Card",
            transaction_id=transaction_id,
        )
        for product, quantity in locked_items:
            OrderItem.objects.create(order=order, product=product, quantity=quantity, unit_price=product.price)
            product.stock -= quantity
            product.save(update_fields=["stock", "updated_at"])
        CartItem.objects.filter(user=request.user).delete()
        loyalty, _ = LoyaltyProfile.objects.get_or_create(user=request.user)
        loyalty.points += points
        loyalty.save(update_fields=["points"])
    request.session["cart"] = {}
    messages.success(request, "Order placed successfully.")
    return redirect("my_orders")


def simple_page(name):
    def page(request):
        return HttpResponse(f"<h1>{name}</h1>")
    return page

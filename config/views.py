from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render


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


def get_product(product_id):
    return next((product for product in PRODUCTS if product["id"] == product_id), None)


def shop_products(request):
    category = request.GET.get("category", "all").lower()
    query = request.GET.get("q", "").strip().lower()
    sort = request.GET.get("sort", "")

    products = list(PRODUCTS)
    if category != "all":
        category_name = next((item["name"] for item in CATEGORIES if item["slug"] == category), "")
        products = [product for product in products if product["category"] == category_name]
    if query:
        products = [
            product for product in products
            if query in product["name"].lower() or query in product["category"].lower()
        ]
    if sort == "recommended":
        products.sort(key=lambda product: float(product["rating"]), reverse=True)

    cart = request.session.get("cart", {})
    favorites = request.session.get("favorites", [])

    return render(request, "shop.html", {
        "products": products,
        "categories": CATEGORIES,
        "current_category": category,
        "cart_count": sum(cart.values()),
        "favorite_ids": favorites,
    })


def add_to_cart(request, product_id):
    product = get_product(product_id)
    if product is None:
        raise Http404("Product not found")
    if request.method == "POST":
        cart = request.session.get("cart", {})
        cart[str(product_id)] = cart.get(str(product_id), 0) + 1
        request.session["cart"] = cart
        messages.success(request, f"{product['name']} added to cart.")
    return redirect("shop_products")


def toggle_favorite(request, product_id):
    product = get_product(product_id)
    if product is None:
        raise Http404("Product not found")
    if request.method == "POST":
        favorites = request.session.get("favorites", [])
        if product_id in favorites:
            favorites.remove(product_id)
            request.session["favorites"] = favorites
            messages.success(request, f"{product['name']} removed from favorites.")
        else:
            favorites.append(product_id)
            request.session["favorites"] = favorites
            messages.success(request, f"{product['name']} added to favorites.")
    return redirect("shop_products")


def simple_page(name):
    def page(request):
        return HttpResponse(f"<h1>{name}</h1>")
    return page

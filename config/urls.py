"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# from django.contrib import admin
# from django.urls import path

# urlpatterns = [
#     path('admin/', admin.site.urls),
# ]

from django.urls import include, path
from . import views

urlpatterns = [
    path("", include("account.urls")),
    path("", views.shop_products, name="shop_products"),
    path("shop/", views.shop_products, name="shop_products"),
    path("overview/", views.overview, name="overview"),
    path("orders/", views.orders, name="my_orders"),
    path("rewards/", views.rewards, name="loyalty_rewards"),
    path("preferences/", views.preferences, name="my_preferences"),
    path("reviews/", views.reviews_feedback, name="reviews_feedback"),
    path("admin/", views.admin_dashboard, name="admin_dashboard"),
    path("products/manage/", views.product_management, name="product_management"),
    path("products/add/", views.add_product, name="add_product"),
    path("products/<int:product_id>/edit/", views.edit_product, name="edit_product"),
    path("customers/", views.customers, name="customers"),
    path("analytics/", views.analytics, name="retention_analytics"),
    path("cart/add/<int:product_id>/", views.add_to_cart, name="add_to_cart"),
    path("favorites/toggle/<int:product_id>/", views.toggle_favorite, name="toggle_favorite"),
    path("checkout/", views.checkout, name="checkout"),
]

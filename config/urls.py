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

from django.urls import path
from . import views

urlpatterns = [
    path("", views.shop_products, name="shop_products"),
    path("shop/", views.shop_products, name="shop_products"),
    path("overview/", views.simple_page("Overview"), name="overview"),
    path("orders/", views.simple_page("My orders"), name="my_orders"),
    path("rewards/", views.simple_page("Loyalty & rewards"), name="loyalty_rewards"),
    path("preferences/", views.simple_page("My preferences"), name="my_preferences"),
    path("reviews/", views.simple_page("Reviews & feedback"), name="reviews_feedback"),
    path("admin/", views.simple_page("Admin dashboard"), name="admin_dashboard"),
    path("products/manage/", views.simple_page("Product management"), name="product_management"),
    path("customers/", views.simple_page("Customers"), name="customers"),
    path("analytics/", views.simple_page("Retention analytics"), name="retention_analytics"),
    path("cart/add/<int:product_id>/", views.add_to_cart, name="add_to_cart"),
    path("favorites/toggle/<int:product_id>/", views.toggle_favorite, name="toggle_favorite"),
]

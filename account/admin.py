from django.contrib import admin
from .models import Category, Product, CartItem, Favorite, Order, OrderItem, Review, LoyaltyProfile, Preference


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "stock", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("name", "description")


admin.site.register([CartItem, Favorite, Order, OrderItem, Review, LoyaltyProfile, Preference])

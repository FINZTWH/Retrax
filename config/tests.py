from django.test import Client, TestCase
from django.urls import reverse
from django.contrib.auth.models import User


class ShopPageTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_shop_page_renders(self):
        response = self.client.get(reverse("shop_products"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Find your next favourite")

    def test_search_filters_products(self):
        response = self.client.get(reverse("shop_products"), {"q": "mug"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ceramic Coffee Mug")
        self.assertNotContains(response, "Botanical Candle")

    def test_invalid_category_falls_back_to_all(self):
        response = self.client.get(reverse("shop_products"), {"category": "invalid"})
        self.assertEqual(response.context["current_category"], "all")
        self.assertEqual(len(response.context["products"]), 8)

    def test_add_to_cart_requires_post_and_returns_to_filter(self):
        target = reverse("add_to_cart", args=[1])
        self.assertEqual(self.client.get(target).status_code, 302)
        response = self.client.post(
            target,
            {"next": "/shop/?category=home&q=mug"},
        )
        self.assertRedirects(response, "/shop/?category=home&q=mug", fetch_redirect_response=False)
        self.assertEqual(self.client.session["cart"]["1"], 1)

    def test_rejects_external_redirect_after_cart_action(self):
        response = self.client.post(
            reverse("add_to_cart", args=[1]),
            {"next": "https://example.com/"},
        )
        self.assertRedirects(response, reverse("shop_products"), fetch_redirect_response=False)

    def test_shop_shows_guest_auth_links(self):
        response = self.client.get(reverse("shop_products"))
        self.assertContains(response, reverse("login"))
        self.assertContains(response, reverse("register"))

    def test_registration_creates_authenticated_member(self):
        response = self.client.post(reverse("register"), {
            "username": "newmember",
            "first_name": "New",
            "last_name": "Member",
            "email": "member@example.com",
            "password1": "Retrax-Test-123!",
            "password2": "Retrax-Test-123!",
        })
        self.assertRedirects(response, reverse("shop_products"), fetch_redirect_response=False)
        self.assertTrue(User.objects.filter(username="newmember").exists())
        self.assertTrue(self.client.session["_auth_user_id"])

    def test_workspace_routes_render_templates(self):
        routes = [
            "overview",
            "my_orders",
            "loyalty_rewards",
            "my_preferences",
            "reviews_feedback",
        ]
        for route in routes:
            with self.subTest(route=route):
                response = self.client.get(reverse(route))
                self.assertEqual(response.status_code, 200)

    def test_management_routes_require_staff(self):
        routes = [
            "admin_dashboard",
            "product_management",
            "add_product",
            "customers",
            "retention_analytics",
        ]
        for route in routes:
            with self.subTest(route=route):
                response = self.client.get(reverse(route))
                self.assertEqual(response.status_code, 302)

    def test_staff_can_open_management_routes(self):
        staff = User.objects.create_user("staff", password="testpass123", is_staff=True)
        self.client.force_login(staff)
        for route in ["admin_dashboard", "product_management", "add_product", "customers", "retention_analytics"]:
            with self.subTest(route=route):
                response = self.client.get(reverse(route))
                self.assertEqual(response.status_code, 200)

    def test_shop_and_product_management_render_separate_templates(self):
        shop_response = self.client.get(reverse("shop_products"))
        self.assertTemplateUsed(shop_response, "shop.html")
        self.assertTemplateNotUsed(shop_response, "product.html")
        self.assertContains(shop_response, "Find your next favourite")

        staff = User.objects.create_user("template_staff", password="testpass123", is_staff=True)
        self.client.force_login(staff)
        management_response = self.client.get(reverse("product_management"))
        self.assertTemplateUsed(management_response, "product.html")
        self.assertTemplateNotUsed(management_response, "shop.html")
        self.assertContains(management_response, "Product management")

    def test_sign_in_rejects_external_next_redirect(self):
        user = User.objects.create_user("member", password="testpass123")
        response = self.client.post(
            reverse("login"),
            {"username": "member", "password": "testpass123", "next": "https://example.com"},
        )
        self.assertRedirects(response, reverse("shop_products"), fetch_redirect_response=False)

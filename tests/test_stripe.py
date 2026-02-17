"""Tests for Stripe payment integration."""

from __future__ import annotations

import json
import pytest
from unittest.mock import patch, MagicMock


class TestStripeAvailability:
    """Test Stripe availability detection."""

    def test_stripe_not_available_without_key(self, app):
        with app.app_context():
            from stripe_integration import is_stripe_available
            # Test config has no STRIPE_SECRET_KEY
            assert is_stripe_available() is False

    def test_stripe_available_with_key(self, app):
        app.config["STRIPE_SECRET_KEY"] = "sk_test_fake"
        with app.app_context():
            from stripe_integration import is_stripe_available
            assert is_stripe_available() is True


class TestCustomerManagement:
    """Test Stripe customer creation and retrieval."""

    @patch("stripe_integration._get_stripe")
    def test_create_new_customer(self, mock_get_stripe, app):
        mock_stripe = MagicMock()
        mock_stripe.Customer.create.return_value = MagicMock(id="cus_test123")
        mock_get_stripe.return_value = mock_stripe

        app.config["STRIPE_SECRET_KEY"] = "sk_test_fake"
        with app.app_context():
            from stripe_integration import get_or_create_customer
            customer_id = get_or_create_customer(1, "test@example.com", "Test")
            assert customer_id == "cus_test123"
            mock_stripe.Customer.create.assert_called_once()

    @patch("stripe_integration._get_stripe")
    def test_existing_customer_reused(self, mock_get_stripe, app):
        mock_stripe = MagicMock()
        mock_get_stripe.return_value = mock_stripe

        app.config["STRIPE_SECRET_KEY"] = "sk_test_fake"
        with app.app_context():
            from database import get_db
            db = get_db()
            db.execute("UPDATE users SET stripe_customer_id = 'cus_existing' WHERE id = 1")
            db.commit()

            from stripe_integration import get_or_create_customer
            customer_id = get_or_create_customer(1, "test@example.com")
            assert customer_id == "cus_existing"
            mock_stripe.Customer.create.assert_not_called()


class TestCheckoutSessions:
    """Test Stripe checkout session creation."""

    @patch("stripe_integration._get_stripe")
    def test_create_subscription_checkout(self, mock_get_stripe, app):
        mock_stripe = MagicMock()
        mock_stripe.Customer.create.return_value = MagicMock(id="cus_test")
        mock_stripe.checkout.Session.create.return_value = MagicMock(
            id="cs_test123", url="https://checkout.stripe.com/test"
        )
        mock_get_stripe.return_value = mock_stripe

        app.config["STRIPE_SECRET_KEY"] = "sk_test_fake"
        with app.app_context():
            import stripe_integration
            stripe_integration.PLAN_STRIPE_PRICES["explorer"]["monthly"] = "price_explorer_mo"

            from stripe_integration import create_checkout_session
            result = create_checkout_session(1, "test@example.com", "explorer", "monthly")
            assert result["session_id"] == "cs_test123"
            assert result["url"] == "https://checkout.stripe.com/test"

    @patch("stripe_integration._get_stripe")
    def test_create_credit_checkout(self, mock_get_stripe, app):
        mock_stripe = MagicMock()
        mock_stripe.Customer.create.return_value = MagicMock(id="cus_test")
        mock_stripe.checkout.Session.create.return_value = MagicMock(
            id="cs_credits", url="https://checkout.stripe.com/credits"
        )
        mock_get_stripe.return_value = mock_stripe

        app.config["STRIPE_SECRET_KEY"] = "sk_test_fake"
        with app.app_context():
            import stripe_integration
            stripe_integration.CREDIT_PACK_PRICES[100] = "price_credits_100"

            from stripe_integration import create_credit_checkout
            result = create_credit_checkout(1, "test@example.com", 100)
            assert result["session_id"] == "cs_credits"

    def test_checkout_invalid_plan(self, app):
        app.config["STRIPE_SECRET_KEY"] = "sk_test_fake"
        with app.app_context():
            from stripe_integration import create_checkout_session
            with pytest.raises(ValueError, match="No Stripe price"):
                create_checkout_session(1, "test@example.com", "nonexistent", "monthly")


class TestPortalSession:
    """Test Stripe customer portal."""

    @patch("stripe_integration._get_stripe")
    def test_create_portal_session(self, mock_get_stripe, app):
        mock_stripe = MagicMock()
        mock_stripe.Customer.create.return_value = MagicMock(id="cus_test")
        mock_stripe.billing_portal.Session.create.return_value = MagicMock(
            url="https://billing.stripe.com/portal"
        )
        mock_get_stripe.return_value = mock_stripe

        app.config["STRIPE_SECRET_KEY"] = "sk_test_fake"
        with app.app_context():
            from stripe_integration import create_portal_session
            result = create_portal_session(1, "test@example.com")
            assert result["url"] == "https://billing.stripe.com/portal"


class TestWebhookHandling:
    """Test Stripe webhook event processing."""

    def test_checkout_completed_subscription(self, app):
        """checkout.session.completed with subscription mode activates plan."""
        with app.app_context():
            from stripe_integration import handle_webhook_event
            event = {
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "mode": "subscription",
                        "subscription": "sub_test123",
                        "metadata": {
                            "user_id": "1",
                            "plan_id": "explorer",
                        },
                    }
                },
            }
            result = handle_webhook_event(event)
            assert result["action"] == "subscription_activated"
            assert result["plan_id"] == "explorer"

            # Verify plan was actually upgraded
            from subscription_store import SubscriptionStoreDB
            store = SubscriptionStoreDB(1)
            assert store.current_plan()["plan_id"] == "explorer"

    def test_checkout_completed_credits(self, app):
        """checkout.session.completed with payment mode adds credits."""
        with app.app_context():
            from stripe_integration import handle_webhook_event
            from credit_store import CreditStoreDB

            initial = CreditStoreDB(1).balance()

            event = {
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "mode": "payment",
                        "metadata": {
                            "user_id": "1",
                            "credit_amount": "500",
                            "type": "credit_purchase",
                        },
                    }
                },
            }
            result = handle_webhook_event(event)
            assert result["action"] == "credits_purchased"
            assert result["amount"] == 500
            assert CreditStoreDB(1).balance() == initial + 500

    def test_subscription_deleted(self, app):
        """customer.subscription.deleted cancels and downgrades."""
        with app.app_context():
            from subscription_store import SubscriptionStoreDB
            store = SubscriptionStoreDB(1)
            store.upgrade("scholar")

            from stripe_integration import handle_webhook_event
            event = {
                "type": "customer.subscription.deleted",
                "data": {
                    "object": {
                        "metadata": {"user_id": "1"},
                    }
                },
            }
            result = handle_webhook_event(event)
            assert result["action"] == "subscription_cancelled"
            assert store.current_plan()["plan_id"] == "free"

    def test_subscription_updated(self, app):
        """customer.subscription.updated with active status upgrades."""
        with app.app_context():
            from stripe_integration import handle_webhook_event
            event = {
                "type": "customer.subscription.updated",
                "data": {
                    "object": {
                        "status": "active",
                        "metadata": {
                            "user_id": "1",
                            "plan_id": "diploma_pass",
                        },
                    }
                },
            }
            result = handle_webhook_event(event)
            assert result["action"] == "subscription_updated"

    def test_payment_failed_notification(self, app):
        """invoice.payment_failed creates notification for user."""
        with app.app_context():
            from database import get_db
            db = get_db()
            db.execute("UPDATE users SET stripe_customer_id = 'cus_fail' WHERE id = 1")
            db.commit()

            from stripe_integration import handle_webhook_event
            event = {
                "type": "invoice.payment_failed",
                "data": {
                    "object": {
                        "customer": "cus_fail",
                    }
                },
            }
            result = handle_webhook_event(event)
            assert result["action"] == "payment_failed_notified"

    def test_invoice_paid_allocates_credits(self, app):
        """invoice.payment_succeeded allocates monthly credits."""
        with app.app_context():
            from database import get_db
            from subscription_store import SubscriptionStoreDB
            from credit_store import CreditStoreDB

            db = get_db()
            db.execute("UPDATE users SET stripe_customer_id = 'cus_renew' WHERE id = 1")
            db.commit()

            SubscriptionStoreDB(1).upgrade("explorer")
            balance_before = CreditStoreDB(1).balance()

            from stripe_integration import handle_webhook_event
            event = {
                "type": "invoice.payment_succeeded",
                "data": {
                    "object": {
                        "customer": "cus_renew",
                    }
                },
            }
            result = handle_webhook_event(event)
            assert result["action"] == "credits_allocated"
            assert CreditStoreDB(1).balance() > balance_before

    def test_unknown_event_ignored(self, app):
        with app.app_context():
            from stripe_integration import handle_webhook_event
            event = {
                "type": "some.unknown.event",
                "data": {"object": {}},
            }
            result = handle_webhook_event(event)
            assert result["action"] == "ignored"

    def test_missing_user_id_skipped(self, app):
        with app.app_context():
            from stripe_integration import handle_webhook_event
            event = {
                "type": "checkout.session.completed",
                "data": {"object": {"mode": "subscription", "metadata": {}}},
            }
            result = handle_webhook_event(event)
            assert result["action"] == "skipped"


class TestWebhookEndpoint:
    """Test the webhook HTTP endpoint."""

    def test_webhook_without_stripe_returns_503(self, client):
        resp = client.post("/api/billing/webhook", data=b"test")
        assert resp.status_code == 503

    def test_webhook_without_secret_returns_500(self, app):
        app.config["STRIPE_SECRET_KEY"] = "sk_test_fake"
        app.config["STRIPE_WEBHOOK_SECRET"] = ""
        client = app.test_client()
        with client:
            resp = client.post(
                "/api/billing/webhook",
                data=b'{"type": "test"}',
                headers={"Stripe-Signature": "t=123,v1=abc"},
            )
            assert resp.status_code == 500


class TestBillingEndpointsStripe:
    """Test billing endpoint behavior with Stripe unavailable."""

    def test_checkout_returns_503_without_stripe(self, auth_client):
        resp = auth_client.post("/api/billing/checkout", json={
            "plan_id": "explorer",
            "interval": "monthly",
        })
        assert resp.status_code == 503

    def test_portal_returns_503_without_stripe(self, auth_client):
        resp = auth_client.post("/api/billing/portal")
        assert resp.status_code == 503

    def test_credit_buy_returns_503_without_stripe(self, auth_client):
        resp = auth_client.post("/api/credits/buy", json={"amount": 100})
        assert resp.status_code == 503

    def test_checkout_missing_plan_id(self, auth_client, app):
        """Even if Stripe were available, missing plan_id should return 400."""
        app.config["STRIPE_SECRET_KEY"] = "sk_test_fake"
        resp = auth_client.post("/api/billing/checkout", json={
            "interval": "monthly",
        })
        assert resp.status_code == 400

    def test_checkout_invalid_interval(self, auth_client, app):
        app.config["STRIPE_SECRET_KEY"] = "sk_test_fake"
        resp = auth_client.post("/api/billing/checkout", json={
            "plan_id": "explorer",
            "interval": "weekly",
        })
        assert resp.status_code == 400

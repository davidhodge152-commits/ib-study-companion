"""Comprehensive billing, subscription, and credit tests."""

from __future__ import annotations

import pytest


class TestCreditStore:
    """Test CreditStoreDB operations."""

    def test_initial_balance_is_zero(self, app):
        with app.app_context():
            from credit_store import CreditStoreDB
            store = CreditStoreDB(1)
            assert store.balance() == 0

    def test_credit_increases_balance(self, app):
        with app.app_context():
            from credit_store import CreditStoreDB
            store = CreditStoreDB(1)
            result = store.credit(100, "purchase", "Test purchase")
            assert result["success"] is True
            assert result["balance_after"] == 100
            assert store.balance() == 100

    def test_debit_decreases_balance(self, app):
        with app.app_context():
            from credit_store import CreditStoreDB
            store = CreditStoreDB(1)
            store.credit(200, "purchase", "Setup")
            result = store.debit(50, "oral_practice", "Test debit")
            assert result["success"] is True
            assert result["balance_after"] == 150

    def test_debit_insufficient_funds(self, app):
        with app.app_context():
            from credit_store import CreditStoreDB
            store = CreditStoreDB(1)
            result = store.debit(1000, "oral_practice", "Too much")
            assert result["success"] is False
            assert result["tx_id"] is None

    def test_has_credits(self, app):
        with app.app_context():
            from credit_store import CreditStoreDB
            store = CreditStoreDB(1)
            assert store.has_credits(1) is False
            store.credit(50, "purchase")
            assert store.has_credits(50) is True
            assert store.has_credits(51) is False

    def test_transaction_history(self, app):
        with app.app_context():
            from credit_store import CreditStoreDB
            store = CreditStoreDB(1)
            store.credit(100, "purchase", "First")
            store.credit(50, "purchase", "Second")
            store.debit(25, "oral_practice", "Usage")
            history = store.transaction_history(limit=10)
            assert len(history) >= 3
            # Most recent first
            assert history[0]["description"] == "Usage"

    def test_allocate_monthly(self, app):
        with app.app_context():
            from credit_store import CreditStoreDB
            store = CreditStoreDB(1)
            store.allocate_monthly(200)
            assert store.balance() == 200
            # Second allocation adds to balance
            store.allocate_monthly(200)
            assert store.balance() == 400

    def test_multiple_users_isolated(self, app):
        """Credits for one user don't affect another."""
        with app.app_context():
            from credit_store import CreditStoreDB
            from database import get_db
            db = get_db()
            db.execute(
                "INSERT OR IGNORE INTO users (id, name, email, created_at) VALUES (99, 'Other', 'other@test.com', '2026-01-01')"
            )
            db.commit()

            store1 = CreditStoreDB(1)
            store2 = CreditStoreDB(99)
            store1.credit(500, "purchase")
            assert store2.balance() == 0


class TestSubscriptionStore:
    """Test SubscriptionStoreDB operations."""

    def test_default_plan_is_free(self, app):
        with app.app_context():
            from subscription_store import SubscriptionStoreDB
            store = SubscriptionStoreDB(1)
            plan = store.current_plan()
            assert plan["plan_id"] == "free"

    def test_upgrade_to_explorer(self, app):
        with app.app_context():
            from subscription_store import SubscriptionStoreDB
            store = SubscriptionStoreDB(1)
            store.upgrade("explorer")
            plan = store.current_plan()
            assert plan["plan_id"] == "explorer"

    def test_upgrade_to_scholar(self, app):
        with app.app_context():
            from subscription_store import SubscriptionStoreDB
            store = SubscriptionStoreDB(1)
            store.upgrade("scholar")
            assert store.current_plan()["plan_id"] == "scholar"

    def test_upgrade_to_diploma_pass(self, app):
        with app.app_context():
            from subscription_store import SubscriptionStoreDB
            store = SubscriptionStoreDB(1)
            store.upgrade("diploma_pass")
            assert store.current_plan()["plan_id"] == "diploma_pass"

    def test_invalid_plan_raises(self, app):
        with app.app_context():
            from subscription_store import SubscriptionStoreDB
            store = SubscriptionStoreDB(1)
            with pytest.raises(ValueError):
                store.upgrade("nonexistent_plan")

    def test_cancel_subscription(self, app):
        with app.app_context():
            from subscription_store import SubscriptionStoreDB
            store = SubscriptionStoreDB(1)
            store.upgrade("explorer")
            store.cancel()
            plan = store.current_plan()
            assert plan["status"] == "cancelled"

    def test_feature_allowed_free(self, app):
        with app.app_context():
            from subscription_store import SubscriptionStoreDB
            store = SubscriptionStoreDB(1)
            assert store.is_feature_allowed("grading") is True
            assert store.is_feature_allowed("oral_practice") is False
            assert store.is_feature_allowed("examiner_review") is False

    def test_feature_allowed_explorer(self, app):
        with app.app_context():
            from subscription_store import SubscriptionStoreDB
            store = SubscriptionStoreDB(1)
            store.upgrade("explorer")
            assert store.is_feature_allowed("oral_practice") is True
            assert store.is_feature_allowed("examiner_review") is False

    def test_feature_allowed_diploma_pass(self, app):
        with app.app_context():
            from subscription_store import SubscriptionStoreDB
            store = SubscriptionStoreDB(1)
            store.upgrade("diploma_pass")
            # diploma_pass has "all"
            assert store.is_feature_allowed("oral_practice") is True
            assert store.is_feature_allowed("examiner_review") is True
            assert store.is_feature_allowed("anything") is True

    def test_plan_limits(self, app):
        with app.app_context():
            from subscription_store import SubscriptionStoreDB
            store = SubscriptionStoreDB(1)
            limits = store.plan_limits()
            assert "plan_id" in limits
            assert "monthly_credits" in limits
            assert "features" in limits
            assert "max_subjects" in limits

    def test_upgrade_allocates_credits(self, app):
        with app.app_context():
            from subscription_store import SubscriptionStoreDB
            from credit_store import CreditStoreDB
            sub = SubscriptionStoreDB(1)
            credits = CreditStoreDB(1)
            initial = credits.balance()
            sub.upgrade("explorer")
            # Explorer gets 200 monthly credits
            assert credits.balance() == initial + 200


class TestBillingEndpoints:
    """Test billing API endpoints."""

    def test_credits_balance(self, auth_client):
        resp = auth_client.get("/api/credits/balance")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "balance" in data
        assert "transactions" in data

    def test_credits_purchase(self, auth_client):
        resp = auth_client.post("/api/credits/purchase", json={"amount": 100})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["balance_after"] >= 100

    def test_credits_purchase_invalid_amount(self, auth_client):
        resp = auth_client.post("/api/credits/purchase", json={"amount": -5})
        assert resp.status_code == 400

    def test_subscription_current(self, auth_client):
        resp = auth_client.get("/api/subscription/current")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "plan" in data
        assert "limits" in data

    def test_subscription_upgrade(self, auth_client):
        resp = auth_client.post("/api/subscription/upgrade", json={"plan_id": "explorer"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True

    def test_subscription_upgrade_invalid(self, auth_client):
        resp = auth_client.post("/api/subscription/upgrade", json={"plan_id": "invalid"})
        assert resp.status_code == 400

    def test_subscription_upgrade_no_plan(self, auth_client):
        resp = auth_client.post("/api/subscription/upgrade", json={})
        assert resp.status_code == 400

    def test_billing_history(self, auth_client):
        resp = auth_client.get("/api/billing/history")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "subscription" in data
        assert "balance" in data
        assert "transactions" in data

    def test_stripe_checkout_without_stripe(self, auth_client):
        """Stripe checkout should return 503 when Stripe is not configured."""
        resp = auth_client.post("/api/billing/checkout", json={
            "plan_id": "explorer",
            "interval": "monthly",
        })
        assert resp.status_code == 503

    def test_stripe_portal_without_stripe(self, auth_client):
        resp = auth_client.post("/api/billing/portal")
        assert resp.status_code == 503

    def test_stripe_credit_buy_without_stripe(self, auth_client):
        resp = auth_client.post("/api/credits/buy", json={"amount": 100})
        assert resp.status_code == 503


class TestFeatureGating:
    """Test subscription-based feature gating."""

    def test_free_tier_limits(self, auth_client):
        """Free tier should have access to basic features only."""
        resp = auth_client.get("/api/subscription/current")
        data = resp.get_json()
        features = data["limits"]["features"]
        assert "grading" in features
        assert "flashcards" in features

    def test_upgrade_unlocks_features(self, auth_client):
        """Upgrading should unlock additional features."""
        auth_client.post("/api/subscription/upgrade", json={"plan_id": "scholar"})
        resp = auth_client.get("/api/subscription/current")
        data = resp.get_json()
        features = data["limits"]["features"]
        assert "oral_practice" in features
        assert "admissions" in features

"""
Tests for restocking API endpoints.
"""

import pytest

import main


@pytest.fixture(autouse=True)
def clear_restock_orders():
    """Submitted orders are module-level state; reset them so tests stay independent."""
    main.restock_orders.clear()
    yield
    main.restock_orders.clear()


def get_recommendations(client, budget):
    response = client.get(f"/api/restocking/recommendations?budget={budget}")
    assert response.status_code == 200
    return response.json()


class TestRestockRecommendationEndpoints:
    """Test suite for restocking recommendation endpoints."""

    def test_get_recommendations_structure(self, client):
        """Test the recommendation response structure."""
        data = get_recommendations(client, 10000)

        for field in [
            "budget",
            "total_cost",
            "remaining_budget",
            "total_shortfall_cost",
            "items",
        ]:
            assert field in data
        assert isinstance(data["items"], list)
        assert len(data["items"]) > 0

        for item in data["items"]:
            for field in [
                "sku",
                "name",
                "category",
                "warehouse",
                "trend",
                "quantity_on_hand",
                "forecasted_demand",
                "shortfall",
                "recommended_quantity",
                "unit_cost",
                "line_total",
                "lead_time_days",
            ]:
                assert field in item
            assert isinstance(item["recommended_quantity"], int)
            assert item["recommended_quantity"] > 0

    def test_recommendations_stay_within_budget(self, client):
        """Test that planned spend never exceeds the budget."""
        for budget in [0, 50, 1000, 10000, 25000, 1000000]:
            data = get_recommendations(client, budget)
            assert data["total_cost"] <= budget + 0.01
            assert abs(data["total_cost"] + data["remaining_budget"] - budget) < 0.01

    def test_recommendation_line_total_calculation(self, client):
        """Test that line totals and the total cost add up."""
        data = get_recommendations(client, 25000)

        for item in data["items"]:
            assert (
                abs(
                    item["line_total"]
                    - item["recommended_quantity"] * item["unit_cost"]
                )
                < 0.01
            )
        assert (
            abs(data["total_cost"] - sum(i["line_total"] for i in data["items"])) < 0.01
        )

    def test_recommendations_never_exceed_shortfall(self, client):
        """Test that quantities are capped at the forecast shortfall."""
        data = get_recommendations(client, 1000000)

        for item in data["items"]:
            assert (
                item["shortfall"]
                == item["forecasted_demand"] - item["quantity_on_hand"]
            )
            assert item["recommended_quantity"] <= item["shortfall"]

    def test_unlimited_budget_covers_every_shortfall(self, client):
        """Test that a large budget fully funds every item and costs total_shortfall_cost."""
        data = get_recommendations(client, 1000000)

        for item in data["items"]:
            assert item["recommended_quantity"] == item["shortfall"]
        assert abs(data["total_cost"] - data["total_shortfall_cost"]) < 0.01

    def test_recommendations_only_include_items_with_shortfall(self, client):
        """Test that items with enough stock are never recommended."""
        inventory = {i["sku"]: i for i in client.get("/api/inventory").json()}
        forecasts = client.get("/api/demand").json()
        expected_skus = {
            f["item_sku"]
            for f in forecasts
            if f["forecasted_demand"] > inventory[f["item_sku"]]["quantity_on_hand"]
        }

        data = get_recommendations(client, 1000000)
        assert {i["sku"] for i in data["items"]} == expected_skus

    def test_increasing_trend_is_funded_first(self, client):
        """Test that a tight budget goes to increasing-demand items first."""
        full = get_recommendations(client, 1000000)
        increasing_cost = sum(
            i["line_total"] for i in full["items"] if i["trend"] == "increasing"
        )

        data = get_recommendations(client, increasing_cost)
        assert len(data["items"]) > 0
        assert all(i["trend"] == "increasing" for i in data["items"])

    def test_zero_budget_returns_no_items(self, client):
        """Test that a zero budget recommends nothing."""
        data = get_recommendations(client, 0)
        assert data["items"] == []
        assert data["total_cost"] == 0

    def test_recommendation_lead_times_by_category(self, client):
        """Test that lead times come from the category table."""
        data = get_recommendations(client, 1000000)

        for item in data["items"]:
            assert (
                item["lead_time_days"] == main.CATEGORY_LEAD_TIME_DAYS[item["category"]]
            )

    def test_negative_budget_rejected(self, client):
        """Test that a negative budget is a validation error."""
        response = client.get("/api/restocking/recommendations?budget=-1")
        assert response.status_code == 422

    def test_missing_budget_rejected(self, client):
        """Test that budget is required."""
        response = client.get("/api/restocking/recommendations")
        assert response.status_code == 422


class TestRestockOrderEndpoints:
    """Test suite for restocking order endpoints."""

    def test_get_restock_orders_empty(self, client):
        """Test that there are no submitted orders initially."""
        response = client.get("/api/restocking/orders")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_restock_order(self, client):
        """Test submitting an order built from recommendations."""
        recommendations = get_recommendations(client, 25000)
        lines = [
            {"sku": i["sku"], "quantity": i["recommended_quantity"]}
            for i in recommendations["items"]
        ]

        response = client.post("/api/restocking/orders", json={"items": lines})
        assert response.status_code == 201

        order = response.json()
        assert order["status"] == "Submitted"
        assert order["order_number"].startswith("RST-")
        assert len(order["items"]) == len(lines)
        assert abs(order["total_cost"] - recommendations["total_cost"]) < 0.01

    def test_restock_order_lead_time_is_slowest_item(self, client):
        """Test that the order lead time is the longest item lead time."""
        # SRV-301 is an Actuator (21 days), PSU-507 a Power Supply (7 days)
        response = client.post(
            "/api/restocking/orders",
            json={
                "items": [
                    {"sku": "SRV-301", "quantity": 5},
                    {"sku": "PSU-507", "quantity": 5},
                ]
            },
        )
        order = response.json()

        assert order["lead_time_days"] == 21
        assert "T" in order["submitted_date"]
        assert order["expected_delivery"] > order["submitted_date"]

    def test_restock_order_uses_server_prices(self, client):
        """Test that line totals are priced from inventory."""
        inventory = {i["sku"]: i for i in client.get("/api/inventory").json()}
        response = client.post(
            "/api/restocking/orders",
            json={"items": [{"sku": "TMP-201", "quantity": 3}]},
        )
        item = response.json()["items"][0]

        assert item["unit_cost"] == inventory["TMP-201"]["unit_cost"]
        assert abs(item["line_total"] - 3 * inventory["TMP-201"]["unit_cost"]) < 0.01

    def test_submitted_orders_listed_newest_first(self, client):
        """Test that submitted orders appear in the list, newest first."""
        first = client.post(
            "/api/restocking/orders",
            json={"items": [{"sku": "TMP-201", "quantity": 1}]},
        ).json()
        second = client.post(
            "/api/restocking/orders",
            json={"items": [{"sku": "PSU-507", "quantity": 1}]},
        ).json()

        data = client.get("/api/restocking/orders").json()
        assert [o["id"] for o in data] == [second["id"], first["id"]]

    def test_create_restock_order_unknown_sku(self, client):
        """Test that an unknown SKU is rejected."""
        response = client.post(
            "/api/restocking/orders",
            json={"items": [{"sku": "NOPE-999", "quantity": 1}]},
        )
        assert response.status_code == 400
        assert "NOPE-999" in response.json()["detail"]

    def test_create_restock_order_empty_items(self, client):
        """Test that an order needs at least one item."""
        response = client.post("/api/restocking/orders", json={"items": []})
        assert response.status_code == 422

    def test_create_restock_order_non_positive_quantity(self, client):
        """Test that quantities must be positive."""
        response = client.post(
            "/api/restocking/orders",
            json={"items": [{"sku": "TMP-201", "quantity": 0}]},
        )
        assert response.status_code == 422

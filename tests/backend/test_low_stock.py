"""
Tests for the low-stock alerts endpoint.
"""


class TestLowStockEndpoint:
    """Test suite for /api/inventory/low-stock."""

    def test_returns_only_items_at_or_below_reorder_point(self, client):
        response = client.get("/api/inventory/low-stock")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        for item in data:
            assert item["quantity_on_hand"] <= item["reorder_point"]
            assert item["shortfall"] == item["reorder_point"] - item["quantity_on_hand"]

    def test_matches_full_inventory(self, client):
        """Every low item in the full inventory appears, and nothing else."""
        inventory = client.get("/api/inventory").json()
        expected = {
            i["id"] for i in inventory if i["quantity_on_hand"] <= i["reorder_point"]
        }
        actual = {i["id"] for i in client.get("/api/inventory/low-stock").json()}
        assert actual == expected

    def test_sorted_most_urgent_first(self, client):
        data = client.get("/api/inventory/low-stock").json()
        ratios = [i["quantity_on_hand"] / max(i["reorder_point"], 1) for i in data]
        assert ratios == sorted(ratios)

    def test_severity(self, client):
        for item in client.get("/api/inventory/low-stock").json():
            critical = item["quantity_on_hand"] <= item["reorder_point"] / 2
            assert item["severity"] == ("critical" if critical else "low")

    def test_filter_by_warehouse(self, client):
        data = client.get("/api/inventory/low-stock?warehouse=Tokyo").json()
        for item in data:
            assert item["warehouse"] == "Tokyo"

    def test_filter_by_category_case_insensitive(self, client):
        data = client.get("/api/inventory/low-stock?category=sensors").json()
        for item in data:
            assert item["category"] == "Sensors"

    def test_all_means_no_filter(self, client):
        unfiltered = client.get("/api/inventory/low-stock").json()
        all_filter = client.get(
            "/api/inventory/low-stock?warehouse=all&category=all"
        ).json()
        assert unfiltered == all_filter

    def test_does_not_shadow_item_route(self, client):
        """The item-by-id route must still work after adding /low-stock."""
        assert client.get("/api/inventory/1").status_code == 200

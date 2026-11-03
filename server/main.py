from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel, Field
from mock_data import (
    inventory_items,
    orders,
    demand_forecasts,
    backlog_items,
    spending_summary,
    monthly_spending,
    category_spending,
    recent_transactions,
    purchase_orders,
)

app = FastAPI(title="Factory Inventory Management System")

# Quarter mapping for date filtering
QUARTER_MAP = {
    "Q1-2025": ["2025-01", "2025-02", "2025-03"],
    "Q2-2025": ["2025-04", "2025-05", "2025-06"],
    "Q3-2025": ["2025-07", "2025-08", "2025-09"],
    "Q4-2025": ["2025-10", "2025-11", "2025-12"],
}


def filter_by_month(items: list, month: Optional[str]) -> list:
    """Filter items by month/quarter based on order_date field"""
    if not month or month == "all":
        return items

    if month.startswith("Q"):
        # Handle quarters
        if month in QUARTER_MAP:
            months = QUARTER_MAP[month]
            return [
                item
                for item in items
                if any(m in item.get("order_date", "") for m in months)
            ]
    else:
        # Direct month match
        return [item for item in items if month in item.get("order_date", "")]

    return items


def apply_filters(
    items: list,
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
) -> list:
    """Apply common filters to a list of items"""
    filtered = items

    if warehouse and warehouse != "all":
        filtered = [item for item in filtered if item.get("warehouse") == warehouse]

    if category and category != "all":
        filtered = [
            item
            for item in filtered
            if item.get("category", "").lower() == category.lower()
        ]

    if status and status != "all":
        filtered = [
            item
            for item in filtered
            if item.get("status", "").lower() == status.lower()
        ]

    return filtered


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Data models
class InventoryItem(BaseModel):
    id: str
    sku: str
    name: str
    category: str
    warehouse: str
    quantity_on_hand: int
    reorder_point: int
    unit_cost: float
    location: str
    last_updated: str


class Order(BaseModel):
    id: str
    order_number: str
    customer: str
    items: List[dict]
    status: str
    order_date: str
    expected_delivery: str
    total_value: float
    actual_delivery: Optional[str] = None
    warehouse: Optional[str] = None
    category: Optional[str] = None


class DemandForecast(BaseModel):
    id: str
    item_sku: str
    item_name: str
    current_demand: int
    forecasted_demand: int
    trend: str
    period: str


class BacklogItem(BaseModel):
    id: str
    order_id: str
    item_sku: str
    item_name: str
    quantity_needed: int
    quantity_available: int
    days_delayed: int
    priority: str
    has_purchase_order: Optional[bool] = False


class PurchaseOrder(BaseModel):
    id: str
    backlog_item_id: str
    supplier_name: str
    quantity: int
    unit_cost: float
    expected_delivery_date: str
    status: str
    created_date: str
    notes: Optional[str] = None


class CreatePurchaseOrderRequest(BaseModel):
    backlog_item_id: str
    supplier_name: str
    quantity: int
    unit_cost: float
    expected_delivery_date: str
    notes: Optional[str] = None


# API endpoints
@app.get("/")
def root():
    return {"message": "Factory Inventory Management System API", "version": "1.0.0"}


@app.get("/api/inventory", response_model=List[InventoryItem])
def get_inventory(warehouse: Optional[str] = None, category: Optional[str] = None):
    """Get all inventory items with optional filtering"""
    return apply_filters(inventory_items, warehouse, category)


class LowStockItem(InventoryItem):
    shortfall: int
    severity: str


# Declared before /api/inventory/{item_id} so "low-stock" isn't captured as an id
@app.get("/api/inventory/low-stock", response_model=List[LowStockItem])
def get_low_stock(warehouse: Optional[str] = None, category: Optional[str] = None):
    """Items at or below their reorder point, most urgent first.

    severity is "critical" at or below half the reorder point, otherwise "low".
    """
    result = []
    for item in apply_filters(inventory_items, warehouse, category):
        qty, reorder = item["quantity_on_hand"], item["reorder_point"]
        if qty > reorder:
            continue
        result.append(
            {
                **item,
                "shortfall": reorder - qty,
                "severity": "critical" if qty <= reorder / 2 else "low",
            }
        )
    # Lowest stock-to-reorder ratio first; guard against a zero reorder point
    result.sort(key=lambda i: i["quantity_on_hand"] / max(i["reorder_point"], 1))
    return result


@app.get("/api/inventory/{item_id}", response_model=InventoryItem)
def get_inventory_item(item_id: str):
    """Get a specific inventory item"""
    item = next((item for item in inventory_items if item["id"] == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@app.get("/api/orders", response_model=List[Order])
def get_orders(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None,
):
    """Get all orders with optional filtering"""
    filtered_orders = apply_filters(orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)
    return filtered_orders


@app.get("/api/orders/{order_id}", response_model=Order)
def get_order(order_id: str):
    """Get a specific order"""
    order = next((order for order in orders if order["id"] == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@app.get("/api/demand", response_model=List[DemandForecast])
def get_demand_forecasts():
    """Get demand forecasts"""
    return demand_forecasts


@app.get("/api/backlog", response_model=List[BacklogItem])
def get_backlog():
    """Get backlog items with purchase order status"""
    # Add has_purchase_order flag to each backlog item
    result = []
    for item in backlog_items:
        item_dict = dict(item)
        # Check if this backlog item has a purchase order
        has_po = any(po["backlog_item_id"] == item["id"] for po in purchase_orders)
        item_dict["has_purchase_order"] = has_po
        result.append(item_dict)
    return result


@app.get("/api/dashboard/summary")
def get_dashboard_summary(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None,
):
    """Get summary statistics for dashboard with optional filtering"""
    # Filter inventory
    filtered_inventory = apply_filters(inventory_items, warehouse, category)

    # Filter orders
    filtered_orders = apply_filters(orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)

    total_inventory_value = sum(
        item["quantity_on_hand"] * item["unit_cost"] for item in filtered_inventory
    )
    low_stock_items = len(
        [
            item
            for item in filtered_inventory
            if item["quantity_on_hand"] <= item["reorder_point"]
        ]
    )
    pending_orders = len(
        [
            order
            for order in filtered_orders
            if order["status"] in ["Processing", "Backordered"]
        ]
    )
    total_backlog_items = len(backlog_items)

    return {
        "total_inventory_value": round(total_inventory_value, 2),
        "low_stock_items": low_stock_items,
        "pending_orders": pending_orders,
        "total_backlog_items": total_backlog_items,
        "total_orders_value": sum(order["total_value"] for order in filtered_orders),
    }


@app.get("/api/spending/summary")
def get_spending_summary():
    """Get spending summary statistics"""
    return spending_summary


@app.get("/api/spending/monthly")
def get_monthly_spending():
    """Get monthly spending breakdown"""
    return monthly_spending


@app.get("/api/spending/categories")
def get_category_spending():
    """Get spending by category"""
    return category_spending


@app.get("/api/spending/transactions")
def get_recent_transactions():
    """Get recent transactions"""
    return recent_transactions


def _filtered_report_orders(warehouse, category, status, month) -> list:
    """Orders narrowed by the same global filters the dashboard and orders routes use"""
    filtered = apply_filters(orders, warehouse, category, status)
    return filter_by_month(filtered, month)


@app.get("/api/reports/quarterly")
def get_quarterly_reports(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None,
):
    """Get quarterly performance reports with optional filtering"""
    quarters = {}

    for order in _filtered_report_orders(warehouse, category, status, month):
        order_date = order.get("order_date", "")
        # Reuse QUARTER_MAP so quarter buckets match the month filter; orders
        # outside the mapped quarters are skipped
        quarter = next(
            (q for q, months in QUARTER_MAP.items() if order_date[:7] in months),
            None,
        )
        if quarter is None:
            continue

        if quarter not in quarters:
            quarters[quarter] = {
                "quarter": quarter,
                "total_orders": 0,
                "total_revenue": 0,
                "delivered_orders": 0,
                "avg_order_value": 0,
                "fulfillment_rate": 0,
            }

        quarters[quarter]["total_orders"] += 1
        quarters[quarter]["total_revenue"] += order.get("total_value", 0)
        if order.get("status") == "Delivered":
            quarters[quarter]["delivered_orders"] += 1

    # Calculate averages and fulfillment rate
    result = []
    for data in quarters.values():
        data["avg_order_value"] = round(data["total_revenue"] / data["total_orders"], 2)
        data["fulfillment_rate"] = round(
            (data["delivered_orders"] / data["total_orders"]) * 100, 1
        )
        result.append(data)

    result.sort(key=lambda x: x["quarter"])
    return result


@app.get("/api/reports/monthly-trends")
def get_monthly_trends(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None,
):
    """Get month-over-month trends with optional filtering"""
    months = {}

    for order in _filtered_report_orders(warehouse, category, status, month):
        order_date = order.get("order_date", "")
        if not order_date:
            continue

        # Extract month (format: YYYY-MM-DD)
        month_key = order_date[:7]

        if month_key not in months:
            months[month_key] = {
                "month": month_key,
                "order_count": 0,
                "revenue": 0,
                "delivered_count": 0,
            }

        months[month_key]["order_count"] += 1
        months[month_key]["revenue"] += order.get("total_value", 0)
        if order.get("status") == "Delivered":
            months[month_key]["delivered_count"] += 1

    result = list(months.values())
    result.sort(key=lambda x: x["month"])
    return result


# Restocking
# Supplier lead times in days, per inventory category.
CATEGORY_LEAD_TIME_DAYS = {
    "Circuit Boards": 14,
    "Sensors": 10,
    "Actuators": 21,
    "Controllers": 12,
    "Power Supplies": 7,
}
DEFAULT_LEAD_TIME_DAYS = 14

# Lower rank = funded first
TREND_PRIORITY = {"increasing": 0, "stable": 1, "decreasing": 2}

# Submitted restocking orders live in memory only and reset on server restart
restock_orders: list = []


class RestockRecommendation(BaseModel):
    sku: str
    name: str
    category: str
    warehouse: str
    trend: str
    quantity_on_hand: int
    forecasted_demand: int
    shortfall: int
    recommended_quantity: int
    unit_cost: float
    line_total: float
    lead_time_days: int


class RestockRecommendationResponse(BaseModel):
    budget: float
    total_cost: float
    remaining_budget: float
    total_shortfall_cost: float
    items: List[RestockRecommendation]


class RestockOrderLine(BaseModel):
    sku: str
    quantity: int = Field(gt=0)


class CreateRestockOrderRequest(BaseModel):
    items: List[RestockOrderLine] = Field(min_length=1)


class RestockOrderItem(BaseModel):
    sku: str
    name: str
    category: str
    warehouse: str
    quantity: int
    unit_cost: float
    line_total: float
    lead_time_days: int


class RestockOrder(BaseModel):
    id: str
    order_number: str
    status: str
    submitted_date: str
    lead_time_days: int
    expected_delivery: str
    total_cost: float
    items: List[RestockOrderItem]


def lead_time_for(category: str) -> int:
    return CATEGORY_LEAD_TIME_DAYS.get(category, DEFAULT_LEAD_TIME_DAYS)


def restock_candidates() -> List[dict]:
    """Forecast items whose forecasted demand exceeds stock on hand, in funding order."""
    inventory_by_sku = {item["sku"]: item for item in inventory_items}
    candidates = []
    for forecast in demand_forecasts:
        item = inventory_by_sku.get(forecast["item_sku"])
        if item is None:
            continue
        shortfall = forecast["forecasted_demand"] - item["quantity_on_hand"]
        if shortfall <= 0:
            continue
        candidates.append(
            {
                "item": item,
                "trend": forecast["trend"].lower(),
                "forecasted_demand": forecast["forecasted_demand"],
                "shortfall": shortfall,
            }
        )
    # Rising demand is funded before stable/falling; within a trend, the biggest gap first
    candidates.sort(key=lambda c: (TREND_PRIORITY.get(c["trend"], 3), -c["shortfall"]))
    return candidates


@app.get(
    "/api/restocking/recommendations", response_model=RestockRecommendationResponse
)
def get_restock_recommendations(budget: float = Query(ge=0)):
    """Spend the budget greedily over the ranked shortfalls."""
    remaining = budget
    recommendations = []
    total_shortfall_cost = 0.0
    for candidate in restock_candidates():
        item = candidate["item"]
        unit_cost = item["unit_cost"]
        total_shortfall_cost += candidate["shortfall"] * unit_cost
        # Buy as much of the shortfall as the remaining budget covers. An item that can only be
        # partly funded doesn't stop the loop: leftover budget can still cover cheaper items below.
        quantity = min(candidate["shortfall"], int(remaining // unit_cost))
        if quantity <= 0:
            continue
        line_total = round(quantity * unit_cost, 2)
        remaining -= line_total
        recommendations.append(
            RestockRecommendation(
                sku=item["sku"],
                name=item["name"],
                category=item["category"],
                warehouse=item["warehouse"],
                trend=candidate["trend"],
                quantity_on_hand=item["quantity_on_hand"],
                forecasted_demand=candidate["forecasted_demand"],
                shortfall=candidate["shortfall"],
                recommended_quantity=quantity,
                unit_cost=unit_cost,
                line_total=line_total,
                lead_time_days=lead_time_for(item["category"]),
            )
        )
    total_cost = round(budget - remaining, 2)
    return RestockRecommendationResponse(
        budget=budget,
        total_cost=total_cost,
        remaining_budget=round(remaining, 2),
        total_shortfall_cost=round(total_shortfall_cost, 2),
        items=recommendations,
    )


@app.get("/api/restocking/orders", response_model=List[RestockOrder])
def get_restock_orders():
    """Submitted restocking orders, newest first."""
    return list(reversed(restock_orders))


@app.post("/api/restocking/orders", response_model=RestockOrder, status_code=201)
def create_restock_order(request: CreateRestockOrderRequest):
    inventory_by_sku = {item["sku"]: item for item in inventory_items}
    unknown = [line.sku for line in request.items if line.sku not in inventory_by_sku]
    if unknown:
        raise HTTPException(
            status_code=400, detail=f"Unknown SKU(s): {', '.join(unknown)}"
        )

    # Prices come from inventory, never from the client
    order_items = []
    for line in request.items:
        item = inventory_by_sku[line.sku]
        order_items.append(
            RestockOrderItem(
                sku=item["sku"],
                name=item["name"],
                category=item["category"],
                warehouse=item["warehouse"],
                quantity=line.quantity,
                unit_cost=item["unit_cost"],
                line_total=round(line.quantity * item["unit_cost"], 2),
                lead_time_days=lead_time_for(item["category"]),
            )
        )

    # The order arrives complete only when its slowest item does
    lead_time_days = max(i.lead_time_days for i in order_items)
    submitted = datetime.now().replace(microsecond=0)
    sequence = len(restock_orders) + 1
    order = RestockOrder(
        id=f"rst-{sequence}",
        order_number=f"RST-{submitted.year}-{sequence:04d}",
        status="Submitted",
        submitted_date=submitted.isoformat(),
        lead_time_days=lead_time_days,
        expected_delivery=(submitted + timedelta(days=lead_time_days)).isoformat(),
        total_cost=round(sum(i.line_total for i in order_items), 2),
        items=order_items,
    )
    restock_orders.append(order)
    return order


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)

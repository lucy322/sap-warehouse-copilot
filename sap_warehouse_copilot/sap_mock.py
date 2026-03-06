"""
SAP Mock Data Layer — Simulates SAP MM/WM OData responses.

In production, replace these functions with real SAP OData V4 calls:
  https://<host>/sap/opu/odata4/sap/api_material/srvd_a2x/...

This mock layer lets the demo run without a live SAP system while
producing realistic material master, stock, and purchase order data.
"""

import random
from datetime import datetime, timedelta
from typing import Optional

# ---------------------------------------------------------------------------
# Material Master (MM01 / MARA + MAKT)
# ---------------------------------------------------------------------------
MATERIALS = {
    "MAT-1001": {
        "material_number": "MAT-1001",
        "description": "Hydraulic Pump Assembly HPA-200",
        "material_type": "FERT",
        "material_group": "PUMP",
        "base_uom": "EA",
        "gross_weight": 12.5,
        "weight_unit": "KG",
        "plant": "1000",
        "storage_location": "WH-A01",
    },
    "MAT-1002": {
        "material_number": "MAT-1002",
        "description": "Servo Motor Drive Unit SMD-X7",
        "material_type": "HALB",
        "material_group": "MOTOR",
        "base_uom": "EA",
        "gross_weight": 3.8,
        "weight_unit": "KG",
        "plant": "1000",
        "storage_location": "WH-B03",
    },
    "MAT-1003": {
        "material_number": "MAT-1003",
        "description": "Industrial Bearing SKF-6205",
        "material_type": "ROH",
        "material_group": "BEARING",
        "base_uom": "EA",
        "gross_weight": 0.21,
        "weight_unit": "KG",
        "plant": "1000",
        "storage_location": "WH-A01",
    },
    "MAT-1004": {
        "material_number": "MAT-1004",
        "description": "Stainless Steel Flange DN50",
        "material_type": "ROH",
        "material_group": "PIPE",
        "base_uom": "EA",
        "gross_weight": 1.9,
        "weight_unit": "KG",
        "plant": "2000",
        "storage_location": "WH-C02",
    },
    "MAT-1005": {
        "material_number": "MAT-1005",
        "description": "PLC Controller Siemens S7-1500",
        "material_type": "FERT",
        "material_group": "ELEC",
        "base_uom": "EA",
        "gross_weight": 0.85,
        "weight_unit": "KG",
        "plant": "1000",
        "storage_location": "WH-B03",
    },
    "MAT-1006": {
        "material_number": "MAT-1006",
        "description": "Conveyor Belt Module CBM-3000",
        "material_type": "FERT",
        "material_group": "CONV",
        "base_uom": "EA",
        "gross_weight": 45.0,
        "weight_unit": "KG",
        "plant": "2000",
        "storage_location": "WH-D01",
    },
}

# ---------------------------------------------------------------------------
# Stock Overview (MMBE / MARD)
# ---------------------------------------------------------------------------
STOCK_LEVELS = {
    "MAT-1001": {"unrestricted": 42, "reserved": 8, "in_quality": 3, "blocked": 0, "reorder_point": 20, "safety_stock": 10},
    "MAT-1002": {"unrestricted": 7, "reserved": 5, "in_quality": 0, "blocked": 0, "reorder_point": 15, "safety_stock": 8},
    "MAT-1003": {"unrestricted": 1200, "reserved": 300, "in_quality": 50, "blocked": 0, "reorder_point": 500, "safety_stock": 200},
    "MAT-1004": {"unrestricted": 3, "reserved": 3, "in_quality": 0, "blocked": 2, "reorder_point": 25, "safety_stock": 10},
    "MAT-1005": {"unrestricted": 18, "reserved": 2, "in_quality": 1, "blocked": 0, "reorder_point": 10, "safety_stock": 5},
    "MAT-1006": {"unrestricted": 0, "reserved": 0, "in_quality": 0, "blocked": 0, "reorder_point": 5, "safety_stock": 2},
}

# ---------------------------------------------------------------------------
# Purchase Orders (ME23N / EKKO + EKPO)
# ---------------------------------------------------------------------------
PURCHASE_ORDERS = [
    {"po_number": "4500012001", "material": "MAT-1002", "vendor": "Siemens AG", "quantity": 50, "uom": "EA", "delivery_date": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d"), "status": "Open", "net_price": 245.00, "currency": "EUR"},
    {"po_number": "4500012002", "material": "MAT-1004", "vendor": "ThyssenKrupp Steel", "quantity": 100, "uom": "EA", "delivery_date": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"), "status": "Open", "net_price": 38.50, "currency": "EUR"},
    {"po_number": "4500012003", "material": "MAT-1006", "vendor": "FlexLink AB", "quantity": 10, "uom": "EA", "delivery_date": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"), "status": "Overdue", "net_price": 2800.00, "currency": "EUR"},
    {"po_number": "4500012004", "material": "MAT-1001", "vendor": "Bosch Rexroth", "quantity": 25, "uom": "EA", "delivery_date": (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d"), "status": "Open", "net_price": 520.00, "currency": "EUR"},
    {"po_number": "4500012005", "material": "MAT-1003", "vendor": "SKF Group", "quantity": 2000, "uom": "EA", "delivery_date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"), "status": "Partially Delivered", "net_price": 4.75, "currency": "EUR"},
]

# ---------------------------------------------------------------------------
# Plant Maintenance (PM / IW39 Work Orders)
# ---------------------------------------------------------------------------
MAINTENANCE_ORDERS = [
    {"order_number": "800010001", "description": "Quarterly inspection — Pump Station Alpha", "equipment": "PUMP-001", "priority": "High", "status": "In Process", "planned_start": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")},
    {"order_number": "800010002", "description": "Replace conveyor belt motor — Line 3", "equipment": "CONV-003", "priority": "Critical", "status": "Released", "planned_start": datetime.now().strftime("%Y-%m-%d")},
    {"order_number": "800010003", "description": "Calibrate PLC sensors — Cell B", "equipment": "PLC-007", "priority": "Medium", "status": "Scheduled", "planned_start": (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")},
]


# ---------------------------------------------------------------------------
# Query Functions (simulates SAP OData service calls)
# ---------------------------------------------------------------------------

def get_material_info(material_id: str) -> Optional[dict]:
    """GET /sap/opu/odata4/sap/api_material/... → Material details."""
    mat = material_id.upper().replace(" ", "-")
    # Try exact match first
    if mat in MATERIALS:
        return MATERIALS[mat]
    # Fuzzy: search by description keyword
    for mid, mdata in MATERIALS.items():
        if mat.lower() in mdata["description"].lower() or mat.lower() in mid.lower():
            return mdata
    return None


def get_stock_level(material_id: str) -> Optional[dict]:
    """GET /sap/opu/odata4/sap/api_material_stock/... → Stock overview."""
    mat = material_id.upper().replace(" ", "-")
    if mat in STOCK_LEVELS:
        stock = STOCK_LEVELS[mat].copy()
        stock["material_number"] = mat
        stock["description"] = MATERIALS.get(mat, {}).get("description", "Unknown")
        stock["available"] = stock["unrestricted"] - stock["reserved"]
        # Determine health
        if stock["available"] <= 0:
            stock["health"] = "OUT_OF_STOCK"
        elif stock["available"] <= stock["safety_stock"]:
            stock["health"] = "CRITICAL"
        elif stock["available"] <= stock["reorder_point"]:
            stock["health"] = "REORDER"
        else:
            stock["health"] = "HEALTHY"
        return stock
    # Fuzzy
    for mid in STOCK_LEVELS:
        mdata = MATERIALS.get(mid, {})
        if mat.lower() in mdata.get("description", "").lower():
            return get_stock_level(mid)
    return None


def get_purchase_orders(material_id: Optional[str] = None, status: Optional[str] = None) -> list:
    """GET /sap/opu/odata4/sap/api_purchaseorder/... → PO list."""
    results = PURCHASE_ORDERS
    if material_id:
        mat = material_id.upper().replace(" ", "-")
        results = [po for po in results if mat in po["material"] or mat.lower() in MATERIALS.get(po["material"], {}).get("description", "").lower()]
    if status:
        results = [po for po in results if status.lower() in po["status"].lower()]
    return results


def get_maintenance_orders(priority: Optional[str] = None) -> list:
    """GET /sap/opu/odata4/sap/api_maintorder/... → Maintenance work orders."""
    if priority:
        return [mo for mo in MAINTENANCE_ORDERS if priority.lower() in mo["priority"].lower()]
    return MAINTENANCE_ORDERS


def get_warehouse_summary() -> dict:
    """Aggregate KPIs across all materials."""
    total_materials = len(MATERIALS)
    out_of_stock = sum(1 for mid in STOCK_LEVELS if get_stock_level(mid)["health"] == "OUT_OF_STOCK")
    critical = sum(1 for mid in STOCK_LEVELS if get_stock_level(mid)["health"] == "CRITICAL")
    reorder_needed = sum(1 for mid in STOCK_LEVELS if get_stock_level(mid)["health"] == "REORDER")
    healthy = total_materials - out_of_stock - critical - reorder_needed
    overdue_pos = len([po for po in PURCHASE_ORDERS if po["status"] == "Overdue"])
    open_maintenance = len([mo for mo in MAINTENANCE_ORDERS if mo["status"] != "Completed"])

    return {
        "total_materials": total_materials,
        "healthy": healthy,
        "reorder_needed": reorder_needed,
        "critical": critical,
        "out_of_stock": out_of_stock,
        "overdue_purchase_orders": overdue_pos,
        "open_maintenance_orders": open_maintenance,
        "overall_health": "RED" if out_of_stock > 0 or overdue_pos > 0 else ("AMBER" if critical > 0 or reorder_needed > 1 else "GREEN"),
    }


# ---------------------------------------------------------------------------
# Tool definitions for the LLM function-calling layer
# ---------------------------------------------------------------------------
SAP_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_stock_level",
            "description": "Get current stock level and availability for a material in the SAP warehouse. Returns unrestricted, reserved, available quantities and health status (HEALTHY / REORDER / CRITICAL / OUT_OF_STOCK).",
            "parameters": {
                "type": "object",
                "properties": {
                    "material_id": {
                        "type": "string",
                        "description": "SAP material number (e.g. MAT-1001) or partial description keyword (e.g. 'pump', 'bearing')."
                    }
                },
                "required": ["material_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_material_info",
            "description": "Get material master data from SAP including description, material type, group, weight, plant and storage location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "material_id": {
                        "type": "string",
                        "description": "SAP material number or description keyword."
                    }
                },
                "required": ["material_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_purchase_orders",
            "description": "List purchase orders from SAP, optionally filtered by material or status (Open, Overdue, Partially Delivered).",
            "parameters": {
                "type": "object",
                "properties": {
                    "material_id": {
                        "type": "string",
                        "description": "Filter by material number or keyword. Optional."
                    },
                    "status": {
                        "type": "string",
                        "description": "Filter by PO status: Open, Overdue, Partially Delivered. Optional."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_maintenance_orders",
            "description": "List plant maintenance work orders, optionally filtered by priority (Critical, High, Medium).",
            "parameters": {
                "type": "object",
                "properties": {
                    "priority": {
                        "type": "string",
                        "description": "Filter by priority level. Optional."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_warehouse_summary",
            "description": "Get overall warehouse KPI summary: total materials, stock health distribution, overdue POs, open maintenance orders, and overall RAG status.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
]

# Map function names to callables
SAP_FUNCTION_MAP = {
    "get_stock_level": lambda args: get_stock_level(args.get("material_id", "")),
    "get_material_info": lambda args: get_material_info(args.get("material_id", "")),
    "get_purchase_orders": lambda args: get_purchase_orders(args.get("material_id"), args.get("status")),
    "get_maintenance_orders": lambda args: get_maintenance_orders(args.get("priority")),
    "get_warehouse_summary": lambda args: get_warehouse_summary(),
}

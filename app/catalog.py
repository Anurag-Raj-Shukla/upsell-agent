"""
Loads the mock product catalog.

Day 1-2 TODO: swap this for a real DB (SQLite/Postgres) if time allows.
For a 10-day build, a JSON file is fine — don't over-engineer this part.
"""
import json
from pathlib import Path
from typing import Optional

_CATALOG_PATH = Path(__file__).parent.parent / "data" / "catalog.json"


def load_catalog() -> list[dict]:
    with open(_CATALOG_PATH, "r") as f:
        return json.load(f)


def get_product(sku: str) -> Optional[dict]:
    for product in load_catalog():
        if product["id"] == sku:
            return product
    return None


def get_pairings(sku: str) -> list[dict]:
    """Return catalog items that pair well with the given sku."""
    product = get_product(sku)
    if not product:
        return []
    catalog = load_catalog()
    pair_ids = set(product.get("pairs_well_with", []))
    return [p for p in catalog if p["id"] in pair_ids]


def in_stock(sku: str, qty: int = 1) -> bool:
    product = get_product(sku)
    return bool(product) and product["stock"] >= qty

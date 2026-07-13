from __future__ import annotations

import json

from .models import GlobalSettings, Product


def save_project(path: str, products: list[Product], settings: GlobalSettings) -> None:
    data = {
        "settings": settings.to_dict(),
        "products": [p.to_dict() for p in products],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_project(path: str) -> tuple[list[Product], GlobalSettings]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    settings = GlobalSettings.from_dict(data.get("settings", {}))
    products = [Product.from_dict(d) for d in data.get("products", [])]
    return products, settings

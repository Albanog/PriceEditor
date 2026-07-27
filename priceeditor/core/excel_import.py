from __future__ import annotations

from openpyxl import load_workbook

from .models import Product


def import_excel(path: str) -> list[tuple[str, float, str | None]]:
    """Reads first three columns (Name, USD price, Codigo) starting after header row.
    Codigo (3rd column) is optional."""
    wb = load_workbook(path, data_only=True)
    ws = wb.active
    rows: list[tuple[str, float, str | None]] = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row is None or len(row) < 2:
            continue
        name, price = row[0], row[1]
        codigo = row[2] if len(row) > 2 else None
        if name is None or price is None:
            continue
        name = str(name).strip()
        if not name:
            continue
        try:
            price = float(price)
        except (TypeError, ValueError):
            continue
        codigo = str(codigo).strip() if codigo is not None else None
        codigo = codigo or None
        rows.append((name, price, codigo))
    return rows


def merge_import(existing: list[Product], imported: list[tuple[str, float, str | None]]) -> list[Product]:
    """Update USD price (and codigo, if provided) on existing products matched by name
    (case-insensitive), keep their manual settings. Add new products for unmatched names.
    Existing products not present in the import are left untouched."""
    by_name = {p.name.strip().lower(): p for p in existing}
    for name, price, codigo in imported:
        key = name.strip().lower()
        if key in by_name:
            by_name[key].usd_price = price
            if codigo is not None:
                by_name[key].codigo = codigo
        else:
            new_p = Product(name=name, usd_price=price, codigo=codigo)
            existing.append(new_p)
            by_name[key] = new_p
    return existing

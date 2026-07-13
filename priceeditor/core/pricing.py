from __future__ import annotations

from .models import GlobalSettings, Product


def round_to_step(value: float, step: int) -> int:
    if step <= 0:
        return round(value)
    return int(round(value / step) * step)


def compute_contado_ars(product: Product, settings: GlobalSettings) -> int:
    if product.override_contado_ars is not None:
        return int(round(product.override_contado_ars))
    raw = product.usd_price * settings.exchange_rate
    return round_to_step(raw, settings.rounding_step)


def compute_cuota_ars(product: Product, settings: GlobalSettings, contado_ars: int) -> int:
    if product.override_cuota_ars is not None:
        return int(round(product.override_cuota_ars))
    n = product.cuotas_count or settings.default_cuotas_count
    if n <= 0:
        return 0
    total_with_surcharge = contado_ars * (1 + settings.cuotas_pct / 100.0)
    raw = total_with_surcharge / n
    return round_to_step(raw, settings.rounding_step)


def compute_prices(product: Product, settings: GlobalSettings) -> tuple[int, int, int]:
    """Returns (contado_ars, cuota_ars, cuotas_count)."""
    contado = compute_contado_ars(product, settings)
    n = product.cuotas_count or settings.default_cuotas_count
    cuota = compute_cuota_ars(product, settings, contado)
    return contado, cuota, n

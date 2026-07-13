from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Product:
    name: str
    usd_price: float
    checked: bool = True
    deleted: bool = False
    cuotas_count: Optional[int] = None  # None -> use global default
    tipo_cobro_text: Optional[str] = None  # custom cuotas line override
    override_contado_ars: Optional[float] = None
    override_cuota_ars: Optional[float] = None
    copies: int = 1

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "usd_price": self.usd_price,
            "checked": self.checked,
            "deleted": self.deleted,
            "cuotas_count": self.cuotas_count,
            "tipo_cobro_text": self.tipo_cobro_text,
            "override_contado_ars": self.override_contado_ars,
            "override_cuota_ars": self.override_cuota_ars,
            "copies": self.copies,
        }

    @staticmethod
    def from_dict(d: dict) -> "Product":
        return Product(
            name=d["name"],
            usd_price=d["usd_price"],
            checked=d.get("checked", True),
            deleted=d.get("deleted", False),
            cuotas_count=d.get("cuotas_count"),
            tipo_cobro_text=d.get("tipo_cobro_text"),
            override_contado_ars=d.get("override_contado_ars"),
            override_cuota_ars=d.get("override_cuota_ars"),
            copies=d.get("copies", 1),
        )


@dataclass
class GlobalSettings:
    exchange_rate: float = 1000.0
    cuotas_pct: float = 0.0
    default_cuotas_count: int = 3
    rounding_step: int = 100

    def to_dict(self) -> dict:
        return {
            "exchange_rate": self.exchange_rate,
            "cuotas_pct": self.cuotas_pct,
            "default_cuotas_count": self.default_cuotas_count,
            "rounding_step": self.rounding_step,
        }

    @staticmethod
    def from_dict(d: dict) -> "GlobalSettings":
        return GlobalSettings(
            exchange_rate=d.get("exchange_rate", 1000.0),
            cuotas_pct=d.get("cuotas_pct", 0.0),
            default_cuotas_count=d.get("default_cuotas_count", 3),
            rounding_step=d.get("rounding_step", 100),
        )

"""Utilidades compartidas por las pruebas.

Los UUID se generan a partir de un numero para poder escribir `pid(1)` en vez
de pegar un UUID completo en cada linea de prueba.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ceats_intel.domain.entidades import LineaPedido, Pedido
from ceats_intel.domain.valueobjects import Dinero, ProductoId, SucursalId


def uuid_de(n: int) -> str:
    return f"00000000-0000-4000-8000-{n:012d}"


def pid(n: int) -> ProductoId:
    return ProductoId(uuid_de(n))


def sid(n: int = 1) -> SucursalId:
    return SucursalId(uuid_de(n))


def pedido(
    numero: int,
    productos: list[int],
    *,
    cuando: datetime | None = None,
    precio: float = 100.0,
    cantidad: int = 1,
) -> Pedido:
    return Pedido(
        id_=f"pedido-{numero}",
        sucursal_id=sid(),
        creado_en=cuando or datetime(2026, 9, 1, 13, 0, tzinfo=UTC),
        lineas=[LineaPedido(pid(p), cantidad, Dinero.desde_pesos(precio)) for p in productos],
    )


@pytest.fixture
def constructor_pedido():
    return pedido

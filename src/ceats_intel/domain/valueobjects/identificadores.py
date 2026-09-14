"""Identificadores del dominio.

Son value objects: no tienen identidad propia, valen por su contenido. Dos
`ProductoId` con el mismo texto son el mismo objeto para todos los efectos.

La razon de no usar `str` pelon es que en este servicio circulan al menos tres
UUID distintos (producto, sucursal, restaurante) y todos se ven igual. Con tipos
separados, pasar una sucursal donde iba un producto truena al construir en vez
de devolver una lista vacia media hora despues.
"""

from __future__ import annotations

import re

_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class _IdentificadorUUID:
    """Base comun de los identificadores. No se usa directamente."""

    __slots__ = ("_valor",)

    def __init__(self, valor: str) -> None:
        if not isinstance(valor, str):
            raise TypeError(f"{type(self).__name__} espera str, llego {type(valor).__name__}")
        normalizado = valor.strip().lower()
        if not _UUID.match(normalizado):
            raise ValueError(f"{type(self).__name__} invalido: {valor!r}")
        self._valor = normalizado

    @property
    def valor(self) -> str:
        return self._valor

    def __eq__(self, otro: object) -> bool:
        # Comparar solo contra el mismo tipo. Si no, un ProductoId y un
        # SucursalId con el mismo UUID saldrian iguales.
        if type(otro) is not type(self):
            return NotImplemented
        return self._valor == otro._valor

    def __hash__(self) -> int:
        return hash((type(self).__name__, self._valor))

    def __lt__(self, otro: object) -> bool:
        # Hace falta para ordenar. El desempate de las recomendaciones usa el id
        # como segundo criterio, y sin esto el orden dependeria del azar.
        if type(otro) is not type(self):
            return NotImplemented
        return self._valor < otro._valor

    def __str__(self) -> str:
        return self._valor

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._valor!r})"


class ProductoId(_IdentificadorUUID):
    """Identifica un producto del menu (`menu_productos.id` en cEats)."""


class SucursalId(_IdentificadorUUID):
    """Identifica una sucursal (`sucursales.id` en cEats)."""


class RestauranteId(_IdentificadorUUID):
    """Identifica un restaurante (`restaurantes.id` en cEats)."""


class CategoriaId(_IdentificadorUUID):
    """Identifica una categoria del menu (`menu_categorias.id` en cEats)."""

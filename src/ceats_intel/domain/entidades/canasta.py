"""Lo que el cliente trae en el carrito cuando pedimos sugerencias.

No es un Pedido: el pedido ya ocurrio y tiene precios cerrados, la canasta esta
viva y todavia puede cambiar. Comparten forma pero no significado, y mezclarlos
seria pedir problemas mas adelante.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator

from ceats_intel.domain.valueobjects import ProductoId, SucursalId


class Canasta:
    __slots__ = ("_sucursal_id", "_productos")

    def __init__(self, sucursal_id: SucursalId, productos: Iterable[ProductoId]) -> None:
        # Ordenada: la canasta entra en la huella de la decision, y si el orden
        # cambiara segun como llego el JSON, la huella cambiaria sin que cambie
        # nada real.
        self._sucursal_id = sucursal_id
        self._productos = tuple(sorted(set(productos)))

    @property
    def sucursal_id(self) -> SucursalId:
        return self._sucursal_id

    @property
    def productos(self) -> tuple[ProductoId, ...]:
        return self._productos

    def contiene(self, producto_id: ProductoId) -> bool:
        return producto_id in self._productos

    def vacia(self) -> bool:
        return not self._productos

    def clave(self) -> str:
        """Texto estable para la huella."""
        return ",".join(str(p) for p in self._productos)

    def __iter__(self) -> Iterator[ProductoId]:
        return iter(self._productos)

    def __len__(self) -> int:
        return len(self._productos)

    def __eq__(self, otro: object) -> bool:
        if not isinstance(otro, Canasta):
            return NotImplemented
        return self._sucursal_id == otro._sucursal_id and self._productos == otro._productos

    def __hash__(self) -> int:
        return hash((self._sucursal_id, self._productos))

    def __repr__(self) -> str:
        return f"Canasta({len(self._productos)} productos)"

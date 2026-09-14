"""Producto del menu.

Es entidad, no value object: dos productos con el mismo nombre y precio siguen
siendo productos distintos si tienen id distinto. Por eso `__eq__` compara solo
el id.
"""

from __future__ import annotations

from ceats_intel.domain.valueobjects import CategoriaId, Dinero, ProductoId


class Producto:
    __slots__ = (
        "_id",
        "_nombre",
        "_precio",
        "_categoria_id",
        "_categoria_nombre",
        "_tiene_modificadores",
        "_activo",
    )

    def __init__(
        self,
        id_: ProductoId,
        nombre: str,
        precio: Dinero,
        categoria_id: CategoriaId | None = None,
        categoria_nombre: str = "",
        *,
        tiene_modificadores: bool = False,
        activo: bool = True,
    ) -> None:
        if not nombre.strip():
            raise ValueError("El producto necesita nombre")
        self._id = id_
        self._nombre = nombre.strip()
        self._precio = precio
        self._categoria_id = categoria_id
        self._categoria_nombre = categoria_nombre.strip()
        self._tiene_modificadores = tiene_modificadores
        self._activo = activo

    @property
    def id(self) -> ProductoId:
        return self._id

    @property
    def nombre(self) -> str:
        return self._nombre

    @property
    def precio(self) -> Dinero:
        return self._precio

    @property
    def categoria_id(self) -> CategoriaId | None:
        return self._categoria_id

    @property
    def categoria_nombre(self) -> str:
        return self._categoria_nombre

    @property
    def tiene_modificadores(self) -> bool:
        """Si es True, el front abre el modal en vez de agregar al carrito.

        Un producto con grupos de modificadores requeridos que se agrega directo
        llega incompleto a cocina. Ya paso con la barra de recomendaciones.
        """
        return self._tiene_modificadores

    @property
    def activo(self) -> bool:
        return self._activo

    def es_sugerible(self) -> bool:
        return self._activo

    def __eq__(self, otro: object) -> bool:
        if not isinstance(otro, Producto):
            return NotImplemented
        return self._id == otro._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"Producto({self._nombre!r}, {self._precio})"

"""Pedido y sus lineas.

Aqui vive el ejemplo de copia defensiva del que hablo en la Unidad 1: el
constructor recibe una lista y guarda una tupla. Si guardara la lista tal cual,
quien la paso conserva una referencia al estado interno del pedido y lo puede
mutar por fuera, sin pasar por ningun metodo. Eso rompe el encapsulamiento
aunque el atributo se llame `_lineas`.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import datetime

from ceats_intel.domain.valueobjects import Dinero, ProductoId, SucursalId


class LineaPedido:
    """Un renglon del pedido. Value object: vale por su contenido."""

    __slots__ = ("_producto_id", "_cantidad", "_precio_unitario")

    def __init__(self, producto_id: ProductoId, cantidad: int, precio_unitario: Dinero) -> None:
        if not isinstance(cantidad, int) or isinstance(cantidad, bool):
            raise TypeError("La cantidad debe ser entero")
        if cantidad < 1:
            raise ValueError(f"Cantidad invalida: {cantidad}")
        self._producto_id = producto_id
        self._cantidad = cantidad
        self._precio_unitario = precio_unitario

    @property
    def producto_id(self) -> ProductoId:
        return self._producto_id

    @property
    def cantidad(self) -> int:
        return self._cantidad

    @property
    def precio_unitario(self) -> Dinero:
        return self._precio_unitario

    def subtotal(self) -> Dinero:
        return self._precio_unitario.por(self._cantidad)

    def __eq__(self, otro: object) -> bool:
        if not isinstance(otro, LineaPedido):
            return NotImplemented
        return (
            self._producto_id == otro._producto_id
            and self._cantidad == otro._cantidad
            and self._precio_unitario == otro._precio_unitario
        )

    def __hash__(self) -> int:
        return hash((self._producto_id, self._cantidad, self._precio_unitario))

    def __repr__(self) -> str:
        return f"LineaPedido({self._producto_id}, x{self._cantidad}, {self._precio_unitario})"


class Pedido:
    __slots__ = ("_id", "_sucursal_id", "_creado_en", "_lineas")

    def __init__(
        self,
        id_: str,
        sucursal_id: SucursalId,
        creado_en: datetime,
        lineas: Iterable[LineaPedido],
    ) -> None:
        congeladas = tuple(lineas)
        if not congeladas:
            raise ValueError("Un pedido sin lineas no existe")
        if creado_en.tzinfo is None:
            raise ValueError("creado_en debe traer zona horaria")
        self._id = id_
        self._sucursal_id = sucursal_id
        self._creado_en = creado_en
        self._lineas = congeladas

    @property
    def id(self) -> str:
        return self._id

    @property
    def sucursal_id(self) -> SucursalId:
        return self._sucursal_id

    @property
    def creado_en(self) -> datetime:
        return self._creado_en

    @property
    def lineas(self) -> Sequence[LineaPedido]:
        # Tupla, no lista. Quien la recibe no puede agregar ni quitar renglones.
        return self._lineas

    def total(self) -> Dinero:
        total = Dinero.cero()
        for linea in self._lineas:
            total = total.mas(linea.subtotal())
        return total

    def productos(self) -> frozenset[ProductoId]:
        """Los productos distintos del pedido, sin cantidades.

        La co-ocurrencia trabaja con presencia, no con volumen: pedir tres
        refrescos no hace que el refresco acompañe mejor a los tacos.
        """
        return frozenset(linea.producto_id for linea in self._lineas)

    def cantidad_de(self, producto_id: ProductoId) -> int:
        return sum(x.cantidad for x in self._lineas if x.producto_id == producto_id)

    @property
    def hora_del_dia(self) -> int:
        return self._creado_en.hour

    @property
    def dia_semana(self) -> int:
        """Lunes 0, domingo 6. Igual que `datetime.weekday()`."""
        return self._creado_en.weekday()

    def __eq__(self, otro: object) -> bool:
        if not isinstance(otro, Pedido):
            return NotImplemented
        return self._id == otro._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"Pedido({self._id!r}, {len(self._lineas)} lineas, {self.total()})"

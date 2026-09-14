"""Historial de ventas de una sucursal en una ventana.

Es la raiz del agregado: nadie de afuera arma pares de productos a mano, se los
pide a esta clase. Asi la matriz de co-ocurrencia se calcula una sola vez y
siempre igual.

Los conteos se calculan al vuelo la primera vez que se piden y se guardan. Un
historial de 90 dias de una sucursal ocupada anda en los miles de pedidos, y
recorrerlos por cada candidato seria tirar el tiempo.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from itertools import combinations
from types import MappingProxyType

from ceats_intel.domain.entidades.pedido import Pedido
from ceats_intel.domain.valueobjects import ProductoId, SucursalId, VentanaTemporal

# Un par siempre se guarda ordenado, asi (A,B) y (B,A) son la misma llave.
Par = tuple[ProductoId, ProductoId]


class HistorialVentas:
    __slots__ = (
        "_sucursal_id",
        "_ventana",
        "_pedidos",
        "_frecuencias",
        "_pares",
        "_unidades",
    )

    def __init__(
        self,
        sucursal_id: SucursalId,
        ventana: VentanaTemporal,
        pedidos: Iterable[Pedido],
    ) -> None:
        self._sucursal_id = sucursal_id
        self._ventana = ventana
        self._pedidos = tuple(pedidos)
        self._frecuencias: Counter[ProductoId] | None = None
        self._pares: Counter[Par] | None = None
        self._unidades: Counter[ProductoId] | None = None

    @property
    def sucursal_id(self) -> SucursalId:
        return self._sucursal_id

    @property
    def ventana(self) -> VentanaTemporal:
        return self._ventana

    @property
    def pedidos(self) -> Sequence[Pedido]:
        return self._pedidos

    @property
    def total_pedidos(self) -> int:
        return len(self._pedidos)

    def vacio(self) -> bool:
        return not self._pedidos

    # ---------------------------------------------------------------- conteos

    def frecuencia(self, producto_id: ProductoId) -> int:
        """En cuantos pedidos distintos aparecio el producto."""
        return self._calcular_frecuencias()[producto_id]

    def unidades(self, producto_id: ProductoId) -> int:
        """Cuantas piezas se vendieron en total. Sirve para los mas vendidos."""
        return self._calcular_unidades()[producto_id]

    def veces_juntos(self, a: ProductoId, b: ProductoId) -> int:
        if a == b:
            return 0
        return self._calcular_pares()[self._llave(a, b)]

    def soporte(self, producto_id: ProductoId) -> float:
        """Proporcion de pedidos que traen el producto. Entre 0 y 1."""
        if not self._pedidos:
            return 0.0
        return self.frecuencia(producto_id) / len(self._pedidos)

    def acompanantes(self, producto_id: ProductoId) -> Mapping[ProductoId, int]:
        """Que salio junto a este producto y cuantas veces.

        Devuelve una vista de solo lectura. Si devolviera el dict interno,
        cualquiera podria modificar los conteos del agregado desde fuera.
        """
        pares = self._calcular_pares()
        acompana: Counter[ProductoId] = Counter()
        for (a, b), veces in pares.items():
            if a == producto_id:
                acompana[b] = veces
            elif b == producto_id:
                acompana[a] = veces
        return MappingProxyType(dict(acompana))

    def productos_vistos(self) -> frozenset[ProductoId]:
        return frozenset(self._calcular_frecuencias())

    # ----------------------------------------------------------------- series

    def serie_por_hora(self) -> tuple[int, ...]:
        """Pedidos por hora del dia, 24 posiciones. Alimenta el pronostico."""
        conteo = [0] * 24
        for pedido in self._pedidos:
            conteo[pedido.hora_del_dia] += 1
        return tuple(conteo)

    def serie_por_dia_semana(self) -> tuple[int, ...]:
        """Pedidos por dia de la semana, 7 posiciones. Lunes primero."""
        conteo = [0] * 7
        for pedido in self._pedidos:
            conteo[pedido.dia_semana] += 1
        return tuple(conteo)

    # ------------------------------------------------------------- internos

    @staticmethod
    def _llave(a: ProductoId, b: ProductoId) -> Par:
        return (a, b) if a < b else (b, a)

    def _calcular_frecuencias(self) -> Counter[ProductoId]:
        if self._frecuencias is None:
            conteo: Counter[ProductoId] = Counter()
            for pedido in self._pedidos:
                conteo.update(pedido.productos())
            self._frecuencias = conteo
        return self._frecuencias

    def _calcular_unidades(self) -> Counter[ProductoId]:
        if self._unidades is None:
            conteo: Counter[ProductoId] = Counter()
            for pedido in self._pedidos:
                for linea in pedido.lineas:
                    conteo[linea.producto_id] += linea.cantidad
            self._unidades = conteo
        return self._unidades

    def _calcular_pares(self) -> Counter[Par]:
        if self._pares is None:
            conteo: Counter[Par] = Counter()
            for pedido in self._pedidos:
                productos = sorted(pedido.productos())
                # combinations sobre la lista ya ordenada deja cada par en
                # orden, asi que no hace falta volver a normalizarlo aqui.
                conteo.update(combinations(productos, 2))
            self._pares = conteo
        return self._pares

    def __repr__(self) -> str:
        return (
            f"HistorialVentas({self._sucursal_id}, {self._ventana.clave()}, "
            f"{len(self._pedidos)} pedidos)"
        )

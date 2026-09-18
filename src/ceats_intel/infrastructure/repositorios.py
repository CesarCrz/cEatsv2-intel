"""Adaptadores HTTP de los puertos del dominio.

Aqui vive la unica frontera entre "lo que dice el JSON del backend" y "lo que
entiende el negocio": el dominio nunca ve un dict. Los nombres de los campos
que se leen aqui son los que ya expone
`app/api/internal/intel/{ventas,catalogo}/route.ts` en el backend --
cualquier cambio ahi tiene que reflejarse aqui.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import UTC, datetime

from ceats_intel.domain.catalogo import Catalogo
from ceats_intel.domain.entidades import HistorialVentas, LineaPedido, Pedido, Producto
from ceats_intel.domain.valueobjects import (
    CategoriaId,
    Dinero,
    ProductoId,
    SucursalId,
    VentanaTemporal,
)
from ceats_intel.infrastructure.cliente_backend import ClienteBackend

logger = logging.getLogger(__name__)


def _como_datetime(valor: str) -> datetime:
    momento = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=UTC)
    return momento


class RepositorioVentasHTTP:
    """Implementa `RepositorioVentas` pegandole a `/api/internal/intel/ventas`."""

    def __init__(self, cliente: ClienteBackend) -> None:
        self._cliente = cliente

    async def historial(self, sucursal_id: SucursalId, ventana: VentanaTemporal) -> HistorialVentas:
        crudo = await self._cliente.obtener_ventas(
            str(sucursal_id),
            ventana.desde.date().isoformat(),
            ventana.hasta.date().isoformat(),
        )
        if crudo.get("truncado"):
            # El backend ya recorto la respuesta a su tope de renglones. No
            # hay nada que reintentar: se trabaja con lo que llego.
            # `pedidos_incluidos` es la cuenta real; `total_pedidos` incluiria
            # pedidos que nunca llegaron a `ventas` y sesgaria el soporte si
            # se usara por error.
            logger.warning(
                "Ventas truncadas para sucursal %s: %s de %s pedidos incluidos",
                sucursal_id,
                crudo.get("pedidos_incluidos"),
                crudo.get("total_pedidos"),
            )
        pedidos = self._agrupar_pedidos(crudo.get("ventas", []), sucursal_id)
        return HistorialVentas(sucursal_id=sucursal_id, ventana=ventana, pedidos=pedidos)

    @staticmethod
    def _agrupar_pedidos(renglones: list[dict], sucursal_id: SucursalId) -> list[Pedido]:
        """Renglones planos -> `Pedido` con sus `LineaPedido`, por `pedido_id`.

        El backend manda una fila por linea de venta, no un pedido ya armado.
        Aqui es donde se reconstruye el agregado que pide el dominio.
        """
        por_pedido: dict[str, list[dict]] = defaultdict(list)
        for renglon in renglones:
            por_pedido[renglon["pedido_id"]].append(renglon)

        pedidos: list[Pedido] = []
        for pedido_id, filas in por_pedido.items():
            lineas = [
                LineaPedido(
                    ProductoId(fila["producto_id"]),
                    int(fila["cantidad"]),
                    Dinero.desde_pesos(fila["precio_unitario"]),
                )
                for fila in filas
            ]
            # Las lineas de un mismo pedido se crean juntas; el mas viejo de
            # sus timestamps es una aproximacion mas que suficiente para
            # `creado_en`, que solo se usa para la hora y el dia de la semana.
            creado_en = min(_como_datetime(fila["creado_en"]) for fila in filas)
            pedidos.append(Pedido(pedido_id, sucursal_id, creado_en, lineas))
        return pedidos


class RepositorioCatalogoHTTP:
    """Implementa `RepositorioCatalogo` pegandole a `/api/internal/intel/catalogo`."""

    def __init__(self, cliente: ClienteBackend) -> None:
        self._cliente = cliente

    async def catalogo(self, sucursal_id: SucursalId) -> Catalogo:
        crudo = await self._cliente.obtener_catalogo(str(sucursal_id))
        productos = [
            Producto(
                id_=ProductoId(fila["producto_id"]),
                nombre=fila["nombre"],
                precio=Dinero.desde_pesos(fila["precio"]),
                categoria_id=(
                    CategoriaId(fila["categoria_id"]) if fila.get("categoria_id") else None
                ),
                categoria_nombre=fila.get("categoria_nombre") or "",
                tiene_modificadores=bool(fila.get("tiene_modificadores", False)),
                activo=bool(fila.get("activo", True)),
            )
            for fila in crudo.get("productos", [])
        ]
        # El backend ya filtro por activo/disponible en la sucursal; no hay
        # `destacados` en el contrato todavia, asi que `Catalogo` cae a sus
        # primeros ocho activos como ultimo escalon de la cascada.
        return Catalogo(productos)

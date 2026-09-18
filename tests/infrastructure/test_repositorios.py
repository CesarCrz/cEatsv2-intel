"""Los adaptadores convierten el JSON despersonalizado del backend en objetos
de dominio. Aqui se prueba esa frontera, con el mismo shape que expone
`app/api/internal/intel/{ventas,catalogo}/route.ts` del backend.
"""

from __future__ import annotations

import asyncio

import httpx

from ceats_intel.domain.valueobjects import ProductoId, SucursalId, VentanaTemporal
from ceats_intel.infrastructure.cliente_backend import ClienteBackend
from ceats_intel.infrastructure.repositorios import RepositorioCatalogoHTTP, RepositorioVentasHTTP

_SUCURSAL = "11111111-1111-4111-8111-111111111111"
_PRODUCTO_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
_PRODUCTO_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"


def test_historial_agrupa_renglones_por_pedido(settings):
    cuerpo = {
        "sucursal_id": _SUCURSAL,
        "total_pedidos": 1,
        "pedidos_incluidos": 1,
        "ventas": [
            {
                "pedido_id": "pedido-1",
                "producto_id": _PRODUCTO_A,
                "cantidad": 2,
                "precio_unitario": 45.5,
                "creado_en": "2026-09-01T13:00:00.000Z",
            },
            {
                "pedido_id": "pedido-1",
                "producto_id": _PRODUCTO_B,
                "cantidad": 1,
                "precio_unitario": 30,
                "creado_en": "2026-09-01T13:00:01.000Z",
            },
        ],
    }

    def manejador(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=cuerpo)

    cliente = ClienteBackend(settings, transport=httpx.MockTransport(manejador))
    repo = RepositorioVentasHTTP(cliente)
    ventana = VentanaTemporal.ultimos_dias(90)

    historial = asyncio.run(repo.historial(SucursalId(_SUCURSAL), ventana))

    assert historial.total_pedidos == 1
    (pedido,) = historial.pedidos
    assert pedido.id == "pedido-1"
    assert pedido.productos() == frozenset({ProductoId(_PRODUCTO_A), ProductoId(_PRODUCTO_B)})
    assert pedido.cantidad_de(ProductoId(_PRODUCTO_A)) == 2


def test_historial_respeta_pedidos_incluidos_cuando_trunca(settings):
    # Solo un renglon llego aunque el backend diga que hay mas pedidos en la
    # ventana: el historial se arma solo con lo que de verdad recibio.
    cuerpo = {
        "sucursal_id": _SUCURSAL,
        "total_pedidos": 500,
        "pedidos_incluidos": 1,
        "truncado": True,
        "ventas": [
            {
                "pedido_id": "pedido-1",
                "producto_id": _PRODUCTO_A,
                "cantidad": 1,
                "precio_unitario": 10,
                "creado_en": "2026-09-01T13:00:00.000Z",
            }
        ],
    }

    def manejador(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=cuerpo)

    cliente = ClienteBackend(settings, transport=httpx.MockTransport(manejador))
    repo = RepositorioVentasHTTP(cliente)
    ventana = VentanaTemporal.ultimos_dias(90)

    historial = asyncio.run(repo.historial(SucursalId(_SUCURSAL), ventana))

    assert historial.total_pedidos == 1  # no 500: eso vendria de confiar en total_pedidos


def test_catalogo_arma_productos_desde_el_json(settings):
    cuerpo = {
        "productos": [
            {
                "producto_id": _PRODUCTO_A,
                "nombre": "Gyoza (6 pz)",
                "categoria_id": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
                "categoria_nombre": "Entradas",
                "precio": 95,
                "activo": True,
                "tiene_modificadores": False,
            }
        ]
    }

    def manejador(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=cuerpo)

    cliente = ClienteBackend(settings, transport=httpx.MockTransport(manejador))
    repo = RepositorioCatalogoHTTP(cliente)

    catalogo = asyncio.run(repo.catalogo(SucursalId(_SUCURSAL)))

    producto = catalogo.producto(ProductoId(_PRODUCTO_A))
    assert producto is not None
    assert producto.nombre == "Gyoza (6 pz)"
    assert producto.precio.centavos == 9500

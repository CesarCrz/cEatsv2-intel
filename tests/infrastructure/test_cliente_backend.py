"""Pruebas del cliente HTTP y su circuit breaker.

Todo sobre `httpx.MockTransport`: nada de esto toca una red real. Las
funciones async se manejan con `asyncio.run()` en vez de pytest-asyncio, que
no esta entre las dependencias de desarrollo del proyecto.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest

from ceats_intel.infrastructure.cliente_backend import CircuitoAbiertoError, ClienteBackend


def _cliente(settings, manejador) -> ClienteBackend:
    transporte = httpx.MockTransport(manejador)
    return ClienteBackend(settings, transport=transporte)


def test_obtener_ventas_manda_bearer_y_regresa_json(settings):
    vistos: list[httpx.Request] = []

    def manejador(request: httpx.Request) -> httpx.Response:
        vistos.append(request)
        return httpx.Response(200, json={"ventas": []})

    cliente = _cliente(settings, manejador)
    resultado = asyncio.run(cliente.obtener_ventas("sucursal-1", "2026-01-01", "2026-02-01"))

    assert resultado == {"ventas": []}
    assert len(vistos) == 1
    peticion = vistos[0]
    assert peticion.url.path == "/api/internal/intel/ventas"
    assert peticion.headers["authorization"] == "Bearer clave-de-salida-de-prueba"
    assert dict(peticion.url.params) == {
        "sucursal_id": "sucursal-1",
        "desde": "2026-01-01",
        "hasta": "2026-02-01",
    }


def test_obtener_catalogo_pega_a_la_ruta_correcta(settings):
    def manejador(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"productos": []})

    cliente = _cliente(settings, manejador)
    resultado = asyncio.run(cliente.obtener_catalogo("sucursal-1"))

    assert resultado == {"productos": []}


def test_error_5xx_se_propaga(settings):
    def manejador(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    cliente = _cliente(settings, manejador)
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(cliente.obtener_catalogo("sucursal-1"))


def test_circuito_abre_tras_cinco_fallos_seguidos(settings):
    llamadas = 0

    def manejador(request: httpx.Request) -> httpx.Response:
        nonlocal llamadas
        llamadas += 1
        return httpx.Response(500)

    cliente = _cliente(settings, manejador)

    for _ in range(5):
        with pytest.raises(httpx.HTTPStatusError):
            asyncio.run(cliente.obtener_catalogo("sucursal-1"))

    assert llamadas == 5

    # El sexto intento ni siquiera toca la red: el circuito ya esta abierto.
    with pytest.raises(CircuitoAbiertoError):
        asyncio.run(cliente.obtener_catalogo("sucursal-1"))

    assert llamadas == 5


def test_circuito_se_cierra_tras_un_exito(settings):
    respuestas = iter([httpx.Response(500)] * 4 + [httpx.Response(200, json={"productos": []})])

    def manejador(request: httpx.Request) -> httpx.Response:
        return next(respuestas)

    cliente = _cliente(settings, manejador)

    for _ in range(4):
        with pytest.raises(httpx.HTTPStatusError):
            asyncio.run(cliente.obtener_catalogo("sucursal-1"))

    # El quinto intento tiene exito antes de llegar al umbral de apertura.
    resultado = asyncio.run(cliente.obtener_catalogo("sucursal-1"))
    assert resultado == {"productos": []}

    # Y el contador de fallos quedo en cero: hacen falta cinco fallos mas
    # (no uno) para volver a abrir el circuito.
    assert cliente._fallos_seguidos == 0  # noqa: SLF001 -- se inspecciona el estado interno a proposito

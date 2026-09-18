"""Fixtures compartidas de las pruebas de API.

Las tres variables obligatorias se ponen ANTES de importar `ceats_intel.main`:
ese modulo llama a `obtener_settings()` al nivel de modulo (a proposito, para
que el proceso truene al arrancar si falta alguna), asi que tienen que existir
desde el primer import o la simple coleccion de pruebas fallaria.

Nada de esto toca una red real: los repositorios se sustituyen con dobles en
`app.dependency_overrides`.
"""

from __future__ import annotations

import os

os.environ.setdefault("CEATS_BACKEND_URL", "http://backend.test")
os.environ.setdefault("INTEL_SERVICE_KEY", "clave-de-salida-de-prueba")
os.environ.setdefault("INTEL_INBOUND_KEY", "clave-de-entrada-correcta")

import pytest
from fastapi.testclient import TestClient

from ceats_intel.api.dependencias import obtener_repositorio_catalogo, obtener_repositorio_ventas
from ceats_intel.domain.catalogo import Catalogo
from ceats_intel.domain.entidades import HistorialVentas
from ceats_intel.domain.valueobjects import SucursalId, VentanaTemporal
from ceats_intel.main import app

LLAVE_CORRECTA = "clave-de-entrada-correcta"


class RepoVentasVacio:
    """Doble sin ventas: alcanza para probar el camino feliz sin red."""

    async def historial(self, sucursal_id: SucursalId, ventana: VentanaTemporal) -> HistorialVentas:
        return HistorialVentas(sucursal_id=sucursal_id, ventana=ventana, pedidos=[])


class RepoCatalogoVacio:
    async def catalogo(self, sucursal_id: SucursalId) -> Catalogo:
        return Catalogo([])


@pytest.fixture(autouse=True)
def _limpiar_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def cliente() -> TestClient:
    return TestClient(app)


@pytest.fixture
def cliente_con_datos_vacios(cliente: TestClient) -> TestClient:
    """Cliente con los repositorios sustituidos por dobles sin datos.

    Sirve para probar el camino feliz de principio a fin (auth -> validacion
    -> caso de uso -> respuesta) sin que nada intente hablarle a un backend
    real.
    """
    app.dependency_overrides[obtener_repositorio_ventas] = lambda: RepoVentasVacio()
    app.dependency_overrides[obtener_repositorio_catalogo] = lambda: RepoCatalogoVacio()
    return cliente

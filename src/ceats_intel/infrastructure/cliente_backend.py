"""Cliente HTTP hacia el backend de cEats. Solo lee, nunca escribe.

Dos rutas nada mas, las que describe CONTRATO_INTEL.md:

    GET /api/internal/intel/ventas?sucursal_id=&desde=&hasta=
    GET /api/internal/intel/catalogo?sucursal_id=

Circuit breaker sencillo: tras `_FALLOS_PARA_ABRIR` fallos seguidos el
circuito se abre `_SEGUNDOS_ABIERTO` segundos y las peticiones fallan de
inmediato, sin tocar la red. No hay medio-abierto ni ventana deslizante --
aqui lo unico que importa es dejar de pegarle a un backend que ya esta caido,
para que el timeout de 2s de cada intento no se sume por cada sucursal que
pida algo mientras tanto.

El checkout nunca se entera de nada de esto: si esto falla, el backend cae al
resolver de siempre. Por eso todos los errores de aqui se dejan subir tal
cual (httpx.HTTPError, CircuitoAbiertoError) y quien llama decide que hacer.
"""

from __future__ import annotations

import logging
import time

import httpx

from ceats_intel.infrastructure.config import Settings

logger = logging.getLogger(__name__)

_FALLOS_PARA_ABRIR = 5
_SEGUNDOS_ABIERTO = 30.0

_RUTA_VENTAS = "/api/internal/intel/ventas"
_RUTA_CATALOGO = "/api/internal/intel/catalogo"


class CircuitoAbiertoError(RuntimeError):
    """El circuito esta abierto: la peticion ni siquiera se intenta."""


class ClienteBackend:
    def __init__(
        self,
        settings: Settings,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._settings = settings
        self._fallos_seguidos = 0
        self._abierto_hasta: float | None = None
        self._cliente = httpx.AsyncClient(
            base_url=settings.ceats_backend_url,
            timeout=settings.http_timeout_segundos,
            transport=transport,
        )

    async def cerrar(self) -> None:
        await self._cliente.aclose()

    async def obtener_ventas(self, sucursal_id: str, desde: str, hasta: str) -> dict:
        """`desde`/`hasta` van en formato `YYYY-MM-DD`. `hasta` es exclusivo."""
        return await self._get(
            _RUTA_VENTAS,
            {"sucursal_id": sucursal_id, "desde": desde, "hasta": hasta},
        )

    async def obtener_catalogo(self, sucursal_id: str) -> dict:
        return await self._get(_RUTA_CATALOGO, {"sucursal_id": sucursal_id})

    # ------------------------------------------------------------- internos

    async def _get(self, ruta: str, parametros: dict[str, str]) -> dict:
        self._verificar_circuito(ruta)
        cabeceras = {
            "Authorization": f"Bearer {self._settings.intel_service_key.get_secret_value()}"
        }
        try:
            respuesta = await self._cliente.get(ruta, params=parametros, headers=cabeceras)
            respuesta.raise_for_status()
        except httpx.HTTPError as error:
            self._registrar_fallo(ruta, error)
            raise
        else:
            self._registrar_exito()
            return respuesta.json()

    def _verificar_circuito(self, ruta: str) -> None:
        if self._abierto_hasta is None:
            return
        if time.monotonic() < self._abierto_hasta:
            raise CircuitoAbiertoError(f"Circuito abierto, no se llama a {ruta}")
        # Se cumplio la espera: se deja pasar una peticion de prueba. Si
        # vuelve a fallar, `_registrar_fallo` lo vuelve a abrir de inmediato.
        self._abierto_hasta = None
        self._fallos_seguidos = 0

    def _registrar_exito(self) -> None:
        self._fallos_seguidos = 0
        self._abierto_hasta = None

    def _registrar_fallo(self, ruta: str, error: httpx.HTTPError) -> None:
        self._fallos_seguidos += 1
        # Nunca el cuerpo de la respuesta ni las cabeceras: podrian traer
        # datos del backend. Solo la ruta y el tipo de error.
        logger.warning("Fallo llamando %s: %s", ruta, type(error).__name__)
        if self._fallos_seguidos >= _FALLOS_PARA_ABRIR:
            self._abierto_hasta = time.monotonic() + _SEGUNDOS_ABIERTO
            logger.warning("Circuito abierto por %.0f segundos tras %d fallos seguidos",
                            _SEGUNDOS_ABIERTO, self._fallos_seguidos)

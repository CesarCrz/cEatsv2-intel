"""Autenticacion de entrada y armado de las dependencias de los routers.

La cabecera es `X-Intel-Key`. La comparacion es en tiempo constante con
`hmac.compare_digest`: no hay razon para darle a quien intenta adivinar la
llave una pista de cuantos caracteres acerto por cuanto tarda la respuesta.

Si `INTEL_INBOUND_KEY` llegara vacia (no deberia: `Settings` truena al
arrancar si falta), la peticion se rechaza igual. Nunca se abre por omision.
"""

from __future__ import annotations

import hmac
from functools import lru_cache

from fastapi import Depends, Header, HTTPException, status

from ceats_intel.infrastructure.cache import RepositorioCacheado
from ceats_intel.infrastructure.cliente_backend import ClienteBackend
from ceats_intel.infrastructure.config import Settings, obtener_settings
from ceats_intel.infrastructure.repositorios import RepositorioCatalogoHTTP, RepositorioVentasHTTP


async def verificar_llave(
    x_intel_key: str | None = Header(default=None),
    settings: Settings = Depends(obtener_settings),
) -> None:
    esperado = settings.intel_inbound_key.get_secret_value()
    if not esperado or not x_intel_key or not hmac.compare_digest(x_intel_key, esperado):
        # Nunca decir cual de las dos cosas fallo (llave ausente vs.
        # incorrecta): la respuesta es identica en ambos casos.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autorizado")


@lru_cache
def _cliente_backend_singleton() -> ClienteBackend:
    """Un solo `httpx.AsyncClient` para todo el proceso: reusa conexiones.

    Cacheado a proposito -- crear un cliente por peticion tiraria el pool de
    conexiones que httpx mantiene abierto hacia el backend. Las pruebas nunca
    llaman a esta funcion: sobreescriben `obtener_cliente_backend` en
    `app.dependency_overrides` con su propio cliente sobre `MockTransport`.
    """
    return ClienteBackend(obtener_settings())


def obtener_cliente_backend() -> ClienteBackend:
    return _cliente_backend_singleton()


@lru_cache
def obtener_repositorio_ventas() -> RepositorioCacheado:
    """Singleton por proceso: la cache solo sirve si sobrevive entre peticiones.

    `lru_cache` sin argumentos lo vuelve un unico objeto para toda la vida del
    proceso -- si `Depends()` lo reconstruyera en cada request, el TTL de
    `RepositorioCacheado` nunca tendria oportunidad de servir un acierto.

    En pruebas, `app.dependency_overrides[obtener_repositorio_ventas]` se
    sustituye directo por un doble; esta funcion nunca llega a llamarse.
    """
    settings = obtener_settings()
    interno = RepositorioVentasHTTP(_cliente_backend_singleton())
    return RepositorioCacheado(interno, ttl_segundos=settings.cache_ttl_segundos)


def obtener_repositorio_catalogo(
    cliente: ClienteBackend = Depends(obtener_cliente_backend),
) -> RepositorioCatalogoHTTP:
    # Sin estado propio que cachear aqui: el catalogo no entra en la huella de
    # la decision del mismo modo que el historial, y cada llamada es barata.
    return RepositorioCatalogoHTTP(cliente)

"""Arma la app FastAPI: routers, autenticacion, manejo de errores.

Dos reglas duras, sacadas de SEGURIDAD.md:

1. El manejador de errores global nunca deja pasar una traza de Python al
   cliente. Lo que sale de aca son mensajes genericos; el detalle completo se
   va al log del servidor.
2. Si falta una variable de entorno obligatoria, el proceso truena al
   arrancar (`obtener_settings()` se llama al importar este modulo, antes de
   levantar nada), nunca queda abierto.

Docs (`/docs`, `/redoc`, `/openapi.json`) van apagados: este servicio no se
publica a internet (SEGURIDAD.md, "Sin exposicion publica") y no hay razon
para ofrecer un mapa del API ni siquiera en la red interna.
"""

from __future__ import annotations

import logging

import httpx
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ceats_intel.api.routers import analitica, lambdacalc, recomendaciones, salud
from ceats_intel.infrastructure.cliente_backend import CircuitoAbiertoError
from ceats_intel.infrastructure.config import obtener_settings

logger = logging.getLogger("ceats_intel")

# Se resuelve al importar: si falta CEATS_BACKEND_URL, INTEL_SERVICE_KEY o
# INTEL_INBOUND_KEY, esto truena y el servidor nunca llega a levantar.
obtener_settings()

app = FastAPI(
    title="cEats Intel",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.include_router(salud.router)
app.include_router(recomendaciones.router)
app.include_router(analitica.router)
app.include_router(lambdacalc.router)

# Generoso para una canasta de 50 productos + 50 reglas manuales, pero lejos
# de lo que alguien necesitaria para un abuso de memoria. Se corta por
# Content-Length ANTES de que FastAPI intente parsear el cuerpo.
_MAX_BODY_BYTES = 100_000


@app.middleware("http")
async def limitar_tamano_del_cuerpo(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            largo = int(content_length)
        except ValueError:
            largo = 0
        if largo > _MAX_BODY_BYTES:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"detail": "Cuerpo demasiado grande"},
            )
    return await call_next(request)


@app.exception_handler(RequestValidationError)
async def error_de_validacion(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Los errores de pydantic describen la forma del payload (campo, tipo
    # esperado), no datos del sistema. Se pueden regresar tal cual; lo que
    # nunca sale es una traza de Python.
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )


@app.exception_handler(CircuitoAbiertoError)
async def error_circuito_abierto(request: Request, exc: CircuitoAbiertoError) -> JSONResponse:
    logger.warning("Circuito abierto en %s", request.url.path)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Servicio no disponible temporalmente"},
    )


@app.exception_handler(httpx.HTTPError)
async def error_backend(request: Request, exc: httpx.HTTPError) -> JSONResponse:
    # El backend no respondio a tiempo o respondio con error. El checkout
    # nunca depende de esto: quien llamo (el backend) ya tiene su propio
    # resolver de respaldo si este servicio no contesta bien.
    logger.warning("Fallo hablando con el backend en %s: %s", request.url.path, type(exc).__name__)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Servicio no disponible temporalmente"},
    )


@app.exception_handler(Exception)
async def error_no_manejado(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Error no manejado en %s", request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Error interno del servidor"},
    )

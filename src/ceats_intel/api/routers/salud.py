"""Healthcheck sin autenticacion.

A proposito no revela nada: ni version del modelo, ni si el backend responde,
ni el estado del circuit breaker. Es lo que pega Docker/EasyPanel para saber
si el proceso sigue vivo, y SEGURIDAD.md pide explicitamente que no exponga
informacion del sistema.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["salud"])


@router.get("/healthz")
async def salud() -> dict[str, str]:
    return {"status": "ok"}

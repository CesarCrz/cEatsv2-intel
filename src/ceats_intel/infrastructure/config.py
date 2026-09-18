"""Configuracion del servicio, leida de variables de entorno.

Las tres obligatorias no tienen valor por defecto a proposito: si falta una,
`Settings()` truena al construirse y el proceso no arranca. Prefiero que
truene al inicio a que arranque abierto sin que nadie se de cuenta -- es el
mismo criterio que ya usa el backend con `INTEL_SERVICE_KEY`.

Las llaves van en `SecretStr`. Pydantic ya las oculta en `repr()` y en los
logs de validacion; nunca se llama `.get_secret_value()` salvo justo antes de
usarlas (cabecera saliente o comparacion de entrada).
"""

from __future__ import annotations

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ceats_backend_url: str
    intel_service_key: SecretStr
    intel_inbound_key: SecretStr

    cache_ttl_segundos: int = Field(default=300, gt=0)
    http_timeout_segundos: float = Field(default=2.0, gt=0)
    max_pasos_lambda: int = Field(default=10_000, gt=0)
    ventana_dias: int = Field(default=90, gt=0)
    ventana_larga_dias: int = Field(default=365, gt=0)


def obtener_settings() -> Settings:
    """Construye `Settings` a partir del entorno actual.

    Sin cachear a proposito: es una lectura de unas cuantas variables de
    entorno, no vale la pena la complicacion de invalidar un cache para algo
    que las pruebas necesitan poder cambiar entre casos con `monkeypatch`.
    """
    return Settings()  # type: ignore[call-arg]  # los campos obligatorios llegan del entorno

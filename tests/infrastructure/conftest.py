from __future__ import annotations

import pytest

from ceats_intel.infrastructure.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        ceats_backend_url="http://backend.test",
        intel_service_key="clave-de-salida-de-prueba",
        intel_inbound_key="clave-de-entrada-de-prueba",
        http_timeout_segundos=0.2,
    )

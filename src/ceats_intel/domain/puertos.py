"""Puertos que el dominio declara y que la infraestructura implementa.

El dominio pide datos en su propio idioma (`HistorialVentas`, `Catalogo`) y no
sabe ni le importa si detras hay HTTP, una base de datos o un archivo. Eso es
lo que permite probar todo el dominio con `pytest` sin levantar servidor ni
tocar la red: en las pruebas, el puerto lo implementa un doble en memoria.

Son `Protocol`, no clases abstractas: la infraestructura no necesita heredar
de nada de aqui, solo tener el metodo con la firma correcta. Es tipado
estructural, igual que en `EstrategiaRecomendacion`... salvo que ahi si hace
falta heredar porque `puntuar()` vive en la base. Aqui no hay comportamiento
compartido que ofrecer, asi que un `Protocol` alcanza.
"""

from __future__ import annotations

from typing import Protocol

from ceats_intel.domain.catalogo import Catalogo
from ceats_intel.domain.entidades import HistorialVentas
from ceats_intel.domain.valueobjects import SucursalId, VentanaTemporal


class RepositorioVentas(Protocol):
    async def historial(self, sucursal_id: SucursalId, ventana: VentanaTemporal) -> HistorialVentas:
        """El historial de ventas de una sucursal dentro de la ventana dada."""
        ...


class RepositorioCatalogo(Protocol):
    async def catalogo(self, sucursal_id: SucursalId) -> Catalogo:
        """El menu vigente de una sucursal."""
        ...

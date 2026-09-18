"""Cache en memoria para `RepositorioVentas`. Patron Decorator.

Envuelve cualquier cosa que hable el protocolo `RepositorioVentas` y le
antepone una cache con TTL. Sin disco, sin persistencia: si el proceso se
reinicia la cache se pierde y ya (ver SEGURIDAD.md, "Sin nada guardado").

La llave es `(sucursal_id, ventana.clave())`, la misma combinacion que entra
en la huella de la decision (`application/huella.py`): dos peticiones con la
misma huella deben ver exactamente el mismo historial, y esta es la pieza que
lo garantiza dentro del TTL.

Tope de entradas con desalojo del mas viejo para no crecer sin limite si en un
dia le pegan muchas sucursales distintas.
"""

from __future__ import annotations

import time
from collections import OrderedDict

from ceats_intel.domain.entidades import HistorialVentas
from ceats_intel.domain.puertos import RepositorioVentas
from ceats_intel.domain.valueobjects import SucursalId, VentanaTemporal

_MAX_ENTRADAS_POR_DEFECTO = 500

Llave = tuple[str, str]


class RepositorioCacheado:
    def __init__(
        self,
        interno: RepositorioVentas,
        ttl_segundos: int,
        max_entradas: int = _MAX_ENTRADAS_POR_DEFECTO,
    ) -> None:
        if ttl_segundos <= 0:
            raise ValueError("ttl_segundos debe ser positivo")
        if max_entradas <= 0:
            raise ValueError("max_entradas debe ser positivo")
        self._interno = interno
        self._ttl = float(ttl_segundos)
        self._max_entradas = max_entradas
        # OrderedDict como LRU de insercion/refresco: `move_to_end` en cada
        # acierto basta para este patron de acceso, no hace falta nada mas
        # fino para un servicio de este tamano.
        self._entradas: OrderedDict[Llave, tuple[float, HistorialVentas]] = OrderedDict()

    async def historial(self, sucursal_id: SucursalId, ventana: VentanaTemporal) -> HistorialVentas:
        llave: Llave = (str(sucursal_id), ventana.clave())
        vigente = self._entradas.get(llave)
        if vigente is not None:
            expira_en, historial = vigente
            if time.monotonic() < expira_en:
                self._entradas.move_to_end(llave)
                return historial
            del self._entradas[llave]

        historial = await self._interno.historial(sucursal_id, ventana)
        self._guardar(llave, historial)
        return historial

    def _guardar(self, llave: Llave, historial: HistorialVentas) -> None:
        if llave in self._entradas:
            del self._entradas[llave]
        elif len(self._entradas) >= self._max_entradas:
            self._entradas.popitem(last=False)  # el mas viejo
        self._entradas[llave] = (time.monotonic() + self._ttl, historial)

    def __len__(self) -> int:
        return len(self._entradas)

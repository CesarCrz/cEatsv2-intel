"""La cache debe servir dos peticiones con una sola llamada al repositorio
interno, y dejar de servir en cuanto expira el TTL."""

from __future__ import annotations

import asyncio
import time

from ceats_intel.domain.entidades import HistorialVentas
from ceats_intel.domain.valueobjects import SucursalId, VentanaTemporal
from ceats_intel.infrastructure.cache import RepositorioCacheado

_SUCURSAL = SucursalId("11111111-1111-4111-8111-111111111111")


class _RepositorioContador:
    """Doble en memoria que cuenta cuantas veces se le pide historial."""

    def __init__(self) -> None:
        self.llamadas = 0

    async def historial(self, sucursal_id: SucursalId, ventana: VentanaTemporal) -> HistorialVentas:
        self.llamadas += 1
        return HistorialVentas(sucursal_id=sucursal_id, ventana=ventana, pedidos=[])


def test_segunda_llamada_no_toca_el_repositorio_interno():
    interno = _RepositorioContador()
    cache = RepositorioCacheado(interno, ttl_segundos=300)
    ventana = VentanaTemporal.ultimos_dias(90)

    asyncio.run(cache.historial(_SUCURSAL, ventana))
    asyncio.run(cache.historial(_SUCURSAL, ventana))

    assert interno.llamadas == 1


def test_ventanas_distintas_son_llaves_distintas():
    interno = _RepositorioContador()
    cache = RepositorioCacheado(interno, ttl_segundos=300)

    asyncio.run(cache.historial(_SUCURSAL, VentanaTemporal.ultimos_dias(90)))
    asyncio.run(cache.historial(_SUCURSAL, VentanaTemporal.ultimos_dias(365)))

    assert interno.llamadas == 2


def test_entrada_expirada_vuelve_a_pedir(monkeypatch):
    interno = _RepositorioContador()
    cache = RepositorioCacheado(interno, ttl_segundos=300)
    ventana = VentanaTemporal.ultimos_dias(90)

    asyncio.run(cache.historial(_SUCURSAL, ventana))

    # Adelanto el reloj 301 segundos: el TTL de 300 ya vencio.
    #
    # Dos cuidados. Uno: el reloj falso no puede ser un iterador de dos valores,
    # porque la cache consulta la hora mas de una vez por llamada (revisa si
    # vencio y despues sella la entrada nueva). Dos: hay que guardar la funcion
    # real ANTES de parchear; `time` aqui es el mismo objeto modulo que ve la
    # cache, asi que llamar a time.monotonic() adentro del reemplazo se llama a
    # si mismo hasta reventar.
    reloj_real = time.monotonic
    monkeypatch.setattr(
        "ceats_intel.infrastructure.cache.time.monotonic", lambda: reloj_real() + 301.0
    )

    asyncio.run(cache.historial(_SUCURSAL, ventana))

    assert interno.llamadas == 2


def test_desaloja_la_entrada_mas_vieja_al_llegar_al_tope():
    interno = _RepositorioContador()
    cache = RepositorioCacheado(interno, ttl_segundos=300, max_entradas=2)
    ventana = VentanaTemporal.ultimos_dias(90)

    for n in range(3):
        sucursal = SucursalId(f"1111111{n}-1111-4111-8111-111111111111")
        asyncio.run(cache.historial(sucursal, ventana))

    assert len(cache) == 2

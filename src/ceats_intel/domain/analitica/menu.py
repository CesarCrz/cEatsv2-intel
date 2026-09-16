"""Clasificacion de productos y deteccion de anomalias.

Menu engineering es la matriz clasica de Kasavana y Smith: cada platillo se
ubica por popularidad y por margen, contra la mediana del menu.

    margen alto + popular       estrella   (protegerla, no tocarle el precio)
    margen bajo + popular       caballo    (subirle precio con cuidado)
    margen alto + impopular     puzzle     (empujarlo, aqui entra el upsell)
    margen bajo + impopular     perro      (quitarlo del menu)

Uso mediana y no promedio porque un solo platillo carisimo mueve el promedio y
manda a medio menu al cuadrante equivocado.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from enum import Enum
from statistics import mean, median, pstdev

from ceats_intel.domain.catalogo import Catalogo
from ceats_intel.domain.entidades import HistorialVentas
from ceats_intel.domain.valueobjects import ProductoId


class Cuadrante(str, Enum):
    ESTRELLA = "estrella"
    CABALLO = "caballo"
    PUZZLE = "puzzle"
    PERRO = "perro"

    def __str__(self) -> str:
        return self.value


class ClasificadorMenu(ABC):
    @abstractmethod
    def clasificar(
        self, historial: HistorialVentas, catalogo: Catalogo
    ) -> dict[ProductoId, Cuadrante]:
        ...


class MenuEngineeringClasificador(ClasificadorMenu):
    def __init__(self, costo_relativo: float = 0.35) -> None:
        # Sin costos reales por platillo, supongo un costo de insumos parejo.
        # Es una simplificacion y hay que decirlo: en cuanto el restaurante
        # capture sus costos en el CRM, este numero se reemplaza por el de
        # cada producto.
        if not 0 < costo_relativo < 1:
            raise ValueError("El costo relativo va entre 0 y 1")
        self._costo_relativo = costo_relativo

    def margen(self, precio_centavos: int) -> float:
        return precio_centavos * (1 - self._costo_relativo)

    def clasificar(
        self, historial: HistorialVentas, catalogo: Catalogo
    ) -> dict[ProductoId, Cuadrante]:
        activos = catalogo.activos()
        if not activos or historial.vacio():
            return {}

        popularidades = {p.id: historial.unidades(p.id) for p in activos}
        margenes = {p.id: self.margen(p.precio.centavos) for p in activos}

        corte_popularidad = median(popularidades.values())
        corte_margen = median(margenes.values())

        salida: dict[ProductoId, Cuadrante] = {}
        for producto in activos:
            popular = popularidades[producto.id] >= corte_popularidad
            rentable = margenes[producto.id] >= corte_margen
            if popular and rentable:
                salida[producto.id] = Cuadrante.ESTRELLA
            elif popular:
                salida[producto.id] = Cuadrante.CABALLO
            elif rentable:
                salida[producto.id] = Cuadrante.PUZZLE
            else:
                salida[producto.id] = Cuadrante.PERRO
        return salida


class Anomalia:
    __slots__ = ("indice", "valor", "esperado", "z")

    def __init__(self, indice: int, valor: float, esperado: float, z: float) -> None:
        self.indice = indice
        self.valor = valor
        self.esperado = round(esperado, 4)
        self.z = round(z, 4)

    @property
    def es_caida(self) -> bool:
        return self.z < 0

    def __repr__(self) -> str:
        cara = "caida" if self.es_caida else "pico"
        return f"Anomalia({cara}, i={self.indice}, z={self.z:+.2f})"


class DetectorAnomalias:
    """Puntaje z sobre la serie de ventas.

        z = (x - media) / desviacion

    Con |z| > 3 se alerta. En una serie normal eso es como el 0.3% de los
    puntos, asi que no llena de ruido el CRM.

    Limitacion conocida: los outliers inflan la desviacion y se tapan solos.
    Con series cortas como las de aqui es aceptable; si empieza a fallar, el
    reemplazo es la mediana absoluta de desviaciones.
    """

    def __init__(self, umbral: float = 3.0) -> None:
        if umbral <= 0:
            raise ValueError("El umbral debe ser positivo")
        self._umbral = umbral

    def detectar(self, serie: Sequence[float]) -> list[Anomalia]:
        if len(serie) < 4:
            return []
        promedio = mean(serie)
        desviacion = pstdev(serie)
        if desviacion == 0:
            # Serie plana: no hay nada raro que encontrar.
            return []
        anomalias = []
        for i, valor in enumerate(serie):
            z = (valor - promedio) / desviacion
            if abs(z) > self._umbral:
                anomalias.append(Anomalia(i, valor, promedio, z))
        return anomalias

"""La clase abstracta de la que cuelga todo lo de la Unidad 2.

El caso de uso nunca pregunta de que tipo es la estrategia. Le pide candidatos y
ya. Eso es polimorfismo y es lo que permite que el comparador del laboratorio
ponga cuatro estrategias lado a lado sin un solo `if`.
"""

from __future__ import annotations

import heapq
from abc import ABC, abstractmethod

from ceats_intel.domain.catalogo import Catalogo
from ceats_intel.domain.entidades import Canasta, HistorialVentas
from ceats_intel.domain.recomendacion.candidato import Candidato, NivelRespaldo, OrigenSugerencia


class ContextoRecomendacion:
    """Todo lo que una estrategia puede necesitar, en un solo objeto.

    Empece pasando historial y canasta sueltos, pero en cuanto entro la cascada
    hicieron falta el historial del restaurante y el catalogo, y la firma se
    volvio impresentable. Con un objeto de contexto, agregar una fuente de datos
    no obliga a tocar la firma de las cinco subclases.
    """

    __slots__ = ("canasta", "historial", "historial_restaurante", "catalogo", "alfa")

    def __init__(
        self,
        canasta: Canasta,
        historial: HistorialVentas,
        catalogo: Catalogo,
        historial_restaurante: HistorialVentas | None = None,
        alfa: float = 10.0,
    ) -> None:
        self.canasta = canasta
        self.historial = historial
        self.catalogo = catalogo
        # El del restaurante completo. Es el nivel 2 de la cascada, para cuando
        # una sucursal sola no junta pedidos suficientes.
        self.historial_restaurante = historial_restaurante
        # El alfa del suavizado. Se puede mover por restaurante desde el CRM.
        self.alfa = alfa

    def con_historial(self, historial: HistorialVentas) -> ContextoRecomendacion:
        return ContextoRecomendacion(
            self.canasta, historial, self.catalogo, self.historial_restaurante, self.alfa
        )


class EstrategiaRecomendacion(ABC):
    def __init__(self, nombre: str, peso: float = 1.0) -> None:
        if peso <= 0:
            raise ValueError("El peso debe ser positivo")
        self._nombre = nombre
        self._peso = peso

    @property
    def nombre(self) -> str:
        return self._nombre

    @property
    def peso(self) -> float:
        return self._peso

    @abstractmethod
    def candidatos(self, ctx: ContextoRecomendacion) -> list[Candidato]:
        """Los productos que esta estrategia propone, con su score crudo."""

    @abstractmethod
    def origen(self) -> OrigenSugerencia:
        """La etiqueta que llevan sus candidatos."""

    @abstractmethod
    def nivel(self) -> NivelRespaldo:
        """En que escalon de la cascada vive."""

    def puntuar(self, ctx: ContextoRecomendacion, limite: int = 4) -> list[Candidato]:
        """Metodo plantilla. Lo comun vive aqui, lo propio en `candidatos`.

        Las subclases no repiten el peso, el filtrado de lo que ya trae el
        cliente ni el top-N. Solo dicen como puntuar.
        """
        if limite < 1:
            raise ValueError("El limite debe ser al menos 1")

        # Los descartados no se devuelven, pero tampoco se tiran: `candidatos()`
        # los sigue exponiendo con su motivo para que el laboratorio del CRM
        # pueda mostrar por que se cayo cada uno.
        crudos = [
            c.con_score(c.score * self._peso)
            for c in self.candidatos(ctx)
            if not c.descartado and not ctx.canasta.contiene(c.producto_id)
        ]
        # nlargest con la clave de orden completa, no solo el score: asi los
        # empates se resuelven por id y el resultado es el mismo siempre.
        return heapq.nsmallest(limite, crudos, key=Candidato.clave_orden)

    def __str__(self) -> str:
        return f"{type(self).__name__}({self._nombre})"

    def __repr__(self) -> str:
        return f"{type(self).__name__}(nombre={self._nombre!r}, peso={self._peso})"

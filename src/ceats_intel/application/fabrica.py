"""Factory Method: del modo configurado a la estrategia concreta.

El caso de uso pide "modo hibrido" y recibe un objeto. No sabe ni le importa
que adentro hay una cascada de siete escalones con un composite arriba.
"""

from __future__ import annotations

from enum import Enum

from ceats_intel.domain.recomendacion import (
    AfinidadCategoriaStrategy,
    CascadaStrategy,
    CoOcurrenciaStrategy,
    DestacadosStrategy,
    EstrategiaRecomendacion,
    HibridaStrategy,
    NivelRespaldo,
    PopularidadStrategy,
    ReglasManualesStrategy,
    ReglaUpsell,
)


class ModoUpsell(str, Enum):
    AUTO = "auto"
    MANUAL = "manual"
    HIBRIDO = "hibrido"
    # Los dos de abajo no son modos de produccion: existen para el comparador
    # del laboratorio, que pone las cuatro columnas lado a lado.
    POPULARIDAD = "popularidad"
    AFINIDAD = "afinidad"

    def __str__(self) -> str:
        return self.value


def cascada_automatica(objetivo: int = 4, lift_minimo: float = 1.0) -> CascadaStrategy:
    """Los siete escalones, de mas informado a mas generico.

    Cada escalon dice de que historial come. El 3 usa el del restaurante igual
    que el 2, pero con el lift minimo aflojado: cuando ya se llego hasta aca, un
    lift de 0.9 sigue siendo mejor informacion que un mas vendido a secas.
    """
    return CascadaStrategy(
        escalones=[
            (
                CoOcurrenciaStrategy(
                    "sucursal", lift_minimo=lift_minimo, nivel=NivelRespaldo.SUCURSAL
                ),
                "sucursal",
            ),
            (
                CoOcurrenciaStrategy(
                    "restaurante", lift_minimo=lift_minimo, nivel=NivelRespaldo.RESTAURANTE
                ),
                "restaurante",
            ),
            (
                CoOcurrenciaStrategy(
                    "ventana larga", lift_minimo=0.85, nivel=NivelRespaldo.VENTANA_LARGA
                ),
                "restaurante",
            ),
            (AfinidadCategoriaStrategy(), "sucursal"),
            (PopularidadStrategy("populares sucursal"), "sucursal"),
            (
                PopularidadStrategy(
                    "populares restaurante", nivel=NivelRespaldo.POPULAR_RESTAURANTE
                ),
                "restaurante",
            ),
            (DestacadosStrategy(), "sucursal"),
        ],
        objetivo=objetivo,
    )


class FabricaEstrategias:
    def __init__(self, lift_minimo: float = 1.0) -> None:
        self._lift_minimo = lift_minimo

    def crear(
        self,
        modo: ModoUpsell,
        reglas: list[ReglaUpsell] | None = None,
        objetivo: int = 4,
    ) -> EstrategiaRecomendacion:
        reglas = reglas or []

        if modo is ModoUpsell.MANUAL:
            # Aun en manual va la cascada atras: si el restaurante escribio dos
            # reglas y la franja pide cuatro tarjetas, las otras dos salen de
            # algun lado. Una franja a medias se ve peor que una automatica.
            return HibridaStrategy(
                [ReglasManualesStrategy(reglas), cascada_automatica(objetivo, self._lift_minimo)],
                nombre="manual con relleno",
            )

        if modo is ModoUpsell.AUTO:
            return cascada_automatica(objetivo, self._lift_minimo)

        if modo is ModoUpsell.HIBRIDO:
            return HibridaStrategy(
                [ReglasManualesStrategy(reglas), cascada_automatica(objetivo, self._lift_minimo)],
                nombre="hibrida",
            )

        if modo is ModoUpsell.POPULARIDAD:
            return PopularidadStrategy()

        if modo is ModoUpsell.AFINIDAD:
            return AfinidadCategoriaStrategy()

        raise ValueError(f"Modo desconocido: {modo}")

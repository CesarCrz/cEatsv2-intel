"""Estrategias hechas de otras estrategias. Patron Composite.

Son estrategias como cualquier otra: heredan de la misma clase abstracta y el
caso de uso no distingue entre una hoja y una compuesta. Por eso la cascada de
siete niveles se puede pasar donde antes iba una co-ocurrencia pelona, sin que
nadie mas se entere.
"""

from __future__ import annotations

from ceats_intel.domain.recomendacion.candidato import Candidato, NivelRespaldo, OrigenSugerencia
from ceats_intel.domain.recomendacion.estrategia import (
    ContextoRecomendacion,
    EstrategiaRecomendacion,
)
from ceats_intel.domain.valueobjects import ProductoId


class HibridaStrategy(EstrategiaRecomendacion):
    """Junta lo que proponen varias y se queda con lo mejor de cada producto.

    Es el modo por defecto: lo que el restaurante puso a mano manda, y lo
    automatico rellena los huecos que queden.
    """

    def __init__(
        self,
        hijas: list[EstrategiaRecomendacion] | None = None,
        nombre: str = "hibrida",
        peso: float = 1.0,
    ) -> None:
        super().__init__(nombre, peso)
        self._hijas: list[EstrategiaRecomendacion] = list(hijas or [])

    def agregar(self, estrategia: EstrategiaRecomendacion) -> HibridaStrategy:
        self._hijas.append(estrategia)
        return self

    @property
    def hijas(self) -> tuple[EstrategiaRecomendacion, ...]:
        return tuple(self._hijas)

    def origen(self) -> OrigenSugerencia:
        # El origen dominante es el de la primera hija que haya aportado algo.
        return self._hijas[0].origen() if self._hijas else OrigenSugerencia.DESTACADO

    def nivel(self) -> NivelRespaldo:
        return min((h.nivel() for h in self._hijas), default=NivelRespaldo.DESTACADOS)

    def candidatos(self, ctx: ContextoRecomendacion) -> list[Candidato]:
        mejor: dict[ProductoId, Candidato] = {}
        for hija in self._hijas:
            for candidato in hija.candidatos(ctx):
                actual = mejor.get(candidato.producto_id)
                # Si dos estrategias proponen el mismo producto, gana la que lo
                # puntuo mas alto. Como lo manual arranca en 1000, siempre le
                # gana a un lift, que rara vez pasa de 5.
                if actual is None or candidato.score > actual.score:
                    mejor[candidato.producto_id] = candidato
        return list(mejor.values())


class CascadaStrategy(EstrategiaRecomendacion):
    """Baja de escalon hasta juntar suficientes sugerencias.

    Cada escalon puede traer su propio historial: el nivel 1 mira la sucursal,
    el 2 el restaurante completo, el 3 una ventana mas larga. Por eso cada
    entrada es un par de estrategia y una funcion que le arma su contexto.

    Se detiene en cuanto junta `objetivo` candidatos. No sigue bajando por
    gusto: si el nivel 1 ya dio cuatro buenos, los de abajo sobran.
    """

    def __init__(
        self,
        escalones: list[tuple[EstrategiaRecomendacion, str]],
        objetivo: int = 4,
        nombre: str = "cascada",
        peso: float = 1.0,
    ) -> None:
        super().__init__(nombre, peso)
        if not escalones:
            raise ValueError("La cascada necesita al menos un escalon")
        # El segundo elemento dice de que historial come el escalon:
        # "sucursal" o "restaurante".
        self._escalones = tuple(escalones)
        self._objetivo = objetivo
        self._ultimo_nivel = escalones[0][0].nivel()

    @property
    def escalones(self) -> tuple[tuple[EstrategiaRecomendacion, str], ...]:
        return self._escalones

    def origen(self) -> OrigenSugerencia:
        return self._escalones[0][0].origen()

    def nivel(self) -> NivelRespaldo:
        """El nivel del ultimo calculo. El laboratorio lo muestra tal cual."""
        return self._ultimo_nivel

    def _contexto_de(self, ctx: ContextoRecomendacion, fuente: str) -> ContextoRecomendacion | None:
        if fuente == "sucursal":
            return ctx
        if fuente == "restaurante":
            if ctx.historial_restaurante is None:
                return None
            return ctx.con_historial(ctx.historial_restaurante)
        raise ValueError(f"Fuente desconocida: {fuente}")

    def candidatos(self, ctx: ContextoRecomendacion) -> list[Candidato]:
        juntados: dict[ProductoId, Candidato] = {}
        descartados: list[Candidato] = []

        for estrategia, fuente in self._escalones:
            contexto = self._contexto_de(ctx, fuente)
            if contexto is None:
                continue

            aporte = estrategia.candidatos(contexto)
            for candidato in aporte:
                if candidato.descartado:
                    descartados.append(candidato)
                    continue
                if candidato.producto_id in juntados:
                    continue
                if ctx.canasta.contiene(candidato.producto_id):
                    continue
                juntados[candidato.producto_id] = candidato.con_score(
                    self._score_en_banda(candidato.score, estrategia.nivel())
                )

            if len(juntados) >= self._objetivo:
                break

        self._ultimo_nivel = min(
            (c.nivel for c in juntados.values()), default=NivelRespaldo.DESTACADOS
        )

        # Los descartados van al final para que el laboratorio los pueda
        # mostrar con su motivo. `puntuar` los filtra antes de responder.
        return list(juntados.values()) + descartados

    @staticmethod
    def _score_en_banda(score: float, nivel: NivelRespaldo) -> float:
        """Mete el score en la banda que le toca a su escalon.

        Sin esto, los scores de distintos escalones se comparan entre si y no
        significan lo mismo. La afinidad por categoria puntua 1, 2 o 3 segun
        que tan bien encaja el tipo; el lift puntua 2.0 cuando la evidencia es
        buenisima. Comparados a pelo, un tres de afinidad le gana a un lift de
        dos, y termina ganando el respaldo generico sobre la evidencia real.
        Eso justo fue lo que salio en la demo de la Unidad 2.

        Cada escalon se queda con una banda de cien puntos y el escalon de
        arriba siempre le gana al de abajo. Adentro de la banda, el score
        original sigue mandando.
        """
        banda = (len(NivelRespaldo) + 1 - int(nivel)) * 100
        return banda + min(score, 99.0)

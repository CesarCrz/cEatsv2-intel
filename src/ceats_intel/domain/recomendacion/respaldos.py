"""Las estrategias que entran cuando la co-ocurrencia no alcanza.

La franja de sugerencias nunca se puede quedar vacia. Un grid de cuatro
tarjetas con dos huecos se ve roto y baja la conversion mas de lo que la sube
una sugerencia mediocre. Asi que siempre hay algo abajo que responde.
"""

from __future__ import annotations

from ceats_intel.domain.catalogo import TipoCategoria
from ceats_intel.domain.recomendacion.candidato import Candidato, NivelRespaldo, OrigenSugerencia
from ceats_intel.domain.recomendacion.estrategia import (
    ContextoRecomendacion,
    EstrategiaRecomendacion,
)
from ceats_intel.domain.valueobjects import ProductoId


class ReglaUpsell:
    """Una regla escrita a mano por el restaurante: si llevan A, ofrece B."""

    __slots__ = ("id", "disparador", "sugerido", "prioridad")

    def __init__(
        self,
        id_: str,
        disparador: ProductoId | None,
        sugerido: ProductoId,
        prioridad: int = 0,
    ) -> None:
        # Sin disparador, la regla aplica a cualquier canasta. Sirve para
        # "empuja siempre el postre nuevo".
        self.id = id_
        self.disparador = disparador
        self.sugerido = sugerido
        self.prioridad = prioridad

    def aplica(self, ctx: ContextoRecomendacion) -> bool:
        if self.disparador is None:
            return True
        return ctx.canasta.contiene(self.disparador)

    def __repr__(self) -> str:
        return f"ReglaUpsell({self.disparador} -> {self.sugerido}, prio={self.prioridad})"


class ReglasManualesStrategy(EstrategiaRecomendacion):
    """Lo que el restaurante decidio a mano. Manda sobre todo lo automatico."""

    def __init__(
        self, reglas: list[ReglaUpsell], nombre: str = "manual", peso: float = 1.0
    ) -> None:
        super().__init__(nombre, peso)
        self._reglas = tuple(reglas)

    def origen(self) -> OrigenSugerencia:
        return OrigenSugerencia.MANUAL

    def nivel(self) -> NivelRespaldo:
        return NivelRespaldo.SUCURSAL

    def candidatos(self, ctx: ContextoRecomendacion) -> list[Candidato]:
        salida: list[Candidato] = []
        vistos: set[ProductoId] = set()
        for regla in sorted(self._reglas, key=lambda r: (-r.prioridad, r.id)):
            if not regla.aplica(ctx) or regla.sugerido in vistos:
                continue
            producto = ctx.catalogo.producto(regla.sugerido)
            if producto is None:
                continue
            vistos.add(regla.sugerido)
            motivo = None if producto.es_sugerible() else "producto inactivo en esta sucursal"
            # Score alto y decreciente por prioridad. Lo manual tiene que
            # quedar arriba de cualquier lift, porque el restaurante ya dijo
            # que eso es lo que quiere empujar.
            salida.append(
                Candidato(
                    producto_id=regla.sugerido,
                    score=1000.0 + regla.prioridad,
                    origen=self.origen(),
                    nivel=NivelRespaldo.SUCURSAL,
                    descarte=motivo,
                )
            )
        return salida


class AfinidadCategoriaStrategy(EstrategiaRecomendacion):
    """Lo que hace un mesero: si ya traes el fuerte, te ofrece la bebida.

    Es el escalon que casi siempre salva el dia, porque no necesita historial.
    Sale de como esta armado el menu, asi que funciona desde el primer dia de un
    restaurante nuevo.
    """

    def __init__(self, nombre: str = "afinidad", peso: float = 1.0) -> None:
        super().__init__(nombre, peso)

    def origen(self) -> OrigenSugerencia:
        return OrigenSugerencia.AFINIDAD_CATEGORIA

    def nivel(self) -> NivelRespaldo:
        return NivelRespaldo.CATEGORIA

    def candidatos(self, ctx: ContextoRecomendacion) -> list[Candidato]:
        catalogo = ctx.catalogo
        tipos_en_canasta = [catalogo.tipo_de(p) for p in ctx.canasta]
        buscados = catalogo.tipos_que_acompanan(tipos_en_canasta)
        if not buscados:
            return []

        historial = ctx.historial
        salida: list[Candidato] = []
        for posicion, tipo in enumerate(buscados):
            if tipo is TipoCategoria.DESCONOCIDO:
                continue
            for producto in catalogo.productos_de_tipo(tipo):
                if ctx.canasta.contiene(producto.id):
                    continue
                # Dentro del tipo correcto, el desempate es que tan vendido es.
                # El 0.001 es para que el orden entre tipos mande y la venta
                # solo desempate adentro.
                popularidad = historial.soporte(producto.id) if not historial.vacio() else 0.0
                salida.append(
                    Candidato(
                        producto_id=producto.id,
                        score=(len(buscados) - posicion) + popularidad * 0.001,
                        origen=self.origen(),
                        nivel=NivelRespaldo.CATEGORIA,
                        descarte=None if producto.es_sugerible() else "producto inactivo",
                    )
                )
        return salida


class PopularidadStrategy(EstrategiaRecomendacion):
    """Los mas vendidos. No es inteligente, pero nunca falla si hay ventas."""

    def __init__(
        self,
        nombre: str = "popularidad",
        peso: float = 1.0,
        nivel: NivelRespaldo = NivelRespaldo.POPULAR_SUCURSAL,
    ) -> None:
        super().__init__(nombre, peso)
        self._nivel = nivel

    def origen(self) -> OrigenSugerencia:
        return OrigenSugerencia.POPULARIDAD

    def nivel(self) -> NivelRespaldo:
        return self._nivel

    def candidatos(self, ctx: ContextoRecomendacion) -> list[Candidato]:
        historial = ctx.historial
        if historial.vacio():
            return []
        salida: list[Candidato] = []
        for producto in ctx.catalogo.activos():
            soporte = historial.soporte(producto.id)
            if soporte <= 0:
                continue
            salida.append(
                Candidato(
                    producto_id=producto.id,
                    score=soporte,
                    origen=self.origen(),
                    nivel=self._nivel,
                )
            )
        return salida


class DestacadosStrategy(EstrategiaRecomendacion):
    """El ultimo escalon. Un restaurante sin un solo pedido tambien vende."""

    def __init__(self, nombre: str = "destacados", peso: float = 1.0) -> None:
        super().__init__(nombre, peso)

    def origen(self) -> OrigenSugerencia:
        return OrigenSugerencia.DESTACADO

    def nivel(self) -> NivelRespaldo:
        return NivelRespaldo.DESTACADOS

    def candidatos(self, ctx: ContextoRecomendacion) -> list[Candidato]:
        destacados = ctx.catalogo.destacados()
        salida: list[Candidato] = []
        for posicion, producto_id in enumerate(destacados):
            producto = ctx.catalogo.producto(producto_id)
            if producto is None or not producto.es_sugerible():
                continue
            salida.append(
                Candidato(
                    producto_id=producto_id,
                    score=float(len(destacados) - posicion),
                    origen=self.origen(),
                    nivel=NivelRespaldo.DESTACADOS,
                )
            )
        return salida

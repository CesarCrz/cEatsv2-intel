"""El caso de uso de recomendar. Una sola ruta para el checkout y para el CRM.

Esto es lo que garantiza que las sugerencias coincidan: no hay dos caminos. El
laboratorio manda `explicar=True` y recibe ademas el detalle, pero la lista de
sugerencias sale del mismo codigo, con la misma entrada y en el mismo orden.

Si alguien alguna vez mete aqui un `if origen == "laboratorio"` que cambie el
resultado, la coherencia se muere. `tests/test_coherencia.py` esta puesto justo
para cachar eso.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ceats_intel.application.fabrica import FabricaEstrategias, ModoUpsell
from ceats_intel.application.huella import VERSION_MODELO, calcular_huella
from ceats_intel.domain.catalogo import Catalogo
from ceats_intel.domain.entidades import Canasta, HistorialVentas
from ceats_intel.domain.recomendacion import (
    Candidato,
    ContextoRecomendacion,
    NivelRespaldo,
    ReglaUpsell,
)
from ceats_intel.domain.scoring import PipelineScoring, Traza
from ceats_intel.domain.scoring import combinadores as comb
from ceats_intel.domain.valueobjects import ProductoId


@dataclass(frozen=True)
class PeticionRecomendacion:
    canasta: Canasta
    modo: ModoUpsell = ModoUpsell.AUTO
    limite: int = 4
    alfa: float = 10.0
    lift_minimo: float = 1.0
    version_config: int = 0
    explicar: bool = False
    reglas: tuple[ReglaUpsell, ...] = ()


@dataclass(frozen=True)
class Sugerencia:
    producto_id: ProductoId
    nombre: str
    precio_centavos: int
    score: float
    origen: str
    nivel: int
    tiene_modificadores: bool
    evidencia: dict | None = None


@dataclass
class RespuestaRecomendacion:
    huella: str
    version_modelo: str
    modo: str
    nivel_alcanzado: int
    sugerencias: list[Sugerencia] = field(default_factory=list)
    descartados: list[dict] = field(default_factory=list)
    traza: list[dict] = field(default_factory=list)
    pedidos_considerados: int = 0

    def ids(self) -> list[str]:
        return [str(s.producto_id) for s in self.sugerencias]


class GenerarRecomendacionesUseCase:
    def __init__(self, fabrica: FabricaEstrategias | None = None) -> None:
        self._fabrica = fabrica or FabricaEstrategias()

    def _pipeline(self, catalogo: Catalogo, canasta: Canasta, limite: int) -> PipelineScoring:
        """El orden importa y no es arbitrario.

        Filtrar antes que nada, para no gastar en lo que ni existe. Diversificar
        antes del recorte, porque si recortara primero me quedaria con cuatro
        refrescos y despues ya no habria de donde sacar variedad.
        """
        return (
            PipelineScoring.identidad()
            .then("filtrar_inactivos", comb.filtrar_inactivos(catalogo))
            .then("quitar_canasta", comb.quitar_los_de_la_canasta(canasta))
            .then("penalizar_caros", comb.penalizar_caros(catalogo))
            .then("diversificar", comb.diversificar_por_categoria(catalogo, maximo=2))
            .then("top_n", comb.top_n(limite))
        )

    def ejecutar(
        self,
        peticion: PeticionRecomendacion,
        historial: HistorialVentas,
        catalogo: Catalogo,
        historial_restaurante: HistorialVentas | None = None,
    ) -> RespuestaRecomendacion:
        estrategia = self._fabrica.crear(
            peticion.modo, list(peticion.reglas), objetivo=peticion.limite
        )
        ctx = ContextoRecomendacion(
            canasta=peticion.canasta,
            historial=historial,
            catalogo=catalogo,
            historial_restaurante=historial_restaurante,
            alfa=peticion.alfa,
        )

        crudos = estrategia.candidatos(ctx)
        vivos = [c for c in crudos if not c.descartado]
        caidos = [c for c in crudos if c.descartado]

        pipeline = self._pipeline(catalogo, peticion.canasta, peticion.limite)
        finales, traza = pipeline.aplicar_con_traza(vivos)

        # Lo que no llego al corte tambien se explica. Sin esto, el laboratorio
        # solo enseña el resultado y no el porque, que es la mitad del valor.
        elegidos = {c.producto_id for c in finales}
        for c in vivos:
            if c.producto_id not in elegidos:
                caidos.append(c.descartar("no alcanzo el corte del top"))

        huella = calcular_huella(
            canasta=peticion.canasta,
            modo=str(peticion.modo),
            ventana=historial.ventana,
            limite=peticion.limite,
            version_config=peticion.version_config,
        )

        return RespuestaRecomendacion(
            huella=huella,
            version_modelo=VERSION_MODELO,
            modo=str(peticion.modo),
            nivel_alcanzado=int(
                min((c.nivel for c in finales), default=NivelRespaldo.DESTACADOS)
            ),
            sugerencias=[self._a_sugerencia(c, catalogo, peticion.explicar) for c in finales],
            descartados=(
                [self._a_descarte(c, catalogo) for c in caidos] if peticion.explicar else []
            ),
            traza=traza.como_lista() if peticion.explicar else [],
            pedidos_considerados=historial.total_pedidos,
        )

    @staticmethod
    def _a_sugerencia(c: Candidato, catalogo: Catalogo, explicar: bool) -> Sugerencia:
        producto = catalogo.producto(c.producto_id)
        return Sugerencia(
            producto_id=c.producto_id,
            nombre=producto.nombre if producto else "",
            precio_centavos=producto.precio.centavos if producto else 0,
            score=c.score,
            origen=str(c.origen),
            nivel=int(c.nivel),
            # Si el producto tiene modificadores, el front DEBE abrir el modal
            # en vez de mandarlo al carrito directo: si no, llega sin grupos
            # requeridos y cocina recibe un item invalido.
            tiene_modificadores=producto.tiene_modificadores if producto else False,
            evidencia=c.evidencia.como_dict() if (explicar and c.evidencia) else None,
        )

    @staticmethod
    def _a_descarte(c: Candidato, catalogo: Catalogo) -> dict:
        producto = catalogo.producto(c.producto_id)
        return {
            "producto_id": str(c.producto_id),
            "nombre": producto.nombre if producto else "",
            "score": c.score,
            "origen": str(c.origen),
            "motivo": c.descarte,
            "evidencia": c.evidencia.como_dict() if c.evidencia else None,
        }


# Traza se reexporta para que la capa de API no tenga que importar del dominio.
__all__ = [
    "GenerarRecomendacionesUseCase",
    "PeticionRecomendacion",
    "RespuestaRecomendacion",
    "Sugerencia",
    "Traza",
]

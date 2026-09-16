"""Co-ocurrencia con lift suavizado. Es el corazon del servicio.

El resolutor que hay hoy en cEats cuenta cuantas veces dos productos salieron
juntos y ordena por ahi. El problema es que el refresco sale con todo, asi que
el refresco gana siempre, aunque no tenga nada que ver con lo que el cliente
pidio.

Las tres medidas del analisis de canasta, sobre N pedidos:

    soporte(B)    = n(B) / N
    confianza(A→B) = n(A∩B) / n(A)
    lift(A→B)      = confianza(A→B) / soporte(B)

El lift responde la pregunta correcta: que tanto sube la probabilidad de B
CUANDO ya pidieron A, comparada con la probabilidad de B a secas. Lift 1 es
indiferencia. Arriba de 1 hay atraccion, abajo hay rechazo.

El suavizado
------------
Exigir un minimo duro de pedidos y tirar lo demas deja fuera a los restaurantes
chicos, que son justo los que mas necesitan la sugerencia. En vez de eso, la
confianza se jala hacia el soporte del candidato:

    confianza_suavizada(A→B) = ( n(A∩B) + α · soporte(B) ) / ( n(A) + α )

Con pocos datos de A el resultado se parece a "que tan popular es B"; conforme A
junta pedidos, el α pesa menos y converge a la confianza real. Es un estimador
m, y la gracia es que no hay salto entre "sin datos" y "con datos".

Nota: con n(A) = 0 la formula da exactamente soporte(B), y por lo tanto lift 1.
Eso es lo correcto: sin evidencia, la respuesta honesta es "no se", no "si".
"""

from __future__ import annotations

from ceats_intel.domain.entidades import HistorialVentas
from ceats_intel.domain.recomendacion.candidato import (
    Candidato,
    Evidencia,
    NivelRespaldo,
    OrigenSugerencia,
)
from ceats_intel.domain.recomendacion.estrategia import (
    ContextoRecomendacion,
    EstrategiaRecomendacion,
)
from ceats_intel.domain.valueobjects import ProductoId


def confianza_suavizada(
    historial: HistorialVentas, ancla: ProductoId, candidato: ProductoId, alfa: float
) -> tuple[float, Evidencia]:
    juntos = historial.veces_juntos(ancla, candidato)
    frecuencia_ancla = historial.frecuencia(ancla)
    soporte_candidato = historial.soporte(candidato)

    confianza = (juntos + alfa * soporte_candidato) / (frecuencia_ancla + alfa)
    lift = confianza / soporte_candidato if soporte_candidato > 0 else 0.0

    return lift, Evidencia(
        juntos=juntos,
        frecuencia_ancla=frecuencia_ancla,
        soporte_candidato=soporte_candidato,
        confianza=confianza,
        lift=lift,
        pedidos=historial.total_pedidos,
    )


class CoOcurrenciaStrategy(EstrategiaRecomendacion):
    def __init__(
        self,
        nombre: str = "co-ocurrencia",
        peso: float = 1.0,
        lift_minimo: float = 1.0,
        nivel: NivelRespaldo = NivelRespaldo.SUCURSAL,
    ) -> None:
        super().__init__(nombre, peso)
        self._lift_minimo = lift_minimo
        self._nivel = nivel

    def origen(self) -> OrigenSugerencia:
        return OrigenSugerencia.CO_OCURRENCIA

    def nivel(self) -> NivelRespaldo:
        return self._nivel

    def candidatos(self, ctx: ContextoRecomendacion) -> list[Candidato]:
        historial = ctx.historial
        if historial.vacio() or ctx.canasta.vacia():
            return []

        mejores: dict[ProductoId, tuple[float, Evidencia]] = {}

        for ancla in ctx.canasta:
            for candidato in historial.acompanantes(ancla):
                if ctx.canasta.contiene(candidato):
                    continue
                lift, evidencia = confianza_suavizada(historial, ancla, candidato, ctx.alfa)
                # Me quedo con el mejor par, no con el promedio. Si el cliente
                # trae cinco cosas, promediar castiga al acompanante perfecto de
                # una sola de ellas, y ese es justo el que quiero ofrecerle.
                actual = mejores.get(candidato)
                if actual is None or lift > actual[0]:
                    mejores[candidato] = (lift, evidencia)

        salida: list[Candidato] = []
        for producto_id, (lift, evidencia) in mejores.items():
            producto = ctx.catalogo.producto(producto_id)
            if producto is None:
                # Se vendio en la ventana pero ya no esta en el menu de esta
                # sucursal. No lo puedo ofrecer.
                continue
            motivo = None
            if lift < self._lift_minimo:
                motivo = f"lift {lift:.2f}, por debajo de {self._lift_minimo:.2f}"
            salida.append(
                Candidato(
                    producto_id=producto_id,
                    score=lift,
                    origen=self.origen(),
                    nivel=self._nivel,
                    evidencia=evidencia,
                    descarte=motivo,
                )
            )
        return salida

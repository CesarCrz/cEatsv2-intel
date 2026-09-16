"""Un producto propuesto, con de donde salio y por que.

`Candidato` es inmutable a proposito: el pipeline de la Unidad 3 lo va
transformando etapa por etapa, y si cada etapa pudiera mutar el objeto en su
lugar seria imposible saber quien cambio que. Cada transformacion devuelve uno
nuevo.
"""

from __future__ import annotations

from enum import Enum

from ceats_intel.domain.valueobjects import ProductoId


class OrigenSugerencia(str, Enum):
    """De donde salio la sugerencia. Va en la respuesta y se ve en el CRM."""

    MANUAL = "manual"
    CO_OCURRENCIA = "cooccurrence"
    AFINIDAD_CATEGORIA = "afinidad_categoria"
    POPULARIDAD = "popularidad"
    DESTACADO = "destacado"

    def __str__(self) -> str:
        return self.value


class NivelRespaldo(int, Enum):
    """Que tan abajo de la cascada hubo que ir para encontrar algo.

    Entre mas alto el numero, menos datos habia. El laboratorio lo muestra tal
    cual: prefiero decir "nivel 4, no alcanzan los datos" que fingir precision.
    """

    SUCURSAL = 1
    RESTAURANTE = 2
    VENTANA_LARGA = 3
    CATEGORIA = 4
    POPULAR_SUCURSAL = 5
    POPULAR_RESTAURANTE = 6
    DESTACADOS = 7


class Confianza(str, Enum):
    ALTA = "alta"
    MEDIA = "media"
    BAJA = "baja"

    def __str__(self) -> str:
        return self.value


class Candidato:
    __slots__ = ("_producto_id", "_score", "_origen", "_nivel", "_evidencia", "_descarte")

    def __init__(
        self,
        producto_id: ProductoId,
        score: float,
        origen: OrigenSugerencia,
        nivel: NivelRespaldo,
        evidencia: Evidencia | None = None,
        descarte: str | None = None,
    ) -> None:
        self._producto_id = producto_id
        # Seis decimales. Dos scores que salen iguales en la formula deben salir
        # iguales aqui: si un error de flotante en el decimo decimal los separa,
        # el desempate por id no se aplica y el orden deja de ser reproducible.
        self._score = round(float(score), 6)
        self._origen = origen
        self._nivel = nivel
        self._evidencia = evidencia
        self._descarte = descarte

    @property
    def producto_id(self) -> ProductoId:
        return self._producto_id

    @property
    def score(self) -> float:
        return self._score

    @property
    def origen(self) -> OrigenSugerencia:
        return self._origen

    @property
    def nivel(self) -> NivelRespaldo:
        return self._nivel

    @property
    def evidencia(self) -> Evidencia | None:
        return self._evidencia

    @property
    def descarte(self) -> str | None:
        """Por que se cayo, si se cayo. El laboratorio lo muestra."""
        return self._descarte

    @property
    def descartado(self) -> bool:
        return self._descarte is not None

    def con_score(self, nuevo: float) -> Candidato:
        return Candidato(
            self._producto_id, nuevo, self._origen, self._nivel, self._evidencia, self._descarte
        )

    def descartar(self, motivo: str) -> Candidato:
        return Candidato(
            self._producto_id, self._score, self._origen, self._nivel, self._evidencia, motivo
        )

    def clave_orden(self) -> tuple[float, str]:
        """Orden total y estable: score de mayor a menor, luego id.

        Sin el id como segundo criterio, dos empates quedarian en el orden en
        que los recorrio un dict, y ese orden no es algo con lo que quiera
        apostar la coherencia entre el checkout y el laboratorio.
        """
        return (-self._score, str(self._producto_id))

    def __eq__(self, otro: object) -> bool:
        if not isinstance(otro, Candidato):
            return NotImplemented
        return (
            self._producto_id == otro._producto_id
            and self._score == otro._score
            and self._origen == otro._origen
        )

    def __hash__(self) -> int:
        return hash((self._producto_id, self._score, self._origen))

    def __repr__(self) -> str:
        cola = f", descartado={self._descarte!r}" if self._descarte else ""
        return f"Candidato({self._producto_id}, {self._score:.4f}, {self._origen}{cola})"


class Evidencia:
    """Los numeros detras de una sugerencia de co-ocurrencia.

    Existe para el laboratorio del CRM y para poder explicar el porque delante
    de alguien. Sin esto la recomendacion es una caja negra.
    """

    __slots__ = ("juntos", "frecuencia_ancla", "soporte_candidato", "confianza", "lift", "pedidos")

    def __init__(
        self,
        juntos: int,
        frecuencia_ancla: int,
        soporte_candidato: float,
        confianza: float,
        lift: float,
        pedidos: int,
    ) -> None:
        self.juntos = juntos
        self.frecuencia_ancla = frecuencia_ancla
        self.soporte_candidato = round(soporte_candidato, 6)
        self.confianza = round(confianza, 6)
        self.lift = round(lift, 6)
        self.pedidos = pedidos

    def confianza_estadistica(self) -> Confianza:
        """Que tanto creerle. Se decide por cuantos pedidos sostienen el par."""
        if self.frecuencia_ancla >= 30 and self.juntos >= 8:
            return Confianza.ALTA
        if self.frecuencia_ancla >= 12 and self.juntos >= 3:
            return Confianza.MEDIA
        return Confianza.BAJA

    def como_dict(self) -> dict[str, float | int | str]:
        return {
            "juntos": self.juntos,
            "frecuencia_ancla": self.frecuencia_ancla,
            "soporte_candidato": self.soporte_candidato,
            "confianza": self.confianza,
            "lift": self.lift,
            "pedidos": self.pedidos,
            "confianza_estadistica": str(self.confianza_estadistica()),
        }

    def __repr__(self) -> str:
        return f"Evidencia(juntos={self.juntos}, lift={self.lift:.2f})"

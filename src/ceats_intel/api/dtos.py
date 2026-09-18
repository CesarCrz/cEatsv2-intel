"""DTOs de entrada y salida de la API.

Los de `/v1/recomendaciones` reflejan `CONTRATO_INTEL.md` al pie de la letra:
cualquier cambio de forma aqui tiene que reflejarse ahi primero, porque el
backend de cEats arma su peticion contra ese documento.

Validacion estricta a proposito (SEGURIDAD.md, "Validacion de entrada"): UUID
con formato, tope al tamano de la canasta, `limite` acotado. `extra="forbid"`
en los DTOs de entrada para que un campo inesperado truene en vez de
ignorarse en silencio.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# Mismo patron que `domain/valueobjects/identificadores.py`, en mayusculas y
# minusculas: la validacion de forma vive aqui, la de significado (que tipo de
# UUID es) la hace el dominio al construir el value object.
UUIDStr = Annotated[
    str,
    StringConstraints(
        pattern=r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
    ),
]

ModoUpsellDTO = Literal["auto", "manual", "hibrido", "popularidad", "afinidad"]

_MAX_CANASTA = 50
_MAX_REGLAS = 50


# --------------------------------------------------------------- peticion


class ReglaUpsellDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUIDStr
    disparador: UUIDStr | None = None
    sugerido: UUIDStr
    prioridad: int = 0


class PeticionRecomendacionDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sucursal_id: UUIDStr
    restaurante_id: UUIDStr
    canasta: Annotated[list[UUIDStr], Field(max_length=_MAX_CANASTA)]
    modo: ModoUpsellDTO = "auto"
    limite: Annotated[int, Field(ge=1, le=10)] = 4
    explicar: bool = False
    version_config: int = 0
    alfa: float | None = Field(default=None, gt=0)
    lift_minimo: float | None = None
    reglas: Annotated[list[ReglaUpsellDTO], Field(max_length=_MAX_REGLAS)] = Field(
        default_factory=list
    )


# ---------------------------------------------------------------- respuesta


class EvidenciaDTO(BaseModel):
    juntos: int
    frecuencia_ancla: int
    soporte_candidato: float
    confianza: float
    lift: float
    pedidos: int
    confianza_estadistica: str


class SugerenciaDTO(BaseModel):
    producto_id: str
    nombre: str
    precio_centavos: int
    score: float
    origen: str
    nivel: int
    tiene_modificadores: bool
    evidencia: EvidenciaDTO | None = None


class DescarteDTO(BaseModel):
    producto_id: str
    nombre: str
    score: float
    origen: str
    motivo: str | None
    evidencia: EvidenciaDTO | None = None


class TrazaEtapaDTO(BaseModel):
    etapa: str
    entraron: int
    salieron: int


class RespuestaRecomendacionDTO(BaseModel):
    huella: str
    version_modelo: str
    modo: str
    nivel_alcanzado: int
    pedidos_considerados: int
    sugerencias: list[SugerenciaDTO]
    descartados: list[DescarteDTO] = Field(default_factory=list)
    traza: list[TrazaEtapaDTO] = Field(default_factory=list)


# --------------------------------------------------------------- analitica


class PuntoPronosticoDTO(BaseModel):
    paso: int
    valor: float


class RespuestaPronosticoDTO(BaseModel):
    sucursal_id: str
    modelo: str
    puntos: list[PuntoPronosticoDTO]


class ProductoMenuEngineeringDTO(BaseModel):
    producto_id: str
    nombre: str
    cuadrante: str


class RespuestaMenuEngineeringDTO(BaseModel):
    sucursal_id: str
    productos: list[ProductoMenuEngineeringDTO]


class AnomaliaDTO(BaseModel):
    indice: int
    valor: float
    esperado: float
    z: float
    es_caida: bool


class RespuestaAnomaliasDTO(BaseModel):
    sucursal_id: str
    serie: str
    anomalias: list[AnomaliaDTO]


# --------------------------------------------------------------- lambdacalc

_MAX_TERMINO = 2000


class PeticionLambdaDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    termino: Annotated[str, Field(min_length=1, max_length=_MAX_TERMINO)]


class PasoReduccionDTO(BaseModel):
    regla: str
    antes: str
    despues: str


class RespuestaLambdaDTO(BaseModel):
    resultado: str
    pasos: list[PasoReduccionDTO]

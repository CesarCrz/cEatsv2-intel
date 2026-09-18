"""GET /v1/pronostico/demanda, /v1/menu-engineering, /v1/anomalias.

Estos tres alimentan al CRM (laboratorio y dashboards), no al checkout: no
comparten el requisito de timeout de 2s de `/v1/recomendaciones` porque aqui
del otro lado hay un superadmin viendo un spinner, no un cliente pagando.

CONTRATO_INTEL.md solo nombra estas rutas sin detallar parametros; el resto de
la forma (query params, campos de respuesta) se definio aqui a partir de lo
que ya ofrece el dominio (`ModeloPronostico`, `MenuEngineeringClasificador`,
`DetectorAnomalias`). Si el CRM necesita otra forma, es cambio de contrato.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query

from ceats_intel.api.dependencias import (
    obtener_repositorio_catalogo,
    obtener_repositorio_ventas,
    verificar_llave,
)
from ceats_intel.api.dtos import (
    AnomaliaDTO,
    ProductoMenuEngineeringDTO,
    PuntoPronosticoDTO,
    RespuestaAnomaliasDTO,
    RespuestaMenuEngineeringDTO,
    RespuestaPronosticoDTO,
    UUIDStr,
)
from ceats_intel.domain.analitica import DetectorAnomalias, MenuEngineeringClasificador
from ceats_intel.domain.pronostico import EstacionalSemanalModelo
from ceats_intel.domain.valueobjects import SucursalId, VentanaTemporal
from ceats_intel.infrastructure.cache import RepositorioCacheado
from ceats_intel.infrastructure.config import Settings, obtener_settings
from ceats_intel.infrastructure.repositorios import RepositorioCatalogoHTTP

router = APIRouter(prefix="/v1", tags=["analitica"], dependencies=[Depends(verificar_llave)])

_HORAS_DIA = 24
_MAX_PASOS_PRONOSTICO = 168  # una semana de horas, tope razonable de respuesta


@router.get("/pronostico/demanda", response_model=RespuestaPronosticoDTO)
async def pronostico_demanda(
    sucursal_id: UUIDStr = Query(...),
    pasos: int = Query(default=_HORAS_DIA, ge=1, le=_MAX_PASOS_PRONOSTICO),
    repo_ventas: RepositorioCacheado = Depends(obtener_repositorio_ventas),
    settings: Settings = Depends(obtener_settings),
) -> RespuestaPronosticoDTO:
    sid = SucursalId(sucursal_id)
    ventana = VentanaTemporal.ultimos_dias(settings.ventana_dias)
    historial = await repo_ventas.historial(sid, ventana)

    modelo = EstacionalSemanalModelo(periodo=_HORAS_DIA)
    serie = [float(v) for v in historial.serie_por_hora()]
    if any(serie):
        modelo.entrenar(serie)
        prediccion = modelo.predecir(pasos)
    else:
        # Sin ventas en la ventana no hay nada que ajustar; `entrenar()`
        # tronaria con una serie en ceros de division-por-cero en la media.
        prediccion = [0.0] * pasos

    return RespuestaPronosticoDTO(
        sucursal_id=sucursal_id,
        modelo=modelo.nombre,
        puntos=[PuntoPronosticoDTO(paso=i, valor=v) for i, v in enumerate(prediccion)],
    )


@router.get("/menu-engineering", response_model=RespuestaMenuEngineeringDTO)
async def menu_engineering(
    sucursal_id: UUIDStr = Query(...),
    repo_ventas: RepositorioCacheado = Depends(obtener_repositorio_ventas),
    repo_catalogo: RepositorioCatalogoHTTP = Depends(obtener_repositorio_catalogo),
    settings: Settings = Depends(obtener_settings),
) -> RespuestaMenuEngineeringDTO:
    sid = SucursalId(sucursal_id)
    ventana = VentanaTemporal.ultimos_dias(settings.ventana_dias)
    historial = await repo_ventas.historial(sid, ventana)
    catalogo = await repo_catalogo.catalogo(sid)

    clasificacion = MenuEngineeringClasificador().clasificar(historial, catalogo)
    productos = [
        ProductoMenuEngineeringDTO(
            producto_id=str(producto_id),
            nombre=producto.nombre if (producto := catalogo.producto(producto_id)) else "",
            cuadrante=str(cuadrante),
        )
        for producto_id, cuadrante in clasificacion.items()
    ]
    return RespuestaMenuEngineeringDTO(sucursal_id=sucursal_id, productos=productos)


@router.get("/anomalias", response_model=RespuestaAnomaliasDTO)
async def anomalias(
    sucursal_id: UUIDStr = Query(...),
    serie: Literal["hora", "dia_semana"] = Query(default="dia_semana"),
    repo_ventas: RepositorioCacheado = Depends(obtener_repositorio_ventas),
    settings: Settings = Depends(obtener_settings),
) -> RespuestaAnomaliasDTO:
    sid = SucursalId(sucursal_id)
    ventana = VentanaTemporal.ultimos_dias(settings.ventana_dias)
    historial = await repo_ventas.historial(sid, ventana)

    valores = historial.serie_por_hora() if serie == "hora" else historial.serie_por_dia_semana()
    detectadas = DetectorAnomalias().detectar([float(v) for v in valores])

    return RespuestaAnomaliasDTO(
        sucursal_id=sucursal_id,
        serie=serie,
        anomalias=[
            AnomaliaDTO(
                indice=a.indice, valor=a.valor, esperado=a.esperado, z=a.z, es_caida=a.es_caida
            )
            for a in detectadas
        ],
    )

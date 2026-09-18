"""POST /v1/recomendaciones -- el unico endpoint que ve el checkout.

Arma el `PeticionRecomendacion` del caso de uso a partir del DTO validado,
junta el historial y el catalogo por HTTP (cacheados donde aplica), y traduce
`RespuestaRecomendacion` de vuelta a la forma exacta de CONTRATO_INTEL.md.

Nota sobre el escalon 2/3 de la cascada (co-ocurrencia de restaurante /
ventana larga): el contrato solo expone `GET .../ventas?sucursal_id=`, no hay
forma de pedirle al backend "todas las sucursales de este restaurante". Se
aproxima usando la misma sucursal con la ventana larga
(`VENTANA_LARGA_DIAS`) como `historial_restaurante`. Para una sucursal unica
(el caso comun hoy) es exacto; para un restaurante con varias sucursales es
una aproximacion razonable pero no perfecta -- lo correcto seria que el
backend agregara un endpoint por `restaurante_id`. Queda anotado para quien
retome esto.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ceats_intel.api.dependencias import (
    obtener_repositorio_catalogo,
    obtener_repositorio_ventas,
    verificar_llave,
)
from ceats_intel.api.dtos import (
    DescarteDTO,
    EvidenciaDTO,
    PeticionRecomendacionDTO,
    RespuestaRecomendacionDTO,
    SugerenciaDTO,
    TrazaEtapaDTO,
)
from ceats_intel.application.fabrica import FabricaEstrategias, ModoUpsell
from ceats_intel.application.recomendar import (
    GenerarRecomendacionesUseCase,
    PeticionRecomendacion,
    RespuestaRecomendacion,
)
from ceats_intel.domain.entidades import Canasta
from ceats_intel.domain.recomendacion import ReglaUpsell
from ceats_intel.domain.valueobjects import ProductoId, SucursalId, VentanaTemporal
from ceats_intel.infrastructure.cache import RepositorioCacheado
from ceats_intel.infrastructure.config import Settings, obtener_settings
from ceats_intel.infrastructure.repositorios import RepositorioCatalogoHTTP

router = APIRouter(prefix="/v1", tags=["recomendaciones"], dependencies=[Depends(verificar_llave)])

_ALFA_POR_DEFECTO = 10.0
_LIFT_MINIMO_POR_DEFECTO = 1.0


@router.post("/recomendaciones", response_model=RespuestaRecomendacionDTO)
async def recomendaciones(
    peticion: PeticionRecomendacionDTO,
    repo_ventas: RepositorioCacheado = Depends(obtener_repositorio_ventas),
    repo_catalogo: RepositorioCatalogoHTTP = Depends(obtener_repositorio_catalogo),
    settings: Settings = Depends(obtener_settings),
) -> RespuestaRecomendacionDTO:
    sucursal_id = SucursalId(peticion.sucursal_id)
    canasta = Canasta(sucursal_id, (ProductoId(p) for p in peticion.canasta))
    reglas = tuple(
        ReglaUpsell(
            r.id,
            ProductoId(r.disparador) if r.disparador else None,
            ProductoId(r.sugerido),
            r.prioridad,
        )
        for r in peticion.reglas
    )

    ventana = VentanaTemporal.ultimos_dias(settings.ventana_dias)
    ventana_larga = VentanaTemporal.ultimos_dias(settings.ventana_larga_dias)

    historial = await repo_ventas.historial(sucursal_id, ventana)
    historial_restaurante = await repo_ventas.historial(sucursal_id, ventana_larga)
    catalogo = await repo_catalogo.catalogo(sucursal_id)

    lift_minimo = (
        peticion.lift_minimo if peticion.lift_minimo is not None else _LIFT_MINIMO_POR_DEFECTO
    )
    # La fabrica fija el lift minimo al construirse (ver `application/fabrica.py`),
    # asi que si la peticion trae uno propio hay que crear la fabrica con ese
    # valor en vez de con el de por defecto.
    caso_uso = GenerarRecomendacionesUseCase(FabricaEstrategias(lift_minimo=lift_minimo))

    peticion_uc = PeticionRecomendacion(
        canasta=canasta,
        modo=ModoUpsell(peticion.modo),
        limite=peticion.limite,
        alfa=peticion.alfa if peticion.alfa is not None else _ALFA_POR_DEFECTO,
        lift_minimo=lift_minimo,
        version_config=peticion.version_config,
        explicar=peticion.explicar,
        reglas=reglas,
    )
    respuesta = caso_uso.ejecutar(peticion_uc, historial, catalogo, historial_restaurante)
    return _a_dto(respuesta)


def _a_dto(respuesta: RespuestaRecomendacion) -> RespuestaRecomendacionDTO:
    return RespuestaRecomendacionDTO(
        huella=respuesta.huella,
        version_modelo=respuesta.version_modelo,
        modo=respuesta.modo,
        nivel_alcanzado=respuesta.nivel_alcanzado,
        pedidos_considerados=respuesta.pedidos_considerados,
        sugerencias=[
            SugerenciaDTO(
                producto_id=str(s.producto_id),
                nombre=s.nombre,
                precio_centavos=s.precio_centavos,
                score=s.score,
                origen=s.origen,
                nivel=s.nivel,
                tiene_modificadores=s.tiene_modificadores,
                evidencia=EvidenciaDTO(**s.evidencia) if s.evidencia else None,
            )
            for s in respuesta.sugerencias
        ],
        descartados=[
            DescarteDTO(
                producto_id=d["producto_id"],
                nombre=d["nombre"],
                score=d["score"],
                origen=d["origen"],
                motivo=d["motivo"],
                evidencia=EvidenciaDTO(**d["evidencia"]) if d.get("evidencia") else None,
            )
            for d in respuesta.descartados
        ],
        traza=[TrazaEtapaDTO(**t) for t in respuesta.traza],
    )

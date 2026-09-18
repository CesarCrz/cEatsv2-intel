"""POST /v1/lambda/reducir -- el interprete de la Unidad 3, expuesto.

Nada de `eval` ni `exec`: el evaluador solo recorre el AST que arma el parser
de descenso recursivo. `ErrorDeSintaxis` es un termino mal escrito (400,
error del cliente); `LimiteReduccionError` es un termino que no llega a forma
normal dentro de `MAX_PASOS_LAMBDA` (422 -- el termino esta bien formado, pero
semanticamente no converge, como el Omega clasico).

Los pasos se recortan a `_TOPE_PASOS_RESPUESTA` para no mandar una respuesta
enorme si alguien pide un termino que tarda miles de pasos en normalizarse.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ceats_intel.api.dependencias import verificar_llave
from ceats_intel.api.dtos import PasoReduccionDTO, PeticionLambdaDTO, RespuestaLambdaDTO
from ceats_intel.domain.lambdacalc import ErrorDeSintaxis, Evaluador, LimiteReduccionError, parsear
from ceats_intel.infrastructure.config import Settings, obtener_settings

router = APIRouter(
    prefix="/v1/lambda", tags=["lambdacalc"], dependencies=[Depends(verificar_llave)]
)

_TOPE_PASOS_RESPUESTA = 200


@router.post("/reducir", response_model=RespuestaLambdaDTO)
async def reducir(
    peticion: PeticionLambdaDTO,
    settings: Settings = Depends(obtener_settings),
) -> RespuestaLambdaDTO:
    try:
        termino = parsear(peticion.termino)
    except ErrorDeSintaxis as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    evaluador = Evaluador(max_pasos=settings.max_pasos_lambda)
    try:
        resultado, pasos = evaluador.reducir_con_pasos(termino)
    except LimiteReduccionError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"El termino no llega a forma normal en {settings.max_pasos_lambda} pasos. "
                "Puede que no tenga forma normal (por ejemplo, Omega)."
            ),
        ) from error

    return RespuestaLambdaDTO(
        resultado=str(resultado),
        pasos=[
            PasoReduccionDTO(regla=p.regla, antes=p.antes, despues=p.despues)
            for p in pasos[:_TOPE_PASOS_RESPUESTA]
        ],
    )

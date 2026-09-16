"""La huella de una decision.

Es lo que hace comprobable que el laboratorio del CRM y el menu publico dan lo
mismo. Dos peticiones con la misma huella tienen que devolver el mismo
resultado, y si no, es un bug.

Entra todo lo que puede cambiar la respuesta:

    sucursal | canasta ordenada | modo | version de config | ventana | version
    del modelo | limite

Y no entra nada mas. La hora exacta no entra (por eso la ventana se redondea al
dia), ni el origen de la peticion, ni quien la pidio.

`version_modelo` sube cuando cambian los pesos o el algoritmo. Sin eso, una
decision vieja y una nueva compartirian huella y pareceria que el sistema se
contradice.
"""

from __future__ import annotations

import hashlib

from ceats_intel.domain.entidades import Canasta
from ceats_intel.domain.valueobjects import VentanaTemporal

# Se sube a mano cuando cambia algo que mueve los resultados.
VERSION_MODELO = "1.0.0"


def calcular_huella(
    canasta: Canasta,
    modo: str,
    ventana: VentanaTemporal,
    limite: int,
    version_config: int = 0,
    version_modelo: str = VERSION_MODELO,
) -> str:
    partes = [
        str(canasta.sucursal_id),
        canasta.clave(),
        modo,
        str(version_config),
        ventana.clave(),
        version_modelo,
        str(limite),
    ]
    crudo = "|".join(partes).encode("utf-8")
    # 16 caracteres alcanzan de sobra: esto no protege nada, nada mas identifica
    # una decision para poder compararla. No es un secreto.
    return hashlib.sha256(crudo).hexdigest()[:16]

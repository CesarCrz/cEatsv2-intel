"""Las etapas del pipeline.

Cada funcion de aqui es de orden superior: no transforma candidatos, devuelve
una funcion que transforma candidatos. `top_n(3)` no recorta nada, entrega el
recortador. Eso es currificacion, y es lo que permite armar el pipeline una vez
y aplicarlo muchas.

Todas son puras. Ninguna toca su entrada: construyen una lista nueva.
"""

from __future__ import annotations

from collections.abc import Callable

from ceats_intel.domain.catalogo import Catalogo
from ceats_intel.domain.entidades import Canasta
from ceats_intel.domain.recomendacion.candidato import Candidato

Etapa = Callable[[list[Candidato]], list[Candidato]]


def componer(f: Etapa, g: Etapa) -> Etapa:
    """(f ∘ g)(x) = f(g(x)). Primero g, luego f."""
    return lambda candidatos: f(g(candidatos))


def identidad() -> Etapa:
    """La funcion I del calculo lambda: \\x. x."""
    return lambda candidatos: list(candidatos)


def filtrar_inactivos(catalogo: Catalogo) -> Etapa:
    def etapa(candidatos: list[Candidato]) -> list[Candidato]:
        salida = []
        for c in candidatos:
            producto = catalogo.producto(c.producto_id)
            if producto is None:
                salida.append(c.descartar("no esta en el menu de esta sucursal"))
            elif not producto.es_sugerible():
                salida.append(c.descartar("producto inactivo en esta sucursal"))
            else:
                salida.append(c)
        return [c for c in salida if not c.descartado]

    return etapa


def quitar_los_de_la_canasta(canasta: Canasta) -> Etapa:
    def etapa(candidatos: list[Candidato]) -> list[Candidato]:
        return [c for c in candidatos if not canasta.contiene(c.producto_id)]

    return etapa


def escalar(factor: float) -> Etapa:
    if factor <= 0:
        raise ValueError("El factor debe ser positivo")
    return lambda candidatos: [c.con_score(c.score * factor) for c in candidatos]


def penalizar_caros(catalogo: Catalogo, tope_relativo: float = 1.0) -> Etapa:
    """Baja el score de lo que cuesta mas que lo que el cliente ya lleva.

    Un upsell de 400 pesos sobre un carrito de 200 no lo agrega nadie. No lo
    quito, nada mas lo mando abajo: si no hay de otra, que salga.
    """

    def etapa(candidatos: list[Candidato]) -> list[Candidato]:
        precios = [
            catalogo.producto(c.producto_id).precio.centavos  # type: ignore[union-attr]
            for c in candidatos
            if catalogo.producto(c.producto_id) is not None
        ]
        if not precios:
            return list(candidatos)
        mediana = sorted(precios)[len(precios) // 2]
        limite = mediana * (1 + tope_relativo)
        salida = []
        for c in candidatos:
            producto = catalogo.producto(c.producto_id)
            if producto is not None and producto.precio.centavos > limite:
                salida.append(c.con_score(c.score * 0.5))
            else:
                salida.append(c)
        return salida

    return etapa


def diversificar_por_categoria(catalogo: Catalogo, maximo: int = 2) -> Etapa:
    """No mas de `maximo` productos de la misma categoria.

    Sin esto, la lista se llena de refrescos: si un refresco tiene buen lift,
    los otros cuatro del menu tambien, y el cliente ve cuatro tarjetas de lo
    mismo. Se recorre en el orden ya definido, asi que sigue siendo determinista.
    """

    def etapa(candidatos: list[Candidato]) -> list[Candidato]:
        ordenados = sorted(candidatos, key=Candidato.clave_orden)
        cupo: dict[str, int] = {}
        salida: list[Candidato] = []
        for c in ordenados:
            producto = catalogo.producto(c.producto_id)
            categoria = str(producto.categoria_id) if producto and producto.categoria_id else "-"
            usados = cupo.get(categoria, 0)
            if usados >= maximo:
                continue
            cupo[categoria] = usados + 1
            salida.append(c)
        return salida

    return etapa


def top_n(n: int) -> Etapa:
    if n < 1:
        raise ValueError("n debe ser al menos 1")

    def etapa(candidatos: list[Candidato]) -> list[Candidato]:
        return sorted(candidatos, key=Candidato.clave_orden)[:n]

    return etapa


def ordenar() -> Etapa:
    return lambda candidatos: sorted(candidatos, key=Candidato.clave_orden)

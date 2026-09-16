"""El score final como composicion de funciones puras.

Aqui es donde la Unidad 3 deja de ser teoria. Cada etapa es una funcion de
lista de candidatos a lista de candidatos, sin estado y sin efectos. El
pipeline las compone:

    score = top_n(4) ∘ diversificar ∘ penalizar ∘ escalar ∘ filtrar

Componer funciones y despues aplicarlas a un argumento es exactamente lo que
hace la reduccion beta. La diferencia con el intérprete de `lambdacalc` es que
alli las funciones son terminos que reduzco yo, y aqui son cierres de Python
que reduce el intérprete del lenguaje. La idea es la misma.

Que sean puras da dos cosas que necesito: el mismo pipeline sobre la misma
entrada da siempre la misma salida (que es de lo que depende que el laboratorio
coincida con el checkout), y puedo registrar cuantos candidatos entraron y
salieron de cada etapa sin que eso cambie el resultado.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from ceats_intel.domain.recomendacion.candidato import Candidato

Etapa = Callable[[list[Candidato]], list[Candidato]]


class Traza:
    """Cuantos candidatos entraron y salieron de cada etapa.

    Es lo que el laboratorio dibuja para explicar de donde salio el resultado.
    Se llena por fuera de las etapas: ellas siguen siendo puras.
    """

    __slots__ = ("_filas",)

    def __init__(self) -> None:
        self._filas: list[tuple[str, int, int]] = []

    def registrar(self, etapa: str, entraron: int, salieron: int) -> None:
        self._filas.append((etapa, entraron, salieron))

    @property
    def filas(self) -> tuple[tuple[str, int, int], ...]:
        return tuple(self._filas)

    def como_lista(self) -> list[dict[str, str | int]]:
        return [{"etapa": e, "entraron": i, "salieron": o} for e, i, o in self._filas]

    def __str__(self) -> str:
        return "\n".join(f"{e:<28} {i:>3} -> {o:>3}" for e, i, o in self._filas)


class PipelineScoring:
    """Una cadena de etapas. Inmutable: `then` devuelve un pipeline nuevo."""

    __slots__ = ("_etapas",)

    def __init__(self, etapas: Sequence[tuple[str, Etapa]] = ()) -> None:
        self._etapas = tuple(etapas)

    @classmethod
    def identidad(cls) -> PipelineScoring:
        """El pipeline vacio. Aplicarlo no cambia nada: es la funcion I."""
        return cls()

    def then(self, nombre: str, etapa: Etapa) -> PipelineScoring:
        return PipelineScoring((*self._etapas, (nombre, etapa)))

    @property
    def nombres(self) -> tuple[str, ...]:
        return tuple(n for n, _ in self._etapas)

    def aplicar(self, candidatos: list[Candidato]) -> list[Candidato]:
        return self.aplicar_con_traza(candidatos)[0]

    def aplicar_con_traza(
        self, candidatos: list[Candidato]
    ) -> tuple[list[Candidato], Traza]:
        traza = Traza()
        actual = list(candidatos)
        for nombre, etapa in self._etapas:
            entraron = len(actual)
            actual = etapa(actual)
            traza.registrar(nombre, entraron, len(actual))
        return actual, traza

    def __len__(self) -> int:
        return len(self._etapas)

    def __str__(self) -> str:
        if not self._etapas:
            return "identidad"
        return " . ".join(reversed(self.nombres))

"""Reduccion: alfa, beta y eta.

Alfa (3.2): renombrar la variable ligada. λx.x y λy.y son el mismo termino.
Beta (3.3): (λx. M) N  →  M[x := N]. Es "aplicar la funcion".
Eta  (3.4): λx. (f x)  →  f, si x no aparece libre en f. Envolver una funcion
            para solo pasarle el argumento no agrega nada.

El evaluador usa orden normal: reduce siempre el redex de mas a la izquierda y
mas afuera. Es mas lento que llamada por valor, pero tiene una propiedad que
aqui importa: si el termino tiene forma normal, el orden normal la encuentra.
Con llamada por valor hay terminos que se cuelgan aunque la respuesta exista.

Seguridad: esto no usa eval ni exec. Es un arbol propio y un recorrido. Y todo
corta en `max_pasos`, porque hay terminos que no tienen forma normal y se
reducen para siempre. El clasico es

    Ω = (λx. x x) (λx. x x)

que en un paso beta se reduce a si mismo. Sin el corte, un termino asi tumba el
proceso, y este servicio esta expuesto a lo que alguien escriba en el
laboratorio del CRM.
"""

from __future__ import annotations

from dataclasses import dataclass

from ceats_intel.domain.lambdacalc.terminos import Abs, App, Termino, Var, nombre_fresco


class LimiteReduccionError(RuntimeError):
    """El termino no llego a forma normal dentro del limite de pasos."""


@dataclass(frozen=True)
class Paso:
    """Un paso de reduccion, para poder mostrar la secuencia en el CRM."""

    regla: str  # "alfa", "beta" o "eta"
    antes: str
    despues: str

    def __str__(self) -> str:
        return f"{self.regla:>5}: {self.antes}  ->  {self.despues}"


class Evaluador:
    def __init__(self, max_pasos: int = 10_000) -> None:
        if max_pasos < 1:
            raise ValueError("max_pasos debe ser positivo")
        self._max_pasos = max_pasos

    # ---------------------------------------------------------------- alfa

    def alfa_convertir(self, termino: Abs, nuevo: str | None = None) -> Abs:
        """Renombra la variable ligada. El termino sigue significando lo mismo."""
        if nuevo is None:
            nuevo = nombre_fresco(termino.parametro, termino.variables_libres())
        if nuevo in termino.cuerpo.variables_libres() - {termino.parametro}:
            raise ValueError(f"Renombrar a {nuevo!r} capturaria una variable libre")
        return Abs(nuevo, termino.cuerpo.sustituir(termino.parametro, Var(nuevo)))

    # ---------------------------------------------------------------- beta

    def _reducir_una_vez(self, t: Termino) -> tuple[Termino, str] | None:
        """Un solo paso, orden normal. None si ya no hay nada que reducir."""
        # El redex de mas afuera y mas a la izquierda va primero.
        if isinstance(t, App):
            if isinstance(t.funcion, Abs):
                return t.funcion.cuerpo.sustituir(t.funcion.parametro, t.argumento), "beta"
            reducida = self._reducir_una_vez(t.funcion)
            if reducida is not None:
                return App(reducida[0], t.argumento), reducida[1]
            reducido = self._reducir_una_vez(t.argumento)
            if reducido is not None:
                return App(t.funcion, reducido[0]), reducido[1]
            return None

        if isinstance(t, Abs):
            # Eta antes de meterse al cuerpo: λx. (f x) con x no libre en f.
            if isinstance(t.cuerpo, App):
                cuerpo = t.cuerpo
                if (
                    isinstance(cuerpo.argumento, Var)
                    and cuerpo.argumento.nombre == t.parametro
                    and t.parametro not in cuerpo.funcion.variables_libres()
                ):
                    return cuerpo.funcion, "eta"
            dentro = self._reducir_una_vez(t.cuerpo)
            if dentro is not None:
                return Abs(t.parametro, dentro[0]), dentro[1]
            return None

        return None

    def beta_reducir(self, t: Termino) -> Termino:
        """Un paso beta (o eta). Si no hay nada que reducir, devuelve lo mismo."""
        resultado = self._reducir_una_vez(t)
        return t if resultado is None else resultado[0]

    def eta_reducir(self, t: Termino) -> Termino:
        """Aplica eta en la raiz si se puede."""
        if isinstance(t, Abs) and isinstance(t.cuerpo, App):
            cuerpo = t.cuerpo
            if (
                isinstance(cuerpo.argumento, Var)
                and cuerpo.argumento.nombre == t.parametro
                and t.parametro not in cuerpo.funcion.variables_libres()
            ):
                return cuerpo.funcion
        return t

    # ------------------------------------------------------- forma normal

    def forma_normal(self, t: Termino) -> Termino:
        return self.reducir_con_pasos(t)[0]

    def reducir_con_pasos(self, t: Termino) -> tuple[Termino, list[Paso]]:
        """La forma normal y el camino completo, paso por paso.

        Los pasos son lo que el laboratorio del CRM dibuja en pantalla.
        """
        pasos: list[Paso] = []
        actual = t
        for _ in range(self._max_pasos):
            siguiente = self._reducir_una_vez(actual)
            if siguiente is None:
                return actual, pasos
            termino, regla = siguiente
            pasos.append(Paso(regla, str(actual), str(termino)))
            actual = termino
        raise LimiteReduccionError(
            f"No llego a forma normal en {self._max_pasos} pasos. "
            f"Quedo en: {actual}. Puede que no tenga forma normal."
        )

    def equivalentes(self, a: Termino, b: Termino) -> bool:
        """Si los dos llegan a la misma forma normal, valen lo mismo."""
        try:
            return self.forma_normal(a) == self.forma_normal(b)
        except LimiteReduccionError:
            return False

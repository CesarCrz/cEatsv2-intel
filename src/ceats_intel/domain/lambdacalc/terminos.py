"""El arbol de sintaxis del calculo lambda.

    M ::= x  |  (λx. M)  |  (M N)

Tres formas nada mas: variable, abstraccion y aplicacion. Con eso se puede
expresar cualquier cosa computable, que es el punto de Church.

Todo aqui es inmutable. Sustituir no modifica el termino, devuelve uno nuevo.
No es capricho: la reduccion beta compara el antes y el despues para saber si
ya llego a forma normal, y si los terminos se mutaran en su lugar esa
comparacion no significaria nada.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class Termino(ABC):
    __slots__ = ()

    @abstractmethod
    def variables_libres(self) -> frozenset[str]:
        """Las variables que no estan ligadas por ningun lambda de adentro."""

    @abstractmethod
    def sustituir(self, variable: str, por: Termino) -> Termino:
        """M[variable := por], evitando captura."""

    @abstractmethod
    def __str__(self) -> str: ...

    @abstractmethod
    def _canonico(self, ligadas: dict[str, int], profundidad: int) -> str:
        """Forma canonica con indices de De Bruijn."""

    def canonico(self) -> str:
        """El termino escrito sin nombres de variables ligadas.

        En vez del nombre, cada variable ligada se escribe como la distancia al
        lambda que la liga: en \\x. x, la x es #0; en \\x. \\y. x, la x es #1.
        Las libres conservan su nombre, porque esas si importan.

        Sirve para comparar: dos terminos alfa-equivalentes tienen la misma
        forma canonica. Sin esto, \\x. x y \\y. y saldrian distintos por el
        puro nombre, que es justo lo que la conversion alfa dice que da igual.
        """
        return self._canonico({}, 0)

    def __eq__(self, otro: object) -> bool:
        if not isinstance(otro, Termino):
            return NotImplemented
        # Igualdad hasta alfa. Es la que corresponde: el nombre de una variable
        # ligada no es parte del significado del termino.
        return self.canonico() == otro.canonico()

    def __hash__(self) -> int:
        return hash(self.canonico())

    def __repr__(self) -> str:
        return f"{type(self).__name__}<{self}>"


class Var(Termino):
    """Una variable: x, y, f."""

    __slots__ = ("nombre",)

    def __init__(self, nombre: str) -> None:
        if not nombre or not nombre.isidentifier():
            raise ValueError(f"Nombre de variable invalido: {nombre!r}")
        self.nombre = nombre

    def variables_libres(self) -> frozenset[str]:
        return frozenset({self.nombre})

    def sustituir(self, variable: str, por: Termino) -> Termino:
        return por if self.nombre == variable else self

    def _canonico(self, ligadas: dict[str, int], profundidad: int) -> str:
        nivel = ligadas.get(self.nombre)
        if nivel is None:
            return self.nombre
        return f"#{profundidad - nivel - 1}"

    def __str__(self) -> str:
        return self.nombre


class Abs(Termino):
    """Una abstraccion: λparametro. cuerpo."""

    __slots__ = ("parametro", "cuerpo")

    def __init__(self, parametro: str, cuerpo: Termino) -> None:
        if not parametro or not parametro.isidentifier():
            raise ValueError(f"Parametro invalido: {parametro!r}")
        self.parametro = parametro
        self.cuerpo = cuerpo

    def variables_libres(self) -> frozenset[str]:
        return self.cuerpo.variables_libres() - {self.parametro}

    def sustituir(self, variable: str, por: Termino) -> Termino:
        # El parametro tapa a la variable: en λx. x, la x de adentro no es la
        # misma x de afuera y no se toca.
        if self.parametro == variable:
            return self

        # Captura de variable. Si `por` trae libre una variable que aqui esta
        # ligada, al meterla quedaria atrapada por este lambda y cambiaria de
        # significado. Ejemplo: (λx. y)[y := x] NO es λx. x. Antes de sustituir
        # hay que renombrar el parametro, y eso es la conversion alfa.
        if self.parametro in por.variables_libres():
            usados = por.variables_libres() | self.cuerpo.variables_libres() | {self.parametro}
            fresco = nombre_fresco(self.parametro, usados)
            renombrado = Abs(fresco, self.cuerpo.sustituir(self.parametro, Var(fresco)))
            return Abs(fresco, renombrado.cuerpo.sustituir(variable, por))

        return Abs(self.parametro, self.cuerpo.sustituir(variable, por))

    def _canonico(self, ligadas: dict[str, int], profundidad: int) -> str:
        dentro = {**ligadas, self.parametro: profundidad}
        return f"(\\. {self.cuerpo._canonico(dentro, profundidad + 1)})"

    def __str__(self) -> str:
        return f"(\\{self.parametro}. {self.cuerpo})"


class App(Termino):
    """Una aplicacion: (funcion argumento)."""

    __slots__ = ("funcion", "argumento")

    def __init__(self, funcion: Termino, argumento: Termino) -> None:
        self.funcion = funcion
        self.argumento = argumento

    def variables_libres(self) -> frozenset[str]:
        return self.funcion.variables_libres() | self.argumento.variables_libres()

    def sustituir(self, variable: str, por: Termino) -> Termino:
        return App(
            self.funcion.sustituir(variable, por),
            self.argumento.sustituir(variable, por),
        )

    def _canonico(self, ligadas: dict[str, int], profundidad: int) -> str:
        izq = self.funcion._canonico(ligadas, profundidad)
        der = self.argumento._canonico(ligadas, profundidad)
        return f"({izq} {der})"

    def __str__(self) -> str:
        return f"({self.funcion} {self.argumento})"


def nombre_fresco(base: str, usados: frozenset[str] | set[str]) -> str:
    """Un nombre que no choque con nada. x, x1, x2, ..."""
    raiz = base.rstrip("0123456789") or "x"
    if raiz not in usados:
        return raiz
    i = 1
    while f"{raiz}{i}" in usados:
        i += 1
    return f"{raiz}{i}"

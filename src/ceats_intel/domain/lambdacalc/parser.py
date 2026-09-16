"""Lector de terminos lambda escritos como texto.

Sintaxis que acepta:

    x                variable
    \\x. M            abstraccion (tambien con λ)
    \\x y. M          azucar para \\x. \\y. M
    (M N)            aplicacion, que asocia a la izquierda: M N P = ((M N) P)

Descenso recursivo, sin dependencias. Escribirlo a mano es mas corto que traer
una libreria de parsing, y de paso el termino nunca pasa por eval.
"""

from __future__ import annotations

from ceats_intel.domain.lambdacalc.terminos import Abs, App, Termino, Var

_SIMBOLOS_LAMBDA = ("\\", "λ")


class ErrorDeSintaxis(ValueError):
    pass


def _tokenizar(fuente: str) -> list[str]:
    tokens: list[str] = []
    i = 0
    while i < len(fuente):
        c = fuente[i]
        if c.isspace():
            i += 1
        elif c in "().":
            tokens.append(c)
            i += 1
        elif c in _SIMBOLOS_LAMBDA:
            tokens.append("\\")
            i += 1
        elif c.isalpha() or c == "_":
            j = i
            while j < len(fuente) and (fuente[j].isalnum() or fuente[j] == "_"):
                j += 1
            tokens.append(fuente[i:j])
            i = j
        else:
            raise ErrorDeSintaxis(f"Caracter inesperado {c!r} en la posicion {i}")
    return tokens


class Parser:
    def __init__(self, fuente: str) -> None:
        if len(fuente) > 2000:
            # Tope de tamano. El laboratorio esta expuesto y no hay razon para
            # aceptar un termino de un megabyte.
            raise ErrorDeSintaxis("El termino es demasiado largo")
        self._tokens = _tokenizar(fuente)
        self._pos = 0

    @classmethod
    def parsear(cls, fuente: str) -> Termino:
        parser = cls(fuente)
        termino = parser._expresion()
        if parser._pos != len(parser._tokens):
            raise ErrorDeSintaxis(f"Sobra texto desde {parser._tokens[parser._pos]!r}")
        return termino

    # ------------------------------------------------------------- internos

    def _mirar(self) -> str | None:
        return self._tokens[self._pos] if self._pos < len(self._tokens) else None

    def _comer(self, esperado: str | None = None) -> str:
        token = self._mirar()
        if token is None:
            raise ErrorDeSintaxis("El termino se corta antes de tiempo")
        if esperado is not None and token != esperado:
            raise ErrorDeSintaxis(f"Esperaba {esperado!r}, llego {token!r}")
        self._pos += 1
        return token

    def _expresion(self) -> Termino:
        if self._mirar() == "\\":
            return self._abstraccion()
        return self._aplicacion()

    def _abstraccion(self) -> Termino:
        self._comer("\\")
        parametros: list[str] = []
        while True:
            token = self._mirar()
            if token is None:
                raise ErrorDeSintaxis("Falta el punto de la abstraccion")
            if token == ".":
                break
            if not token.isidentifier():
                raise ErrorDeSintaxis(f"Parametro invalido: {token!r}")
            parametros.append(self._comer())
        if not parametros:
            raise ErrorDeSintaxis("La abstraccion necesita al menos un parametro")
        self._comer(".")
        cuerpo = self._expresion()
        for parametro in reversed(parametros):
            cuerpo = Abs(parametro, cuerpo)
        return cuerpo

    def _aplicacion(self) -> Termino:
        termino = self._atomo()
        while True:
            siguiente = self._mirar()
            if siguiente is None or siguiente in (")", "."):
                break
            # Una abstraccion al final se come el resto: \x. a b  =  \x. (a b)
            if siguiente == "\\":
                return App(termino, self._abstraccion())
            termino = App(termino, self._atomo())
        return termino

    def _atomo(self) -> Termino:
        token = self._mirar()
        if token is None:
            raise ErrorDeSintaxis("Falta un termino")
        if token == "(":
            self._comer("(")
            dentro = self._expresion()
            self._comer(")")
            return dentro
        if token == "\\":
            return self._abstraccion()
        if token in (")", "."):
            raise ErrorDeSintaxis(f"No esperaba {token!r}")
        return Var(self._comer())


def parsear(fuente: str) -> Termino:
    return Parser.parsear(fuente)


# Los de siempre, para las pruebas y para los botones del laboratorio.
COMBINADORES: dict[str, str] = {
    "I": r"\x. x",
    "K": r"\x y. x",
    "S": r"\x y z. x z (y z)",
    "omega": r"\x. x x",
    "Omega": r"(\x. x x) (\x. x x)",
    "cero": r"\f x. x",
    "uno": r"\f x. f x",
    "dos": r"\f x. f (f x)",
    "tres": r"\f x. f (f (f x))",
    "sucesor": r"\n f x. f (n f x)",
    "suma": r"\m n f x. m f (n f x)",
    "verdadero": r"\x y. x",
    "falso": r"\x y. y",
}


def church(n: int) -> Termino:
    """El numeral de Church de n: aplica f sobre x, n veces."""
    if n < 0:
        raise ValueError("Los numerales de Church son de naturales")
    cuerpo: Termino = Var("x")
    for _ in range(n):
        cuerpo = App(Var("f"), cuerpo)
    return Abs("f", Abs("x", cuerpo))

"""Dinero.

Guardo centavos enteros, no pesos flotantes. La razon es la de siempre:
`0.1 + 0.2` en float da `0.30000000000000004`, y sumando lineas de un pedido
ese error se acumula hasta que el total del reporte no cuadra con el de la app.

cEats guarda los precios en pesos con decimales, asi que la conversion se hace
al construir, con redondeo bancario para no sesgar los medios centavos siempre
hacia arriba.
"""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal


class Dinero:
    __slots__ = ("_centavos", "_moneda")

    def __init__(self, centavos: int, moneda: str = "MXN") -> None:
        if not isinstance(centavos, int) or isinstance(centavos, bool):
            raise TypeError("Dinero espera centavos como int")
        if centavos < 0:
            raise ValueError("No manejo montos negativos en este servicio")
        self._centavos = centavos
        self._moneda = moneda.upper()

    @classmethod
    def cero(cls, moneda: str = "MXN") -> Dinero:
        return cls(0, moneda)

    @classmethod
    def desde_pesos(cls, pesos: float | str | Decimal, moneda: str = "MXN") -> Dinero:
        exacto = Decimal(str(pesos)) * 100
        return cls(int(exacto.quantize(Decimal("1"), rounding=ROUND_HALF_EVEN)), moneda)

    @property
    def centavos(self) -> int:
        return self._centavos

    @property
    def moneda(self) -> str:
        return self._moneda

    def a_pesos(self) -> Decimal:
        return Decimal(self._centavos) / 100

    def mas(self, otro: Dinero) -> Dinero:
        self._verificar_moneda(otro)
        return Dinero(self._centavos + otro._centavos, self._moneda)

    def menos(self, otro: Dinero) -> Dinero:
        self._verificar_moneda(otro)
        return Dinero(self._centavos - otro._centavos, self._moneda)

    def por(self, factor: int) -> Dinero:
        """Multiplica por una cantidad entera de unidades.

        A proposito no acepta float: multiplicar dinero por un decimal es
        calcular un porcentaje, y eso necesita decidir como se redondea. Cuando
        haga falta, va en un metodo aparte que lo diga.
        """
        if not isinstance(factor, int) or isinstance(factor, bool):
            raise TypeError("por() espera un entero de unidades")
        if factor < 0:
            raise ValueError("El factor no puede ser negativo")
        return Dinero(self._centavos * factor, self._moneda)

    def _verificar_moneda(self, otro: Dinero) -> None:
        if self._moneda != otro._moneda:
            raise ValueError(f"No puedo operar {self._moneda} con {otro._moneda}")

    def __eq__(self, otro: object) -> bool:
        if not isinstance(otro, Dinero):
            return NotImplemented
        return self._centavos == otro._centavos and self._moneda == otro._moneda

    def __lt__(self, otro: Dinero) -> bool:
        self._verificar_moneda(otro)
        return self._centavos < otro._centavos

    def __le__(self, otro: Dinero) -> bool:
        self._verificar_moneda(otro)
        return self._centavos <= otro._centavos

    def __hash__(self) -> int:
        return hash((self._centavos, self._moneda))

    def __str__(self) -> str:
        return f"${self.a_pesos():,.2f} {self._moneda}"

    def __repr__(self) -> str:
        return f"Dinero({self._centavos}, {self._moneda!r})"

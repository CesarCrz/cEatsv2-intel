"""Ventana de tiempo sobre la que se calcula todo.

El detalle importante esta en `ultimos_dias`: la ventana se corta a medianoche,
no al instante en que se pide. Si no, el checkout que consulta a las 14:03 y el
laboratorio del CRM que consulta a las 14:07 estarian mirando conjuntos
distintos de pedidos, y basta que entre uno nuevo en medio para que dos
candidatos empatados se inviertan. Con el corte al dia, todo lo que se calcule
la misma fecha usa exactamente los mismos pedidos.

A medianoche cambia, y eso esta bien: es predecible y se puede explicar.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta


class VentanaTemporal:
    __slots__ = ("_desde", "_hasta")

    def __init__(self, desde: datetime, hasta: datetime) -> None:
        if desde.tzinfo is None or hasta.tzinfo is None:
            raise ValueError("Las fechas de la ventana deben traer zona horaria")
        if desde >= hasta:
            raise ValueError(f"Ventana invertida: {desde.isoformat()} >= {hasta.isoformat()}")
        self._desde = desde
        self._hasta = hasta

    @classmethod
    def ultimos_dias(cls, dias: int, hoy: date | None = None) -> VentanaTemporal:
        """Ventana de `dias` completos que termina hoy a las 00:00.

        `hoy` se puede inyectar para que las pruebas no dependan del reloj.
        """
        if dias < 1:
            raise ValueError("La ventana necesita al menos un dia")
        fin = hoy or datetime.now(UTC).date()
        inicio = fin - timedelta(days=dias)
        return cls(
            datetime.combine(inicio, time.min, tzinfo=UTC),
            datetime.combine(fin, time.min, tzinfo=UTC),
        )

    @property
    def desde(self) -> datetime:
        return self._desde

    @property
    def hasta(self) -> datetime:
        return self._hasta

    @property
    def dias(self) -> int:
        return (self._hasta - self._desde).days

    def contiene(self, momento: datetime) -> bool:
        # Intervalo cerrado por la izquierda y abierto por la derecha, para que
        # dos ventanas consecutivas no cuenten dos veces el mismo pedido.
        return self._desde <= momento < self._hasta

    def clave(self) -> str:
        """Texto estable de la ventana. Entra en la huella de la decision."""
        return f"{self._desde.date().isoformat()}..{self._hasta.date().isoformat()}"

    def __eq__(self, otro: object) -> bool:
        if not isinstance(otro, VentanaTemporal):
            return NotImplemented
        return self._desde == otro._desde and self._hasta == otro._hasta

    def __hash__(self) -> int:
        return hash((self._desde, self._hasta))

    def __repr__(self) -> str:
        return f"VentanaTemporal({self.clave()})"

"""Pronostico de demanda. La segunda jerarquia polimorfica de la Unidad 2.

Tres modelos que responden lo mismo con supuestos distintos. El caso de uso
elige uno por configuracion y no sabe cual le toco.

No uso ninguna libreria de series de tiempo a proposito. Con 90 dias de una
sucursal, un ARIMA no le gana a una media movil bien puesta, y ademas tengo que
poder explicar de donde sale cada numero.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence


class ModeloPronostico(ABC):
    def __init__(self, nombre: str) -> None:
        self._nombre = nombre
        self._entrenado = False

    @property
    def nombre(self) -> str:
        return self._nombre

    @property
    def entrenado(self) -> bool:
        return self._entrenado

    @abstractmethod
    def _ajustar(self, serie: Sequence[float]) -> None:
        """Lo propio de cada modelo."""

    @abstractmethod
    def _predecir_paso(self, indice: int) -> float:
        """Valor para el paso `indice` contado desde el final de la serie."""

    def entrenar(self, serie: Sequence[float]) -> ModeloPronostico:
        """Metodo plantilla: valida, delega y marca. Devuelve self para encadenar."""
        if len(serie) < 2:
            raise ValueError(f"{self._nombre} necesita al menos dos observaciones")
        if any(v < 0 for v in serie):
            raise ValueError("La serie no puede traer valores negativos")
        self._ajustar(serie)
        self._entrenado = True
        return self

    def predecir(self, pasos: int = 1) -> list[float]:
        if not self._entrenado:
            raise RuntimeError(f"{self._nombre} no ha sido entrenado")
        if pasos < 1:
            raise ValueError("Hay que predecir al menos un paso")
        # Nunca devuelvo negativos: un pronostico de -3 pedidos no significa nada.
        return [max(0.0, round(self._predecir_paso(i), 4)) for i in range(pasos)]

    @staticmethod
    def error_absoluto_medio(real: Sequence[float], predicho: Sequence[float]) -> float:
        """MAE. En unidades de pedidos, que es lo que se puede explicar."""
        if len(real) != len(predicho):
            raise ValueError("Las series deben medir lo mismo")
        if not real:
            raise ValueError("No hay nada que comparar")
        return round(sum(abs(r - p) for r, p in zip(real, predicho, strict=True)) / len(real), 4)

    def __str__(self) -> str:
        return f"{type(self).__name__}({self._nombre})"


class MediaMovilModelo(ModeloPronostico):
    """El promedio de las ultimas N observaciones. Plano hacia adelante."""

    def __init__(self, ventana: int = 7) -> None:
        super().__init__(f"media movil {ventana}")
        if ventana < 1:
            raise ValueError("La ventana debe ser positiva")
        self._ventana = ventana
        self._valor = 0.0

    def _ajustar(self, serie: Sequence[float]) -> None:
        cola = serie[-self._ventana :]
        self._valor = sum(cola) / len(cola)

    def _predecir_paso(self, indice: int) -> float:
        return self._valor


class EstacionalSemanalModelo(ModeloPronostico):
    """Promedio por posicion del ciclo. Para series con ritmo semanal o diario.

    Le paso `periodo=7` para dias de la semana y `periodo=24` para horas del
    dia. Es el que sirve de verdad en un restaurante: el viernes no se parece
    al martes, y promediarlos juntos borra justo lo que importa.
    """

    def __init__(self, periodo: int = 7) -> None:
        super().__init__(f"estacional {periodo}")
        if periodo < 2:
            raise ValueError("El periodo debe ser al menos 2")
        self._periodo = periodo
        self._perfil: list[float] = []
        self._largo = 0

    def _ajustar(self, serie: Sequence[float]) -> None:
        sumas = [0.0] * self._periodo
        conteos = [0] * self._periodo
        for i, valor in enumerate(serie):
            posicion = i % self._periodo
            sumas[posicion] += valor
            conteos[posicion] += 1
        promedio_global = sum(serie) / len(serie)
        # Las posiciones sin datos caen al promedio general en vez de a cero.
        self._perfil = [
            sumas[p] / conteos[p] if conteos[p] else promedio_global for p in range(self._periodo)
        ]
        self._largo = len(serie)

    def _predecir_paso(self, indice: int) -> float:
        return self._perfil[(self._largo + indice) % self._periodo]

    @property
    def perfil(self) -> tuple[float, ...]:
        return tuple(self._perfil)


class RegresionLinealModelo(ModeloPronostico):
    """Minimos cuadrados sobre el indice. Captura la tendencia, nada mas.

    Sirve para responder "vamos subiendo o bajando", que es distinto de
    "cuantos pedidos entran el viernes".
    """

    def __init__(self) -> None:
        super().__init__("regresion lineal")
        self._pendiente = 0.0
        self._intercepto = 0.0
        self._largo = 0

    def _ajustar(self, serie: Sequence[float]) -> None:
        n = len(serie)
        xs = range(n)
        media_x = (n - 1) / 2
        media_y = sum(serie) / n
        numerador = sum((x - media_x) * (y - media_y) for x, y in zip(xs, serie, strict=True))
        denominador = sum((x - media_x) ** 2 for x in xs)
        self._pendiente = numerador / denominador if denominador else 0.0
        self._intercepto = media_y - self._pendiente * media_x
        self._largo = n

    def _predecir_paso(self, indice: int) -> float:
        return self._intercepto + self._pendiente * (self._largo + indice)

    @property
    def pendiente(self) -> float:
        return round(self._pendiente, 6)

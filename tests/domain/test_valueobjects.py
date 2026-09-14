from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from ceats_intel.domain.valueobjects import (
    Dinero,
    ProductoId,
    SucursalId,
    VentanaTemporal,
)

UUID_A = "3f2504e0-4f89-41d3-9a0c-0305e82c3301"
UUID_B = "3f2504e0-4f89-41d3-9a0c-0305e82c3302"


class TestIdentificadores:
    def test_normaliza_mayusculas_y_espacios(self):
        assert ProductoId(f"  {UUID_A.upper()}  ").valor == UUID_A

    def test_rechaza_texto_que_no_es_uuid(self):
        with pytest.raises(ValueError):
            ProductoId("yakimeshi-crispy")

    def test_rechaza_tipo_equivocado(self):
        with pytest.raises(TypeError):
            ProductoId(123)  # type: ignore[arg-type]

    def test_dos_ids_iguales_valen_lo_mismo(self):
        assert ProductoId(UUID_A) == ProductoId(UUID_A)
        assert len({ProductoId(UUID_A), ProductoId(UUID_A)}) == 1

    def test_tipos_distintos_no_se_confunden(self):
        # Este es el punto de tener tipos separados: mismo UUID, distinto tipo,
        # no son iguales ni colisionan en un set.
        assert ProductoId(UUID_A) != SucursalId(UUID_A)
        assert len({ProductoId(UUID_A), SucursalId(UUID_A)}) == 2

    def test_se_pueden_ordenar(self):
        assert sorted([ProductoId(UUID_B), ProductoId(UUID_A)]) == [
            ProductoId(UUID_A),
            ProductoId(UUID_B),
        ]


class TestDinero:
    def test_convierte_pesos_a_centavos(self):
        assert Dinero.desde_pesos(89.50).centavos == 8950

    def test_no_arrastra_error_de_flotante(self):
        # Con floats, 0.1 + 0.2 no da 0.3. Con centavos enteros, si.
        diez = Dinero.desde_pesos(0.10)
        veinte = Dinero.desde_pesos(0.20)
        assert diez.mas(veinte) == Dinero.desde_pesos(0.30)

    def test_suma_de_muchas_lineas_cuadra(self):
        total = Dinero.cero()
        for _ in range(1000):
            total = total.mas(Dinero.desde_pesos(19.99))
        assert total.a_pesos() == Decimal("19990.00")

    def test_multiplica_por_unidades_enteras(self):
        assert Dinero.desde_pesos(45).por(3) == Dinero.desde_pesos(135)

    def test_rechaza_multiplicar_por_decimal(self):
        with pytest.raises(TypeError):
            Dinero.desde_pesos(45).por(1.5)  # type: ignore[arg-type]

    def test_rechaza_monedas_distintas(self):
        with pytest.raises(ValueError):
            Dinero(100, "MXN").mas(Dinero(100, "USD"))

    def test_rechaza_negativos(self):
        with pytest.raises(ValueError):
            Dinero(-1)


class TestVentanaTemporal:
    def test_corta_a_medianoche_sin_importar_la_hora(self):
        # El punto de todo: dos consultas el mismo dia dan la misma ventana.
        hoy = date(2026, 9, 14)
        a = VentanaTemporal.ultimos_dias(90, hoy=hoy)
        b = VentanaTemporal.ultimos_dias(90, hoy=hoy)
        assert a == b
        assert a.desde.hour == 0 and a.hasta.hour == 0
        assert a.dias == 90

    def test_clave_estable(self):
        v = VentanaTemporal.ultimos_dias(90, hoy=date(2026, 9, 14))
        assert v.clave() == "2026-06-16..2026-09-14"

    def test_intervalo_abierto_por_la_derecha(self):
        v = VentanaTemporal.ultimos_dias(7, hoy=date(2026, 9, 14))
        assert v.contiene(v.desde)
        assert not v.contiene(v.hasta)
        assert v.contiene(v.hasta - timedelta(seconds=1))

    def test_rechaza_fechas_sin_zona(self):
        with pytest.raises(ValueError):
            VentanaTemporal(datetime(2026, 1, 1), datetime(2026, 2, 1, tzinfo=UTC))

    def test_rechaza_ventana_invertida(self):
        with pytest.raises(ValueError):
            VentanaTemporal(
                datetime(2026, 2, 1, tzinfo=UTC),
                datetime(2026, 1, 1, tzinfo=UTC),
            )

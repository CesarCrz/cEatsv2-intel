from datetime import UTC, date, datetime

import pytest
from conftest import pedido, pid, sid

from ceats_intel.domain.entidades import Canasta, HistorialVentas, LineaPedido, Pedido, Producto
from ceats_intel.domain.valueobjects import Dinero, VentanaTemporal


class TestLineaPedido:
    def test_subtotal(self):
        linea = LineaPedido(pid(1), 3, Dinero.desde_pesos(45))
        assert linea.subtotal() == Dinero.desde_pesos(135)

    def test_rechaza_cantidad_cero(self):
        with pytest.raises(ValueError):
            LineaPedido(pid(1), 0, Dinero.desde_pesos(45))

    def test_rechaza_cantidad_booleana(self):
        # True es int en Python. Sin el chequeo explicito pasaria como cantidad 1.
        with pytest.raises(TypeError):
            LineaPedido(pid(1), True, Dinero.desde_pesos(45))  # type: ignore[arg-type]


class TestPedido:
    def test_total_suma_las_lineas(self):
        p = Pedido(
            "p1",
            sid(),
            datetime(2026, 9, 1, 13, 0, tzinfo=UTC),
            [
                LineaPedido(pid(1), 2, Dinero.desde_pesos(89.50)),
                LineaPedido(pid(2), 1, Dinero.desde_pesos(35)),
            ],
        )
        assert p.total() == Dinero.desde_pesos(214)

    def test_no_se_pueden_agregar_lineas_desde_fuera(self):
        # El corazon del tema 1.6. `lineas` devuelve una tupla, no la lista
        # interna, asi que no hay forma de meterle mano al pedido por detras.
        p = pedido(1, [1, 2])
        with pytest.raises(AttributeError):
            p.lineas.append(LineaPedido(pid(9), 1, Dinero.desde_pesos(10)))  # type: ignore[attr-defined]
        assert len(p.lineas) == 2

    def test_mutar_la_lista_original_no_afecta_al_pedido(self):
        # La copia defensiva del constructor. Sin `tuple(lineas)`, este pedido
        # se quedaria con una referencia viva a `originales`.
        originales = [LineaPedido(pid(1), 1, Dinero.desde_pesos(50))]
        p = Pedido("p1", sid(), datetime(2026, 9, 1, tzinfo=UTC), originales)
        originales.append(LineaPedido(pid(2), 1, Dinero.desde_pesos(999)))
        assert len(p.lineas) == 1
        assert p.total() == Dinero.desde_pesos(50)

    def test_productos_ignora_cantidades(self):
        p = pedido(1, [1, 2], cantidad=5)
        assert p.productos() == frozenset({pid(1), pid(2)})

    def test_rechaza_pedido_vacio(self):
        with pytest.raises(ValueError):
            Pedido("p1", sid(), datetime(2026, 9, 1, tzinfo=UTC), [])

    def test_rechaza_fecha_sin_zona(self):
        with pytest.raises(ValueError):
            Pedido("p1", sid(), datetime(2026, 9, 1), [LineaPedido(pid(1), 1, Dinero.cero())])


class TestCanasta:
    def test_ordena_y_quita_repetidos(self):
        c = Canasta(sid(), [pid(3), pid(1), pid(3), pid(2)])
        assert c.productos == (pid(1), pid(2), pid(3))

    def test_la_clave_no_depende_del_orden_de_entrada(self):
        # Si la clave cambiara con el orden del JSON, la huella de la decision
        # cambiaria sin que cambie nada real y el laboratorio no coincidiria.
        a = Canasta(sid(), [pid(1), pid(2)])
        b = Canasta(sid(), [pid(2), pid(1)])
        assert a.clave() == b.clave()
        assert a == b


class TestProducto:
    def test_dos_productos_con_el_mismo_id_son_el_mismo(self):
        a = Producto(pid(1), "Yakimeshi Crispy", Dinero.desde_pesos(189))
        b = Producto(pid(1), "Yakimeshi", Dinero.desde_pesos(200))
        assert a == b

    def test_rechaza_nombre_vacio(self):
        with pytest.raises(ValueError):
            Producto(pid(1), "   ", Dinero.cero())


class TestHistorialVentas:
    @staticmethod
    def _historial(pedidos):
        return HistorialVentas(
            sid(),
            VentanaTemporal.ultimos_dias(90, hoy=date(2026, 9, 14)),
            pedidos,
        )

    def test_frecuencia_cuenta_pedidos_no_piezas(self):
        h = self._historial([pedido(1, [1], cantidad=7), pedido(2, [1], cantidad=1)])
        assert h.frecuencia(pid(1)) == 2
        assert h.unidades(pid(1)) == 8

    def test_veces_juntos_es_simetrico(self):
        h = self._historial([pedido(1, [1, 2]), pedido(2, [2, 1])])
        assert h.veces_juntos(pid(1), pid(2)) == 2
        assert h.veces_juntos(pid(2), pid(1)) == 2

    def test_un_producto_no_acompana_a_si_mismo(self):
        h = self._historial([pedido(1, [1])])
        assert h.veces_juntos(pid(1), pid(1)) == 0

    def test_soporte(self):
        h = self._historial([pedido(1, [1, 2]), pedido(2, [2]), pedido(3, [3])])
        assert h.soporte(pid(2)) == pytest.approx(2 / 3)

    def test_acompanantes_no_se_puede_modificar(self):
        h = self._historial([pedido(1, [1, 2])])
        acompana = h.acompanantes(pid(1))
        assert acompana[pid(2)] == 1
        with pytest.raises(TypeError):
            acompana[pid(9)] = 100  # type: ignore[index]

    def test_serie_por_hora(self):
        h = self._historial(
            [
                pedido(1, [1], cuando=datetime(2026, 9, 1, 13, 5, tzinfo=UTC)),
                pedido(2, [1], cuando=datetime(2026, 9, 2, 13, 40, tzinfo=UTC)),
                pedido(3, [1], cuando=datetime(2026, 9, 2, 20, 0, tzinfo=UTC)),
            ]
        )
        serie = h.serie_por_hora()
        assert serie[13] == 2
        assert serie[20] == 1
        assert sum(serie) == 3

    def test_historial_vacio_no_truena(self):
        h = self._historial([])
        assert h.vacio()
        assert h.soporte(pid(1)) == 0.0
        assert h.frecuencia(pid(1)) == 0
        assert h.serie_por_hora() == tuple([0] * 24)

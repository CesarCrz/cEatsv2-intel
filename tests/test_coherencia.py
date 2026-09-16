"""La prueba que sostiene la demo.

Si en el menu publico pido un Yakimeshi Crispy y me salen tres sugerencias, al
escoger ese mismo platillo en el laboratorio del CRM me tienen que salir las
mismas tres, en el mismo orden. Si eso no se cumple, la demo delante de la
maestra se cae y el proyecto pierde credibilidad.

La unica diferencia entre los dos caminos es `explicar`: el laboratorio lo pide
en true y recibe ademas el detalle. La lista de sugerencias tiene que ser
identica.

Si alguien alguna vez mete un `if` en el caso de uso que cambie el resultado
segun quien llame, estas pruebas se ponen rojas.
"""

from __future__ import annotations

import random

import pytest
from conftest import pid
from factories import MENU, canasta, catalogo, historial_del_refresco

from ceats_intel.application import (
    FabricaEstrategias,
    GenerarRecomendacionesUseCase,
    ModoUpsell,
    PeticionRecomendacion,
)

TODOS = [pid(n) for n, *_ in MENU]


@pytest.fixture
def caso():
    return GenerarRecomendacionesUseCase(FabricaEstrategias())


@pytest.fixture
def escenario():
    return historial_del_refresco(), catalogo()


def ejecutar(caso, escenario, carrito, *, explicar: bool, modo=ModoUpsell.AUTO, limite=3):
    hist, cat = escenario
    return caso.ejecutar(
        PeticionRecomendacion(canasta=carrito, modo=modo, limite=limite, explicar=explicar),
        historial=hist,
        catalogo=cat,
    )


class TestCoherencia:
    def test_checkout_y_laboratorio_dan_lo_mismo(self, caso, escenario):
        carrito = canasta(TODOS[1])
        checkout = ejecutar(caso, escenario, carrito, explicar=False)
        laboratorio = ejecutar(caso, escenario, carrito, explicar=True)

        assert checkout.ids() == laboratorio.ids()
        assert checkout.huella == laboratorio.huella
        assert [s.score for s in checkout.sugerencias] == [
            s.score for s in laboratorio.sugerencias
        ]

    @pytest.mark.parametrize("semilla", range(40))
    def test_doscientas_canastas_al_azar_coinciden(self, caso, escenario, semilla):
        """La red de seguridad. Canastas aleatorias, los dos caminos, mismo resultado.

        Son 40 semillas por 5 modos: 200 comparaciones. Corre en menos de un
        segundo y se da cuenta al instante si alguien separa los caminos.
        """
        azar = random.Random(semilla)
        cuantos = azar.randint(1, 3)
        carrito = canasta(*azar.sample(TODOS, cuantos))

        for modo in ModoUpsell:
            checkout = ejecutar(caso, escenario, carrito, explicar=False, modo=modo)
            laboratorio = ejecutar(caso, escenario, carrito, explicar=True, modo=modo)
            assert checkout.ids() == laboratorio.ids(), f"modo {modo}, canasta {carrito.clave()}"
            assert checkout.huella == laboratorio.huella

    def test_explicar_solo_agrega_informacion(self, caso, escenario):
        carrito = canasta(TODOS[1])
        checkout = ejecutar(caso, escenario, carrito, explicar=False)
        laboratorio = ejecutar(caso, escenario, carrito, explicar=True)

        assert checkout.traza == []
        assert checkout.descartados == []
        assert laboratorio.traza
        assert all(s.evidencia is None for s in checkout.sugerencias)


class TestHuella:
    def test_la_misma_entrada_da_la_misma_huella(self, caso, escenario):
        a = ejecutar(caso, escenario, canasta(TODOS[1]), explicar=False)
        b = ejecutar(caso, escenario, canasta(TODOS[1]), explicar=False)
        assert a.huella == b.huella

    def test_el_orden_de_la_canasta_no_cambia_la_huella(self, caso, escenario):
        # El JSON puede llegar en cualquier orden. La huella no se puede mover
        # por eso, porque nada real cambio.
        a = ejecutar(caso, escenario, canasta(TODOS[1], TODOS[2]), explicar=False)
        b = ejecutar(caso, escenario, canasta(TODOS[2], TODOS[1]), explicar=False)
        assert a.huella == b.huella
        assert a.ids() == b.ids()

    def test_cambiar_de_modo_cambia_la_huella(self, caso, escenario):
        auto = ejecutar(caso, escenario, canasta(TODOS[1]), explicar=False, modo=ModoUpsell.AUTO)
        pop = ejecutar(
            caso, escenario, canasta(TODOS[1]), explicar=False, modo=ModoUpsell.POPULARIDAD
        )
        assert auto.huella != pop.huella

    def test_cambiar_el_limite_cambia_la_huella(self, caso, escenario):
        tres = ejecutar(caso, escenario, canasta(TODOS[1]), explicar=False, limite=3)
        cuatro = ejecutar(caso, escenario, canasta(TODOS[1]), explicar=False, limite=4)
        assert tres.huella != cuatro.huella


class TestSalida:
    def test_nunca_devuelve_mas_del_limite(self, caso, escenario):
        salida = ejecutar(caso, escenario, canasta(TODOS[1]), explicar=False, limite=2)
        assert len(salida.sugerencias) <= 2

    def test_nunca_repite_lo_que_ya_trae_el_cliente(self, caso, escenario):
        carrito = canasta(TODOS[1], TODOS[2])
        salida = ejecutar(caso, escenario, carrito, explicar=False, limite=5)
        assert not (set(salida.ids()) & {str(p) for p in carrito})

    def test_no_repite_productos(self, caso, escenario):
        salida = ejecutar(caso, escenario, canasta(TODOS[1]), explicar=False, limite=5)
        assert len(salida.ids()) == len(set(salida.ids()))

    def test_la_franja_nunca_se_queda_vacia(self, caso, escenario):
        """Con canasta vacia y sin co-ocurrencia posible, la cascada responde igual."""
        _, cat = escenario
        from factories import historial

        salida = caso.ejecutar(
            PeticionRecomendacion(canasta=canasta(), modo=ModoUpsell.AUTO, limite=4),
            historial=historial([]),
            catalogo=cat,
        )
        assert salida.sugerencias
        # Sin un solo pedido, tuvo que bajar hasta el ultimo escalon.
        assert salida.nivel_alcanzado >= 4

"""Pruebas del calculo lambda. Unidad 3.

Si estas pruebas pasan, el intérprete hace lo que dice la teoria: alfa no
cambia el significado, beta aplica funciones y eta quita envoltorios inutiles.
"""

import pytest

from ceats_intel.domain.lambdacalc import (
    COMBINADORES,
    Abs,
    App,
    ErrorDeSintaxis,
    Evaluador,
    LimiteReduccionError,
    Var,
    church,
    parsear,
)


@pytest.fixture
def ev():
    return Evaluador(max_pasos=1000)


class TestParser:
    def test_variable(self):
        assert parsear("x") == Var("x")

    def test_abstraccion(self):
        assert parsear(r"\x. x") == Abs("x", Var("x"))

    def test_varios_parametros_es_azucar(self):
        # \x y. x  es lo mismo que  \x. \y. x
        assert parsear(r"\x y. x") == parsear(r"\x. \y. x")

    def test_aplicacion_asocia_a_la_izquierda(self):
        assert parsear("a b c") == App(App(Var("a"), Var("b")), Var("c"))

    def test_acepta_el_simbolo_lambda(self):
        assert parsear("λx. x") == parsear(r"\x. x")

    def test_rechaza_basura(self):
        with pytest.raises(ErrorDeSintaxis):
            parsear(r"\x. ")

    def test_rechaza_termino_gigante(self):
        with pytest.raises(ErrorDeSintaxis):
            parsear("x" * 2001)


class TestVariablesLibres:
    def test_el_parametro_liga(self):
        assert parsear(r"\x. x").variables_libres() == frozenset()

    def test_lo_de_afuera_queda_libre(self):
        assert parsear(r"\x. y").variables_libres() == frozenset({"y"})

    def test_en_aplicacion_se_unen(self):
        assert parsear("f x").variables_libres() == frozenset({"f", "x"})


class TestAlfa:
    def test_renombrar_no_cambia_el_significado(self, ev):
        identidad = parsear(r"\x. x")
        renombrada = ev.alfa_convertir(identidad, "y")
        assert str(renombrada) == r"(\y. y)"
        assert ev.equivalentes(identidad, renombrada)

    def test_no_deja_renombrar_si_captura(self, ev):
        # \x. y  renombrado a  \y. y  cambiaria el significado: la y libre
        # quedaria atrapada.
        with pytest.raises(ValueError):
            ev.alfa_convertir(parsear(r"\x. y"), "y")

    def test_la_sustitucion_renombra_sola_para_no_capturar(self):
        # (\x. y)[y := x] NO puede dar \x. x. La x que entra es libre y tiene
        # que seguir siendo libre, asi que el parametro se renombra.
        resultado = parsear(r"\x. y").sustituir("y", Var("x"))
        assert "x" in resultado.variables_libres()
        assert resultado != parsear(r"\x. x")


class TestBeta:
    def test_identidad(self, ev):
        assert ev.forma_normal(parsear(r"(\x. x) y")) == Var("y")

    def test_k_se_queda_con_el_primero(self, ev):
        assert ev.forma_normal(parsear(r"(\x y. x) a b")) == Var("a")

    def test_k_aplicado_a_dos_ignora_el_segundo(self, ev):
        # Vale incluso si el segundo argumento no termina. Eso es lo que da el
        # orden normal y lo que la llamada por valor no puede.
        assert ev.forma_normal(parsear(r"(\x y. x) a ((\x. x) b)")) == Var("a")

    def test_s_k_k_es_la_identidad(self, ev):
        s, k = COMBINADORES["S"], COMBINADORES["K"]
        skk = parsear(f"({s}) ({k}) ({k}) z")
        assert ev.forma_normal(skk) == Var("z")


class TestEta:
    def test_quita_el_envoltorio(self, ev):
        assert ev.eta_reducir(parsear(r"\x. f x")) == Var("f")

    def test_no_aplica_si_la_variable_es_libre_en_la_funcion(self, ev):
        # \x. x x  no se puede eta-reducir: la x aparece libre en la funcion.
        termino = parsear(r"\x. x x")
        assert ev.eta_reducir(termino) == termino


class TestNumeralesDeChurch:
    def test_representacion(self):
        assert church(0) == parsear(COMBINADORES["cero"])
        assert church(2) == parsear(COMBINADORES["dos"])

    def test_sucesor(self, ev):
        suc = COMBINADORES["sucesor"]
        assert ev.forma_normal(parsear(f"({suc}) ({COMBINADORES['dos']})")) == church(3)

    @pytest.mark.parametrize(("m", "n"), [(0, 0), (1, 2), (2, 3), (4, 5)])
    def test_suma(self, ev, m, n):
        suma = COMBINADORES["suma"]
        expresion = f"({suma}) ({church(m)}) ({church(n)})"
        assert ev.forma_normal(parsear(expresion)) == church(m + n)


class TestLimites:
    def test_omega_no_termina_y_corta(self, ev):
        # (\x. x x)(\x. x x) se reduce a si mismo, para siempre. Sin el corte,
        # esto cuelga el proceso, y el laboratorio del CRM acepta texto de
        # quien lo use.
        with pytest.raises(LimiteReduccionError):
            ev.forma_normal(parsear(COMBINADORES["Omega"]))

    def test_los_pasos_quedan_registrados(self, ev):
        _, pasos = ev.reducir_con_pasos(parsear(r"(\x y. x) a b"))
        assert [p.regla for p in pasos] == ["beta", "beta"]
        assert pasos[0].antes != pasos[0].despues

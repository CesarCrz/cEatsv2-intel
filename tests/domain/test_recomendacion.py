"""Pruebas de la Unidad 2: herencia, polimorfismo y el lift."""

import pytest
from factories import (
    EDAMAME,
    GYOZA,
    MOCHI,
    RAMEN,
    REFRESCO,
    TE,
    YAKIMESHI,
    canasta,
    catalogo,
    historial,
    historial_del_refresco,
)

from ceats_intel.domain.catalogo import TipoCategoria
from ceats_intel.domain.recomendacion import (
    AfinidadCategoriaStrategy,
    ContextoRecomendacion,
    CoOcurrenciaStrategy,
    DestacadosStrategy,
    EstrategiaRecomendacion,
    HibridaStrategy,
    NivelRespaldo,
    OrigenSugerencia,
    PopularidadStrategy,
    ReglasManualesStrategy,
    ReglaUpsell,
    confianza_suavizada,
)


def ctx(carrito, hist=None, cat=None, alfa=10.0):
    return ContextoRecomendacion(
        canasta=carrito,
        historial=hist or historial_del_refresco(),
        catalogo=cat or catalogo(),
        alfa=alfa,
    )


class TestLift:
    def test_el_lift_le_gana_al_conteo(self):
        """El problema del refresco, que es el motivo de todo esto.

        Contando a secas, el refresco acompaña al ramen 50 veces y la gyoza
        50 tambien, pero el refresco sale en casi todo. El lift lo separa.
        """
        h = historial_del_refresco()
        assert h.veces_juntos(RAMEN, REFRESCO) == 50
        assert h.veces_juntos(RAMEN, GYOZA) == 50

        lift_refresco, _ = confianza_suavizada(h, RAMEN, REFRESCO, alfa=10.0)
        lift_gyoza, _ = confianza_suavizada(h, RAMEN, GYOZA, alfa=10.0)

        # Mismo conteo, distinto lift: la gyoza si va con el ramen, el refresco
        # va con todo.
        assert lift_gyoza > lift_refresco
        assert lift_refresco < 1.3

    def test_lift_uno_es_indiferencia(self):
        # Dos productos independientes: B sale en la mitad de los pedidos,
        # lleve A o no. El lift tiene que rondar 1.
        h = historial([([RAMEN, GYOZA], 50), ([RAMEN], 50), ([GYOZA], 50), ([TE], 50)])
        lift, _ = confianza_suavizada(h, RAMEN, GYOZA, alfa=10.0)
        assert 0.85 < lift < 1.15

    def test_sin_evidencia_el_suavizado_devuelve_la_popularidad(self):
        # n(A) = 0: nunca se ha vendido el ancla. La formula colapsa a
        # soporte(B), y por lo tanto el lift da 1. Es la respuesta honesta.
        h = historial([([GYOZA], 20), ([TE], 10)])
        lift, ev = confianza_suavizada(h, MOCHI, GYOZA, alfa=10.0)
        assert ev.frecuencia_ancla == 0
        assert lift == pytest.approx(1.0, abs=1e-6)

    def test_el_suavizado_frena_los_pares_con_poca_evidencia(self):
        # Un solo pedido con los dos juntos no debe disparar el lift al cielo.
        h = historial([([RAMEN, MOCHI], 1), ([RAMEN], 3), ([GYOZA], 96)])
        con_suavizado, _ = confianza_suavizada(h, RAMEN, MOCHI, alfa=10.0)
        sin_suavizado, _ = confianza_suavizada(h, RAMEN, MOCHI, alfa=0.0)
        assert con_suavizado < sin_suavizado

    def test_mas_datos_acercan_el_suavizado_a_la_verdad(self):
        pocos = historial([([RAMEN, GYOZA], 3), ([RAMEN], 1), ([TE], 6)])
        muchos = historial([([RAMEN, GYOZA], 300), ([RAMEN], 100), ([TE], 600)])
        crudo_pocos, _ = confianza_suavizada(pocos, RAMEN, GYOZA, alfa=0.0)
        suave_pocos, _ = confianza_suavizada(pocos, RAMEN, GYOZA, alfa=10.0)
        crudo_muchos, _ = confianza_suavizada(muchos, RAMEN, GYOZA, alfa=0.0)
        suave_muchos, _ = confianza_suavizada(muchos, RAMEN, GYOZA, alfa=10.0)
        assert abs(suave_muchos - crudo_muchos) < abs(suave_pocos - crudo_pocos)


class TestPolimorfismo:
    """El punto de la Unidad 2: el mismo codigo, distintas estrategias."""

    @pytest.mark.parametrize(
        "estrategia",
        [
            CoOcurrenciaStrategy(),
            PopularidadStrategy(),
            AfinidadCategoriaStrategy(),
            DestacadosStrategy(),
            ReglasManualesStrategy([ReglaUpsell("r1", RAMEN, GYOZA)]),
            HibridaStrategy([CoOcurrenciaStrategy(), PopularidadStrategy()]),
        ],
    )
    def test_todas_responden_a_la_misma_llamada(self, estrategia):
        # Ni un isinstance, ni un if por tipo. Esto es lo que se enseña en la
        # demo del comparador del laboratorio.
        assert isinstance(estrategia, EstrategiaRecomendacion)
        resultado = estrategia.puntuar(ctx(canasta(RAMEN)), limite=3)
        assert len(resultado) <= 3
        assert all(isinstance(c.origen, OrigenSugerencia) for c in resultado)
        assert all(not c.descartado for c in resultado)

    @pytest.mark.parametrize(
        "estrategia",
        [CoOcurrenciaStrategy(), PopularidadStrategy(), AfinidadCategoriaStrategy()],
    )
    def test_una_hoja_etiqueta_todo_con_su_propio_origen(self, estrategia):
        # Las compuestas no: una hibrida devuelve candidatos con el origen de
        # la hija que los propuso, y asi tiene que ser para poder decir en el
        # CRM cual vino de una regla del restaurante y cual del lift.
        resultado = estrategia.puntuar(ctx(canasta(RAMEN)), limite=3)
        assert all(c.origen == estrategia.origen() for c in resultado)

    def test_una_compuesta_conserva_el_origen_de_cada_hija(self):
        hibrida = HibridaStrategy(
            [ReglasManualesStrategy([ReglaUpsell("r1", RAMEN, EDAMAME)]), CoOcurrenciaStrategy()]
        )
        origenes = {c.origen for c in hibrida.puntuar(ctx(canasta(RAMEN)), limite=4)}
        assert OrigenSugerencia.MANUAL in origenes
        assert len(origenes) > 1

    def test_no_se_puede_instanciar_la_abstracta(self):
        with pytest.raises(TypeError):
            EstrategiaRecomendacion("suelta")  # type: ignore[abstract]

    def test_nunca_sugiere_lo_que_ya_trae_el_cliente(self):
        resultado = CoOcurrenciaStrategy().puntuar(ctx(canasta(RAMEN, GYOZA)), limite=5)
        ids = {c.producto_id for c in resultado}
        assert RAMEN not in ids
        assert GYOZA not in ids

    def test_el_peso_escala_el_score(self):
        base = CoOcurrenciaStrategy(peso=1.0).puntuar(ctx(canasta(RAMEN)), limite=1)
        doble = CoOcurrenciaStrategy(peso=2.0).puntuar(ctx(canasta(RAMEN)), limite=1)
        assert doble[0].score == pytest.approx(base[0].score * 2, rel=1e-6)


class TestAfinidadPorCategoria:
    def test_clasifica_por_el_nombre_de_la_categoria(self):
        cat = catalogo()
        assert cat.tipo_de(RAMEN) is TipoCategoria.FUERTE
        assert cat.tipo_de(REFRESCO) is TipoCategoria.BEBIDA
        assert cat.tipo_de(GYOZA) is TipoCategoria.ENTRADA
        assert cat.tipo_de(MOCHI) is TipoCategoria.POSTRE

    def test_con_un_fuerte_ofrece_bebida(self):
        resultado = AfinidadCategoriaStrategy().puntuar(ctx(canasta(RAMEN)), limite=1)
        assert catalogo().tipo_de(resultado[0].producto_id) is TipoCategoria.BEBIDA

    def test_si_ya_trae_bebida_no_le_ofrece_otra(self):
        resultado = AfinidadCategoriaStrategy().puntuar(ctx(canasta(RAMEN, REFRESCO)), limite=4)
        cat = catalogo()
        assert all(cat.tipo_de(c.producto_id) is not TipoCategoria.BEBIDA for c in resultado)

    def test_funciona_sin_un_solo_pedido(self):
        # El escalon que salva a un restaurante recien dado de alta.
        vacio = historial([])
        resultado = AfinidadCategoriaStrategy().puntuar(
            ctx(canasta(RAMEN), hist=vacio), limite=3
        )
        assert resultado
        assert all(c.nivel is NivelRespaldo.CATEGORIA for c in resultado)


class TestReglasManuales:
    def test_lo_manual_le_gana_a_lo_automatico(self):
        regla = ReglaUpsell("r1", disparador=RAMEN, sugerido=EDAMAME, prioridad=5)
        hibrida = HibridaStrategy([ReglasManualesStrategy([regla]), CoOcurrenciaStrategy()])
        resultado = hibrida.puntuar(ctx(canasta(RAMEN)), limite=3)
        assert resultado[0].producto_id == EDAMAME

    def test_la_regla_sin_disparador_aplica_siempre(self):
        regla = ReglaUpsell("r1", disparador=None, sugerido=MOCHI)
        resultado = ReglasManualesStrategy([regla]).puntuar(ctx(canasta(YAKIMESHI)), limite=2)
        assert resultado[0].producto_id == MOCHI

    def test_una_regla_a_un_producto_inactivo_se_descarta_con_motivo(self):
        regla = ReglaUpsell("r1", disparador=RAMEN, sugerido=EDAMAME)
        contexto = ctx(canasta(RAMEN), cat=catalogo(inactivos={EDAMAME}))
        crudos = ReglasManualesStrategy([regla]).candidatos(contexto)
        assert crudos[0].descartado
        assert "inactivo" in crudos[0].descarte
        assert ReglasManualesStrategy([regla]).puntuar(contexto, limite=3) == []


class TestDeterminismo:
    def test_dos_corridas_dan_exactamente_lo_mismo(self):
        estrategia = CoOcurrenciaStrategy()
        a = estrategia.puntuar(ctx(canasta(RAMEN)), limite=4)
        b = estrategia.puntuar(ctx(canasta(RAMEN)), limite=4)
        assert [c.producto_id for c in a] == [c.producto_id for c in b]
        assert [c.score for c in a] == [c.score for c in b]

    def test_los_empates_se_rompen_por_id(self):
        # Dos productos con exactamente la misma evidencia. Sin el id como
        # segundo criterio, el orden dependeria de como itero un dict.
        h = historial([([RAMEN, GYOZA], 20), ([RAMEN, EDAMAME], 20), ([RAMEN], 10)])
        resultado = CoOcurrenciaStrategy().puntuar(ctx(canasta(RAMEN), hist=h), limite=2)
        if resultado[0].score == resultado[1].score:
            assert str(resultado[0].producto_id) < str(resultado[1].producto_id)


class TestCascada:
    """Regresion de un bug que salio corriendo la demo de la Unidad 2.

    Con el ramen en el carrito, la gyoza tiene lift 2.0 y es la sugerencia
    correcta. Pero la afinidad por categoria puntuaba 3.0 (por ser bebida, que
    es lo que mejor acompana a un fuerte) y le ganaba. Los scores de escalones
    distintos no significan lo mismo y no se pueden comparar a pelo; por eso
    cada escalon tiene su banda.
    """

    def _cascada(self):
        from ceats_intel.application.fabrica import cascada_automatica

        return cascada_automatica(objetivo=4)

    def test_la_evidencia_le_gana_al_respaldo_generico(self):
        sugerencias = self._cascada().puntuar(ctx(canasta(RAMEN)), limite=3)
        assert sugerencias[0].producto_id == GYOZA
        assert sugerencias[0].origen is OrigenSugerencia.CO_OCURRENCIA

    def test_el_nivel_reportado_es_el_mejor_no_el_ultimo(self):
        cascada = self._cascada()
        cascada.candidatos(ctx(canasta(RAMEN)))
        # Aporto el nivel 1 y despues bajo al 4 para llenar. El nivel que se
        # reporta tiene que ser el mejor que alcanzo, no el ultimo que toco.
        assert cascada.nivel() is NivelRespaldo.SUCURSAL

    def test_nunca_se_queda_sin_nada_que_sugerir(self):
        from factories import historial

        vacio = historial([])
        sugerencias = self._cascada().puntuar(ctx(canasta(RAMEN), hist=vacio), limite=4)
        assert sugerencias

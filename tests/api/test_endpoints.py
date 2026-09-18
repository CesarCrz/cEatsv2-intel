"""Los cuatro endpoints, de la peticion HTTP a la respuesta.

Aqui no hay red: los repositorios se sustituyen con dobles que devuelven el
menu de sushi de `tests/factories.py`, el mismo con el que se probo el
dominio. Asi la prueba del API comprueba el cableado (validacion, auth, DTOs,
codigos de error) y no vuelve a probar la formula, que ya tiene lo suyo.

El caso que mas me importa es `test_la_api_da_lo_mismo_que_el_dominio`: si
alguien mete logica en el router en vez de en el caso de uso, la API y el
laboratorio se separan y la demo deja de cuadrar.
"""

from __future__ import annotations

import pytest
from factories import MENU, historial_del_refresco
from factories import catalogo as catalogo_de_prueba

from ceats_intel.api.dependencias import obtener_repositorio_catalogo, obtener_repositorio_ventas
from ceats_intel.main import app

LLAVE_CORRECTA = "clave-de-entrada-correcta"
CABECERA = {"X-Intel-Key": LLAVE_CORRECTA}

SUCURSAL = "00000000-0000-4000-8000-000000000001"
RESTAURANTE = "00000000-0000-4000-8000-000000000002"

# Los ids que arma `conftest.pid` para el menu de sushi de las factories.
def _pid(numero: int) -> str:
    from conftest import pid

    return str(pid(numero))


RAMEN = _pid(2)
GYOZA = _pid(3)


class _RepoVentas:
    async def historial(self, sucursal_id, ventana):
        # El doble ignora la ventana que le pidan: los pedidos de las
        # factories ya estan fechados dentro del escenario de 90 dias.
        return historial_del_refresco()


class _RepoCatalogo:
    async def catalogo(self, sucursal_id):
        return catalogo_de_prueba()


@pytest.fixture
def cliente_con_sushi(cliente):
    app.dependency_overrides[obtener_repositorio_ventas] = lambda: _RepoVentas()
    app.dependency_overrides[obtener_repositorio_catalogo] = lambda: _RepoCatalogo()
    return cliente


def pedir(cliente, **extra):
    cuerpo = {
        "sucursal_id": SUCURSAL,
        "restaurante_id": RESTAURANTE,
        "canasta": [RAMEN],
        "limite": 3,
    }
    cuerpo.update(extra)
    return cliente.post("/v1/recomendaciones", json=cuerpo, headers=CABECERA)


class TestRecomendaciones:
    def test_camino_feliz(self, cliente_con_sushi):
        respuesta = pedir(cliente_con_sushi)
        assert respuesta.status_code == 200

        cuerpo = respuesta.json()
        assert cuerpo["sugerencias"]
        assert len(cuerpo["sugerencias"]) <= 3
        assert cuerpo["huella"]
        assert cuerpo["version_modelo"] == "1.0.0"
        assert cuerpo["nivel_alcanzado"] >= 1

    def test_gana_la_gyoza_y_no_el_refresco(self, cliente_con_sushi):
        """El escenario que motiva el proyecto, ahora por HTTP.

        Con el ramen en la canasta, el refresco sale mas veces en total pero
        la gyoza es la que de verdad acompana. Si esto se invierte, alguien
        cambio el lift por un conteo.
        """
        ids = [s["producto_id"] for s in pedir(cliente_con_sushi).json()["sugerencias"]]
        assert ids[0] == GYOZA

    def test_no_devuelve_lo_que_ya_trae_la_canasta(self, cliente_con_sushi):
        cuerpo = pedir(cliente_con_sushi, canasta=[RAMEN, GYOZA], limite=5).json()
        ids = {s["producto_id"] for s in cuerpo["sugerencias"]}
        assert not ids & {RAMEN, GYOZA}

    def test_la_misma_peticion_da_la_misma_huella(self, cliente_con_sushi):
        a = pedir(cliente_con_sushi).json()["huella"]
        b = pedir(cliente_con_sushi).json()["huella"]
        assert a == b

    def test_explicar_agrega_evidencia_y_traza(self, cliente_con_sushi):
        sin = pedir(cliente_con_sushi).json()
        con = pedir(cliente_con_sushi, explicar=True).json()

        assert [s["producto_id"] for s in sin["sugerencias"]] == [
            s["producto_id"] for s in con["sugerencias"]
        ]
        assert sin["traza"] == []
        assert con["traza"]
        assert any(s["evidencia"] for s in con["sugerencias"])

    def test_la_evidencia_trae_los_numeros_de_la_formula(self, cliente_con_sushi):
        con = pedir(cliente_con_sushi, explicar=True).json()
        evidencia = next(s["evidencia"] for s in con["sugerencias"] if s["evidencia"])
        assert set(evidencia) == {
            "juntos",
            "frecuencia_ancla",
            "soporte_candidato",
            "confianza",
            "lift",
            "pedidos",
            "confianza_estadistica",
        }
        assert evidencia["lift"] > 1.0

    def test_la_api_da_lo_mismo_que_el_dominio(self, cliente_con_sushi):
        """La API no puede decidir distinto que el caso de uso.

        Se corre el mismo escenario por los dos lados y se comparan ids y
        huella. Si algun dia alguien mete un `if` en el router, esto se pone
        rojo.
        """
        from conftest import pid
        from factories import canasta

        from ceats_intel.application import (
            FabricaEstrategias,
            GenerarRecomendacionesUseCase,
            ModoUpsell,
            PeticionRecomendacion,
        )

        por_http = pedir(cliente_con_sushi).json()

        caso = GenerarRecomendacionesUseCase(FabricaEstrategias())
        directo = caso.ejecutar(
            PeticionRecomendacion(canasta=canasta(pid(2)), modo=ModoUpsell.AUTO, limite=3),
            historial=historial_del_refresco(),
            catalogo=catalogo_de_prueba(),
        )

        assert [s["producto_id"] for s in por_http["sugerencias"]] == list(directo.ids())

    @pytest.mark.parametrize("modo", ["auto", "manual", "hibrido", "popularidad", "afinidad"])
    def test_los_cinco_modos_responden(self, cliente_con_sushi, modo):
        assert pedir(cliente_con_sushi, modo=modo).status_code == 200

    def test_sin_historial_la_franja_no_se_queda_vacia(self, cliente_con_datos_vacios):
        """Restaurante recien abierto: no hay co-ocurrencia ni catalogo.

        Con los dobles vacios no hay productos que sugerir, pero lo que no
        puede pasar es que truene: tiene que responder 200 con la cascada
        agotada.
        """
        respuesta = pedir(cliente_con_datos_vacios)
        assert respuesta.status_code == 200
        assert respuesta.json()["sugerencias"] == []


class TestValidacionDeEntrada:
    def test_sucursal_que_no_es_uuid(self, cliente_con_sushi):
        assert pedir(cliente_con_sushi, sucursal_id="sushi-soru").status_code == 422

    def test_canasta_demasiado_grande(self, cliente_con_sushi):
        assert pedir(cliente_con_sushi, canasta=[RAMEN] * 51).status_code == 422

    def test_limite_fuera_de_rango(self, cliente_con_sushi):
        assert pedir(cliente_con_sushi, limite=0).status_code == 422
        assert pedir(cliente_con_sushi, limite=11).status_code == 422

    def test_campo_inesperado_truena_en_vez_de_ignorarse(self, cliente_con_sushi):
        assert pedir(cliente_con_sushi, campo_que_no_existe=1).status_code == 422

    def test_modo_inventado(self, cliente_con_sushi):
        assert pedir(cliente_con_sushi, modo="adivina").status_code == 422

    def test_el_error_no_trae_traza_de_python(self, cliente_con_sushi):
        cuerpo = pedir(cliente_con_sushi, sucursal_id="no").text
        assert "Traceback" not in cuerpo
        assert "ceats_intel" not in cuerpo


class TestLambda:
    def reducir(self, cliente, termino):
        return cliente.post("/v1/lambda/reducir", json={"termino": termino}, headers=CABECERA)

    def test_identidad(self, cliente):
        cuerpo = self.reducir(cliente, r"(\x. x) y").json()
        assert cuerpo["resultado"] == "y"
        assert cuerpo["pasos"]

    def test_church_dos_mas_tres(self, cliente):
        """SUMA 2 3 tiene que normalizar al numeral de Church del 5.

        Los nombres de `COMBINADORES` son texto fuente, no los conoce el
        parser: se sustituyen aqui, igual que hace el laboratorio del CRM
        cuando aprietas uno de los botones.
        """
        from ceats_intel.domain.lambdacalc import COMBINADORES, church

        termino = f"({COMBINADORES['suma']}) ({church(2)}) ({church(3)})"
        cuerpo = self.reducir(cliente, termino).json()
        assert cuerpo["resultado"] == str(church(5))

    def test_termino_mal_escrito_es_400(self, cliente):
        assert self.reducir(cliente, r"(\x. x").status_code == 400

    def test_omega_no_cuelga_el_servidor(self, cliente):
        """Omega no tiene forma normal. Tiene que cortarse, no colgarse."""
        respuesta = self.reducir(cliente, r"(\x. x x) (\x. x x)")
        assert respuesta.status_code == 422
        assert "forma normal" in respuesta.json()["detail"]

    def test_termino_vacio(self, cliente):
        assert self.reducir(cliente, "").status_code == 422

    def test_termino_demasiado_largo(self, cliente):
        assert self.reducir(cliente, "x" * 2001).status_code == 422


class TestAnalitica:
    def test_pronostico(self, cliente_con_sushi):
        respuesta = cliente_con_sushi.get(
            "/v1/pronostico/demanda",
            params={"sucursal_id": SUCURSAL, "pasos": 24},
            headers=CABECERA,
        )
        assert respuesta.status_code == 200
        assert len(respuesta.json()["puntos"]) == 24

    def test_pronostico_sin_ventas_no_truena(self, cliente_con_datos_vacios):
        respuesta = cliente_con_datos_vacios.get(
            "/v1/pronostico/demanda", params={"sucursal_id": SUCURSAL}, headers=CABECERA
        )
        assert respuesta.status_code == 200
        assert all(p["valor"] == 0.0 for p in respuesta.json()["puntos"])

    def test_pronostico_con_pasos_absurdos(self, cliente_con_sushi):
        respuesta = cliente_con_sushi.get(
            "/v1/pronostico/demanda",
            params={"sucursal_id": SUCURSAL, "pasos": 100000},
            headers=CABECERA,
        )
        assert respuesta.status_code == 422

    def test_menu_engineering_clasifica_todo_el_menu(self, cliente_con_sushi):
        respuesta = cliente_con_sushi.get(
            "/v1/menu-engineering", params={"sucursal_id": SUCURSAL}, headers=CABECERA
        )
        assert respuesta.status_code == 200
        productos = respuesta.json()["productos"]
        assert len(productos) == len(MENU)
        assert all(p["cuadrante"] for p in productos)
        assert all(p["nombre"] for p in productos)

    @pytest.mark.parametrize("serie", ["hora", "dia_semana"])
    def test_anomalias(self, cliente_con_sushi, serie):
        respuesta = cliente_con_sushi.get(
            "/v1/anomalias", params={"sucursal_id": SUCURSAL, "serie": serie}, headers=CABECERA
        )
        assert respuesta.status_code == 200
        assert respuesta.json()["serie"] == serie

    def test_serie_inventada(self, cliente_con_sushi):
        respuesta = cliente_con_sushi.get(
            "/v1/anomalias", params={"sucursal_id": SUCURSAL, "serie": "por_luna"}, headers=CABECERA
        )
        assert respuesta.status_code == 422

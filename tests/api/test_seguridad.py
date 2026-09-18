"""Lo que tiene que cumplir la puerta de entrada del servicio.

Estas pruebas son las que me dejan dormir: si alguien afloja la verificacion
de la llave o publica un endpoint nuevo sin la dependencia, aqui se ve.

La regla de SEGURIDAD.md es que solo `/healthz` va sin llave, y que la
respuesta de un rechazo es identica trate de una llave ausente o de una
equivocada.
"""

from __future__ import annotations

import pytest

# La misma que pone `tests/api/conftest.py` en el entorno.
LLAVE_CORRECTA = "clave-de-entrada-correcta"

RUTAS_PROTEGIDAS = [
    ("POST", "/v1/recomendaciones"),
    ("POST", "/v1/lambda/reducir"),
    ("GET", "/v1/pronostico/demanda"),
    ("GET", "/v1/menu-engineering"),
    ("GET", "/v1/anomalias"),
]


class TestLlaveDeEntrada:
    def test_healthz_no_pide_llave(self, cliente):
        respuesta = cliente.get("/healthz")
        assert respuesta.status_code == 200
        assert respuesta.json() == {"status": "ok"}

    def test_healthz_no_revela_nada_del_sistema(self, cliente):
        # Ni version, ni estado del backend, ni nombre del servicio.
        assert set(cliente.get("/healthz").json()) == {"status"}

    @pytest.mark.parametrize(("metodo", "ruta"), RUTAS_PROTEGIDAS)
    def test_sin_llave_es_401(self, cliente, metodo, ruta):
        assert cliente.request(metodo, ruta, json={}).status_code == 401

    @pytest.mark.parametrize(("metodo", "ruta"), RUTAS_PROTEGIDAS)
    def test_llave_equivocada_es_401(self, cliente, metodo, ruta):
        respuesta = cliente.request(metodo, ruta, json={}, headers={"X-Intel-Key": "no-es"})
        assert respuesta.status_code == 401

    def test_una_llave_casi_correcta_tampoco_pasa(self, cliente):
        casi = LLAVE_CORRECTA[:-1] + "x"
        respuesta = cliente.post("/v1/lambda/reducir", json={}, headers={"X-Intel-Key": casi})
        assert respuesta.status_code == 401

    def test_un_prefijo_de_la_llave_no_pasa(self, cliente):
        # compare_digest no compara prefijos; esto documenta que no hay
        # ningun `startswith` escondido.
        respuesta = cliente.post(
            "/v1/lambda/reducir", json={}, headers={"X-Intel-Key": LLAVE_CORRECTA[:10]}
        )
        assert respuesta.status_code == 401

    def test_el_401_no_dice_por_que_fallo(self, cliente):
        sin = cliente.post("/v1/lambda/reducir", json={})
        mala = cliente.post("/v1/lambda/reducir", json={}, headers={"X-Intel-Key": "no-es"})
        assert sin.json() == mala.json()

    def test_el_rechazo_ocurre_antes_de_validar_el_cuerpo(self, cliente):
        # Un cuerpo invalido con llave mala responde 401, no 422: quien no
        # esta autorizado no averigua nada sobre la forma esperada.
        respuesta = cliente.post(
            "/v1/recomendaciones", json={"basura": 1}, headers={"X-Intel-Key": "no-es"}
        )
        assert respuesta.status_code == 401


class TestSuperficieExpuesta:
    def test_no_hay_rutas_publicas_de_mas(self, cliente):
        """La unica ruta sin `verificar_llave` debe ser /healthz.

        Se lee de los propios routers, no de una lista escrita a mano: si
        alguien registra un endpoint nuevo y olvida la dependencia, esta
        prueba lo caza sin que nadie tenga que acordarse de actualizarla.
        """
        from ceats_intel.api.dependencias import verificar_llave
        from ceats_intel.main import app

        def hojas(rutas):
            """FastAPI envuelve los routers incluidos; hay que bajar a las hojas."""
            for ruta in rutas:
                incluido = getattr(ruta, "original_router", None)
                if incluido is not None:
                    yield from hojas(incluido.routes)
                elif hasattr(ruta, "routes"):
                    yield from hojas(ruta.routes)
                else:
                    yield ruta

        publicas = set()
        for ruta in hojas(app.routes):
            dependencias = getattr(getattr(ruta, "dependant", None), "dependencies", [])
            if not any(d.call is verificar_llave for d in dependencias):
                publicas.add(ruta.path)

        assert publicas == {"/healthz"}

    def test_la_documentacion_interactiva_esta_apagada(self, cliente):
        assert cliente.get("/docs").status_code == 404
        assert cliente.get("/openapi.json").status_code == 404

    def test_metodo_equivocado_no_pasa(self, cliente):
        assert cliente.get("/v1/recomendaciones").status_code == 405

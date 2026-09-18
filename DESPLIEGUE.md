# Poner esto en producción

Pasos en orden. Del 1 al 4 no se toca nada de lo que ya está corriendo.

## 1. Generar las llaves

Dos, distintas entre sí y distintas de `API_SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"   # INTEL_SERVICE_KEY
python -c "import secrets; print(secrets.token_hex(32))"   # INTEL_INBOUND_KEY
```

`INTEL_SERVICE_KEY` es la que el microservicio usa para leer del backend.
`INTEL_INBOUND_KEY` es la que el backend usa para hablarle al microservicio.

No las pegues en ningún archivo del repo. Van sólo en las variables de EasyPanel.

## 2. Backend de cEats

Variables nuevas:

| Variable | Valor |
|---|---|
| `INTEL_SERVICE_KEY` | la primera que generaste |
| `INTEL_INBOUND_KEY` | la segunda |
| `INTEL_URL` | `http://ceatsv2-intel:8000` |

Redeploy. Todavía no pasa nada: sin la bandera prendida, el checkout ni pregunta.

Comprueba que el endpoint quedó cerrado:

```bash
curl -i https://<backend>/api/internal/intel/ventas?sucursal_id=<uuid>&desde=2026-06-16&hasta=2026-09-14
# tiene que responder 401

curl -i -X POST https://<backend>/api/internal/intel/ventas
# tiene que responder 405
```

Y con la llave, revisa el JSON **a mano** antes de seguir. Ningún campo de
cliente: sin teléfono, sin nombre, sin dirección, sin CLABE.

## 3. Migración

```sql
-- supabase/migrations/2026-09-16_intel_decisiones.sql
```

Es idempotente. Córrela en el SQL editor de Supabase. Verifica después que la
RLS quedó activa:

```sql
select relrowsecurity from pg_class where relname = 'intel_decisiones';
-- tiene que dar true
```

## 4. Microservicio en EasyPanel

App nueva desde el repo `CesarCrz/cEatsv2-intel`, rama `main`, con el
`Dockerfile` de la raíz.

**Sin dominio. Sin puerto publicado.** Esto no es opcional: el servicio no se
expone a internet, sólo lo alcanza el backend por el nombre de servicio de la
red interna de Docker.

Variables:

| Variable | Valor |
|---|---|
| `CEATS_BACKEND_URL` | la URL interna del backend |
| `INTEL_SERVICE_KEY` | la primera |
| `INTEL_INBOUND_KEY` | la segunda |

Las tres son obligatorias: si falta una, el proceso no arranca. Es a propósito.

Recursos: 256 MB de RAM alcanzan. El healthcheck pega a `/healthz`.

Después del deploy, desde el backend:

```bash
curl -s http://ceatsv2-intel:8000/healthz
```

Y desde fuera del VPS, confirma que **no** responde nada.

## 5. Prueba de humo, con la bandera apagada

Entra al CRM, `/admin/clientes/<id>/inteligencia`. El laboratorio funciona
aunque la bandera esté apagada: por eso existe, para ver qué recomendaría el
micro antes de encendérselo a nadie.

Arma un carrito con un platillo real y calcula. Revisa que:

- Salgan sugerencias y que tengan sentido para ese platillo.
- La evidencia traiga números creíbles (soporte, confianza, lift).
- La traza del pipeline cuadre.
- El nivel alcanzado sea 1 o 2 si el restaurante tiene volumen.

## 6. Encender un restaurante

Bandera `intel_recomendaciones` en el CRM, sólo para Sushi Soru. Nadie más.

Haz un pedido real desde el celular, con el menú público. Luego vuelve al
laboratorio, arma el mismo carrito y compara. Tienen que coincidir los ids y el
orden.

Mira también el panel de decisiones: ahí debe aparecer la del checkout, y el
botón de reproducir debe decir que coinciden.

## 7. Apagar y volver a prender

Con el restaurante encendido, apaga el contenedor del microservicio desde
EasyPanel y haz otro pedido. El checkout tiene que seguir funcionando con el
resolutor anterior, sin un solo hueco en la franja de sugerencias.

Vuelve a prenderlo. Si esto funciona, el riesgo de la integración está acotado.

## 8. Cron de limpieza

Las decisiones se guardan 30 días. Programa el cron de limpieza en EasyPanel
siguiendo el patrón de los que ya existen en `app/api/cron/`.

---

## Si algo sale mal

Apaga la bandera `intel_recomendaciones`. En segundos el checkout vuelve al
comportamiento anterior, sin redeploy y sin tocar nada más. Ese es el punto de
que exista la bandera.

## Antes de la demo

Ten grabado el recorrido completo y capturas de las pantallas. Si el wifi del
salón falla, no te quedas sin proyecto que enseñar.

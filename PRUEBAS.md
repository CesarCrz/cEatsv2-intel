# Cómo probar el proyecto, unidad por unidad

Todo lo de aquí está corrido en esta máquina (Windows 11, Python 3.13, PowerShell).
Si un comando falla, es que algo cambió, no que el comando esté mal escrito.

Las unidades 1, 2 y 3 se prueban enteras en la laptop, sin internet y sin
desplegar nada. La unidad 4 se prueba casi entera en local; lo único que pide
el VPS es la parte que habla con el backend de cEats de verdad.

---

## Preparar la máquina (una sola vez)

Desde `C:\Users\cruzx\Desktop\cEatsv2-intel`:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -e ".[api,dev]"
```

Ya está hecho. Para comprobarlo:

```powershell
.venv\Scripts\python.exe -c "import fastapi, pytest; print('listo')"
```

Un detalle de Windows: la consola por defecto usa cp1252 y las demos imprimen
acentos. Si ves `int�rprete` en vez de `intérprete`, no es un bug del código,
es la consola. Se arregla con:

```powershell
$env:PYTHONUTF8 = "1"
```

Ponlo antes de la demo si vas a proyectar la pantalla.

---

## La prueba de un solo comando

```powershell
.venv\Scripts\python.exe -m pytest -q
```

Esperado: **208 passed**. Si sale eso, las cuatro unidades funcionan.

Y el linter, que también cuenta como evidencia de que el código está cuidado:

```powershell
.venv\Scripts\python.exe -m ruff check .
```

Esperado: `All checks passed!`

---

## Unidad 1 — Clases, objetos, encapsulamiento

**Qué demuestra:** value objects inmutables, entidades con identidad,
agregado raíz, copias defensivas.

**Pruebas automáticas:**

```powershell
.venv\Scripts\python.exe -m pytest tests/domain/test_valueobjects.py tests/domain/test_entidades.py -v
```

Esperado: **38 passed**.

**Demo en vivo:**

```powershell
.venv\Scripts\python.exe -m demos.u1
```

Lo que tienes que señalar cuando la corras:

1. La parte 2 lista los productos con su soporte. Son objetos, no diccionarios.
2. La parte 3 es la que vale: muestra que el refresco sale junto al ramen 84
   veces, pero sale en el 43% de *todos* los pedidos. Contar no sirve. Ese es
   el problema que resuelve la Unidad 2.
3. La parte 4 intenta modificar un pedido desde fuera y falla con
   `AttributeError: 'tuple' object has no attribute 'append'`. Ese es el
   encapsulamiento: `lineas` devuelve una tupla, no la lista interna.

**Con datos reales** (opcional, si ya volcaste un CSV):

```powershell
.venv\Scripts\python.exe -m demos.u1 --csv datos\ventas.csv
```

El CSV lo produce `scripts/volcar-ventas-intel.mjs` del backend. Necesita
`CEATS_BACKEND_URL` e `INTEL_SERVICE_KEY`, así que eso ya es después del
despliegue. Para la demo, los datos de ejemplo alcanzan.

**Evidencia para la maestra:** rama `unidad-1`, tag `v0.1-u1`, diagrama
`docs/uml/png/u1-clases-dominio.png`.

---

## Unidad 2 — Herencia, polimorfismo, clases abstractas

**Qué demuestra:** `EstrategiaRecomendacion` como clase abstracta con método
plantilla, cinco subclases, composites (híbrida y cascada) que son
estrategias ellas mismas.

**Pruebas automáticas:**

```powershell
.venv\Scripts\python.exe -m pytest tests/domain/test_recomendacion.py -v
```

Esperado: **30 passed**. En la rama `unidad-2` completa son 68.

**Demo en vivo:**

```powershell
.venv\Scripts\python.exe -m demos.u2
```

Y las variantes, que son las que hacen ver el polimorfismo:

```powershell
.venv\Scripts\python.exe -m demos.u2 --modo auto
.venv\Scripts\python.exe -m demos.u2 --modo manual
.venv\Scripts\python.exe -m demos.u2 --modo hibrido
.venv\Scripts\python.exe -m demos.u2 --sin-datos
```

Lo que tienes que señalar:

1. En la parte 3, la línea que llama a la estrategia es **la misma** en los
   cuatro modos. No hay un solo `isinstance` ni un `if` por tipo. Eso es el
   polimorfismo, y es lo que la maestra va a querer ver.
2. `--sin-datos` es el restaurante recién abierto: la cascada baja hasta
   afinidad por categoría y sigue respondiendo. La franja de sugerencias nunca
   se queda vacía.
3. La parte 4 explica la afinidad por categoría: sale del menú, no del
   historial, y no es aprendizaje automático. Es la regla del mesero.

**Evidencia:** rama `unidad-2`, tag `v0.2-u2`, diagramas
`u2a-estrategias.png` y `u2b-pronostico-analitica.png`.

---

## Unidad 3 — Cálculo lambda y composición de funciones

**Qué demuestra:** intérprete completo de cálculo lambda escrito a mano
(parser de descenso recursivo, sin `eval` ni `exec`), y el score del upsell
escrito como composición de funciones puras.

**Pruebas automáticas:**

```powershell
.venv\Scripts\python.exe -m pytest tests/domain/test_lambdacalc.py -v
```

Esperado: **27 passed**.

**Demo en vivo:**

```powershell
.venv\Scripts\python.exe -m demos.u3
```

Los cuatro bloques son sintaxis, alfa, beta y eta. Y al final la parte que
conecta con el negocio: el pipeline del score.

**REPL, para cuando la maestra quiera probar algo ella:**

```powershell
.venv\Scripts\python.exe -m demos.u3 --repl
```

Términos que vale la pena tener a la mano:

| Escribes | Sale | Por qué importa |
|---|---|---|
| `(\x. x) y` | `y` | beta reducción, un paso |
| `(\x. \y. x) a b` | `a` | el combinador K |
| `(\x. \y. x) y` | `(\y1. y)` | **alfa conversión**: renombra para no capturar la `y` libre |
| `(\x. x x) (\x. x x)` | se corta a los 10000 pasos | Omega: no tiene forma normal |

El tercero es el que hay que enseñar sí o sí. Si el intérprete no renombrara,
la `y` libre quedaría atrapada por el binder y el resultado sería incorrecto.

Para el numeral de Church del 5 (2 + 3), el comando largo está en la demo
completa; el REPL no expande nombres de combinadores solo.

**Evidencia:** rama `unidad-3`, tag `v0.3-u3`, diagrama `u3-calculo-lambda.png`.

---

## Unidad 4 — Capas, patrones, API y despliegue

Esta es la única que se parte en dos: lo que se prueba en la laptop y lo que
pide el VPS.

### Lo que sí se prueba en local

**Pruebas automáticas** (con dobles en lugar de red, así que no necesitan
backend):

```powershell
.venv\Scripts\python.exe -m pytest tests/api tests/infrastructure tests/test_coherencia.py -v
```

Esperado: **113 passed** (51 del API, 12 de infraestructura, 50 de coherencia).

Vale la pena correr aparte la que sostiene toda la demo:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_coherencia.py -v
```

Son 200 comparaciones (40 canastas al azar × 5 modos) entre el camino del
checkout y el del laboratorio. Si alguien alguna vez mete un `if` que cambie
el resultado según quién llame, esto se pone rojo.

**Levantar el servicio en local.** Necesita las tres variables obligatorias.
Para probar en la laptop pueden ser cualquier cosa, porque el backend real no
va a contestar de todos modos:

```powershell
$env:CEATS_BACKEND_URL = "http://localhost:3001"
$env:INTEL_SERVICE_KEY = "llave-salida-local"
$env:INTEL_INBOUND_KEY = "llave-entrada-local"
.venv\Scripts\python.exe -m uvicorn ceats_intel.main:app --port 8078
```

Deja esa ventana corriendo y abre **otra** de PowerShell para lo siguiente:

```powershell
$h = @{ "X-Intel-Key" = "llave-entrada-local" }
$cuerpo = '{"termino":"(\\x. x) y"}'

# 1. Healthcheck, sin llave. Tiene que dar 200 y nada más que {"status":"ok"}.
(Invoke-WebRequest http://127.0.0.1:8078/healthz -UseBasicParsing).Content

# 2. El intérprete de la Unidad 3, ahora por HTTP.
(Invoke-WebRequest http://127.0.0.1:8078/v1/lambda/reducir -Method POST `
  -Headers $h -ContentType "application/json" -Body $cuerpo -UseBasicParsing).Content

# 3. Sin llave: 401.
try { Invoke-WebRequest http://127.0.0.1:8078/v1/lambda/reducir -Method POST `
  -ContentType "application/json" -Body $cuerpo -UseBasicParsing }
catch { $_.Exception.Response.StatusCode.value__ }

# 4. La documentación interactiva está apagada a propósito: 404.
try { Invoke-WebRequest http://127.0.0.1:8078/docs -UseBasicParsing }
catch { $_.Exception.Response.StatusCode.value__ }
```

Salidas verificadas:

```
{"status":"ok"}
{"resultado":"y","pasos":[{"regla":"beta","antes":"((\\x. x) y)","despues":"y"}]}
401
404
```

Un detalle que importa para el punto 3: manda un JSON **válido**. Si el
cuerpo está mal formado, FastAPI responde 422 antes de llegar a revisar la
llave, y parece que la autenticación no funciona cuando sí funciona.

**Comprobar que arranca cerrado.** Quita una variable obligatoria y mira que
el proceso no levante:

```powershell
Remove-Item Env:\INTEL_INBOUND_KEY
.venv\Scripts\python.exe -m uvicorn ceats_intel.main:app --port 8078
```

Tiene que tronar al importar, antes de escuchar en el puerto. Es a propósito:
nunca queda abierto por omisión.

**Degradación cuando el backend no está.** Con `CEATS_BACKEND_URL` apuntando a
un host que no existe, `/v1/recomendaciones` responde **503** con
`{"detail":"Servicio no disponible temporalmente"}`, no una traza de Python.
Ya está verificado; en producción ese 503 es lo que hace que el checkout se
vaya al resolutor anterior sin que el cliente note nada.

### Lo que sólo se puede probar desplegado

Tres cosas, y las tres son la integración real:

1. `/v1/recomendaciones` contra ventas de verdad.
2. El laboratorio del CRM, en `/admin/clientes/<id>/inteligencia`.
3. Que el checkout del menú público y el laboratorio den lo mismo.

Los pasos están en `DESPLIEGUE.md`. Lo que te toca a ti, en corto:

| Dónde | Qué pones |
|---|---|
| Generas tú | dos llaves de 32 bytes, distintas entre sí y de `API_SECRET_KEY` |
| Backend de cEats | `INTEL_SERVICE_KEY`, `INTEL_INBOUND_KEY`, `INTEL_URL=http://ceatsv2-intel:8000` |
| Supabase | correr `2026-09-16_intel_decisiones.sql` |
| App nueva en EasyPanel | repo `CesarCrz/cEatsv2-intel`, rama `main`, Dockerfile de la raíz, **sin dominio y sin puerto publicado** |
| Variables de esa app | `CEATS_BACKEND_URL`, `INTEL_SERVICE_KEY`, `INTEL_INBOUND_KEY` |
| Bandera | `intel_recomendaciones`, sólo para Sushi Soru |

Las llaves se generan así:

```powershell
.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
```

Córrelo dos veces. No las pegues en ningún archivo del repo: van sólo en las
variables de EasyPanel.

**Evidencia:** rama `unidad-4`, tag `v1.0`, diagramas `u4-patrones-y-capas.png`,
`secuencia-recomendacion.png` y `despliegue-y-seguridad.png`.

---

## Enseñar la entrega de cada unidad

Cada unidad es una rama y un tag. Para pararte en una:

```powershell
git checkout unidad-1
.venv\Scripts\python.exe -m pytest -q
```

| Rama | Tag | Pruebas | Qué hay |
|---|---|---|---|
| `unidad-1` | `v0.1-u1` | 38 | sólo value objects y entidades |
| `unidad-2` | `v0.2-u2` | 68 | + estrategias y cascada |
| `unidad-3` | `v0.3-u3` | 145 | + cálculo lambda y pipeline |
| `unidad-4` | `v1.0` | 208 | + infraestructura, API y despliegue |

Verificado: las cuatro ramas corren en verde por su cuenta. Ese es el punto de
partirlas así, que cada entrega se sostenga sola y no dependa de código que
todavía no existía.

Para volver al final:

```powershell
git checkout unidad-4
```

---

## Los diagramas y el documento

Los PNG ya están exportados en `docs/uml/png/`, así que la maestra los puede
ver sin instalar nada. El fuente `.puml` de cada uno está en `docs/uml/` por
si quiere ver que están escritos, no dibujados a mano.

Para volver a exportarlos:

```powershell
java -jar plantuml.jar -tpng -o png docs\uml\*.puml
```

El documento en LaTeX es `docs/latex/proyecto.tex`. **No está compilado**:
esta máquina no tiene `pdflatex`. Dos salidas:

- Instalar MiKTeX y correr `latexmk -pdf proyecto.tex` dentro de `docs/latex`.
- O subir el `.tex` a Overleaf y descargar el PDF. Es más rápido y no hay que
  instalar 2 GB.

---

## Antes de la demo

- [ ] `pytest -q` da 208 passed
- [ ] `ruff check .` limpio
- [ ] Las tres demos corren con `$env:PYTHONUTF8 = "1"` puesto
- [ ] El PDF compilado
- [ ] El servicio desplegado y el laboratorio del CRM abriendo
- [ ] Un pedido real hecho con la bandera encendida, y comparado con el laboratorio
- [ ] Video de respaldo grabado, por si el wifi del salón falla

El guion de la exposición y las diez preguntas de defensa están en
`GUIA_EXPOSICION.md`.

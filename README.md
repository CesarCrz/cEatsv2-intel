# cEatsv2-intel

Microservicio en Python que calcula recomendaciones y analítica para cEats.
Es mi proyecto final de Programación II, pero no es un proyecto de escuela:
corre en el mismo VPS que el resto de la plataforma y el checkout real lo
consume.

Documentación: [`docs/latex/proyecto.tex`](docs/latex/proyecto.tex).
Diagramas: [`docs/uml/`](docs/uml/).
Seguridad: [`SEGURIDAD.md`](SEGURIDAD.md).
Laboratorio del CRM: [`PLAN_LABORATORIO.md`](PLAN_LABORATORIO.md).

## Qué resuelve

cEats ya sugiere productos en el checkout. El problema es cómo los escoge:
cuenta cuántas veces dos productos salieron en el mismo pedido y ya. Con eso el
refresco siempre gana, porque el refresco aparece con todo. No porque el cliente
haya pedido tacos, sino porque medio mundo pide refresco.

Lo que quiero medir es otra cosa: qué tanto sube la probabilidad de B *porque*
el cliente pidió A. Eso es el lift, y es la diferencia entre sugerir algo útil y
sugerir lo mismo siempre.

De paso, ya que tengo el historial cargado en memoria, salen dos cosas más casi
gratis: pronóstico de pedidos por hora y clasificación de productos por margen
contra popularidad.

## Endpoints

```
POST /v1/recomendaciones      upsell con soporte, confianza y lift
GET  /v1/pronostico/demanda   pedidos esperados por hora
GET  /v1/menu-engineering     estrella / caballo / puzzle / perro
GET  /v1/anomalias            caídas y picos de venta
GET  /healthz                 para el healthcheck de EasyPanel
```

## Cómo está armado

```
src/ceats_intel/
├── api/              FastAPI: routers, DTOs, autenticación
├── application/      casos de uso, fábrica de estrategias, builder
├── domain/           POO pura, cero imports de red
│   ├── valueobjects/ ProductoId, SucursalId, Dinero, VentanaTemporal
│   ├── entidades/    Producto, Pedido, LineaPedido, Canasta, HistorialVentas
│   ├── recomendacion/EstrategiaRecomendacion y sus subclases
│   ├── pronostico/   ModeloPronostico y sus subclases
│   ├── analitica/    ClasificadorMenu, DetectorAnomalias
│   ├── scoring/      PipelineScoring, Combinadores
│   ├── lambdacalc/   Termino, Var, Abs, App, Evaluador
│   └── puertos/      RepositorioVentas, RepositorioCatalogo
├── infrastructure/   cliente HTTP al backend, caché, config
└── main.py
```

Las dependencias van en un solo sentido: `api` usa `application`, `application`
usa `domain`, y `domain` no usa a nadie. `infrastructure` implementa los puertos
que el dominio declara. La ventaja práctica es que todo el dominio se prueba con
`pytest` sin levantar servidor ni tocar la red.

## Plan por unidad

Cada unidad cierra en su rama, con su tag y su demo. Eso es lo que entrego como
evidencia.

**Unidad 1** (`unidad-1`, tag `v0.1-u1`). Las clases del dominio: value objects,
entidades, el agregado de historial. Encapsulación con copias defensivas de las
colecciones. La demo carga pedidos reales, arma los objetos, imprime totales, y
al final intenta mutar las líneas de un pedido y truena. Ahí se explica el tema
de referencias y aliasing.

**Unidad 2** (`unidad-2`, tag `v0.2-u2`). Las jerarquías:
`EstrategiaRecomendacion` abstracta con cuatro subclases, `ModeloPronostico` con
tres, el clasificador de menú. La demo corre el mismo caso con `--modo auto`,
`--modo manual` y `--modo hibrido`: tres salidas distintas, una sola línea de
código llamador.

**Unidad 3** (`unidad-3`, tag `v0.3-u3`). El intérprete de cálculo lambda, con
conversión alfa, reducción beta en orden normal y conversión eta. Y el pipeline
de scoring escrito como composición de funciones puras, que es la misma idea
aplicada al negocio. La demo es un REPL donde reduzco los combinadores I, K y S
y los numerales de Church viendo cada paso.

**Unidad 4** (`unidad-4`, tag `v1.0`). Todo lo que falta para que esto sirva:
cliente HTTP, caché, el endpoint despersonalizado del lado del backend, la tabla
de decisiones, el laboratorio del CRM, la integración con el checkout detrás de
feature flag, Docker y despliegue.

El orden de construcción no es ese. Primero hay que poder sacar los datos, o la
Unidad 1 no se puede demostrar con nada real. El orden va al final de
`PLAN_LABORATORIO.md`.

## Correr en local

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
copy .env.example .env
uvicorn ceats_intel.main:app --reload --port 8000
pytest
```

## Diagramas

Los `.puml` se pegan tal cual en plantuml.com y te descarga el PNG. Para
exportarlos todos de un jalón, con java y `plantuml.jar` a la mano:

```bash
java -jar plantuml.jar -tpng -o png docs/uml/*.puml
```

Los PNG caen en `docs/uml/png/`, que es de donde el LaTeX los jala.

## El PDF

```bash
cd docs/latex
latexmk -pdf proyecto.tex
```

## Variables de entorno

`CEATS_BACKEND_URL` es la URL interna del backend. `INTEL_SERVICE_KEY` es la
clave con la que este servicio lee del backend, e `INTEL_INBOUND_KEY` la que
exige a quien lo llame. Las tres son obligatorias: si falta una, el servicio no
arranca. Prefiero que truene al inicio a que arranque abierto.

Opcionales, con valor por defecto: `CACHE_TTL_SEGUNDOS` (300),
`HTTP_TIMEOUT_SEGUNDOS` (2), `MAX_PASOS_LAMBDA` (10000).

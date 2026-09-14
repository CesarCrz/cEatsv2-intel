# Laboratorio de inteligencia en el CRM

Va en `/admin/clientes/[id]/inteligencia`, al lado de la página de upsell que ya
existe. Selector de sucursal arriba. Sólo superadmin.

Sin esta página el micro es invisible. Nadie puede ver un microservicio interno,
y un proyecto que no se puede enseñar no sirve de proyecto.

## Cómo funciona el laboratorio

Escoges cualquier platillo del menú real de la sucursal, en el momento que sea,
y calcula al instante. No necesitas que exista un pedido. Escoges Yakimeshi
Crispy y ves exactamente lo que vería un cliente que en ese momento trajera el
Yakimeshi Crispy en su carrito.

Puedes armar canastas de varios productos, porque las sugerencias dependen de
toda la canasta, no de un platillo suelto. Si el cliente lleva tres cosas, el
cálculo parte de las tres, y en el laboratorio reproduces ese caso agregando las
mismas tres.

## Que coincida de verdad

Si pido un Yakimeshi Crispy en el menú público y me salen tres sugerencias, al
escoger ese mismo platillo en el laboratorio me tienen que salir las mismas
tres, en el mismo orden. Si no coincide, la demo se cae.

Eso no pasa solo. Hay cuatro cosas que lo pueden romper y cada una tiene su
respuesta.

**Una sola ruta de código.** El laboratorio no reimplementa nada: llama el mismo
`GenerarRecomendacionesUseCase.ejecutar()` que el checkout. Lo único que cambia
es una bandera `explicar: true`, que hace que la respuesta traiga además el
detalle del cálculo. La lista de sugerencias se arma con el mismo código en los
dos caminos.

Si alguien un día mete un `if` que cambie el resultado según el origen, se acabó
la coherencia. Hay una prueba automática que lo vigila, la de más abajo.

**La ventana se redondea al día.** El error fácil: el checkout pide los últimos
90 días a las 14:03 y yo entro al laboratorio a las 14:07. Son ventanas
distintas, y basta un pedido nuevo en medio para invertir dos candidatos
empatados. Por eso la ventana siempre es `[hoy - 90 días 00:00, hoy 00:00)` en
la zona horaria de la sucursal. Todo lo que se calcule el mismo día usa los
mismos pedidos. A medianoche cambia, y eso está bien: es explicable.

**Desempates sin azar.** Nunca depender del orden de iteración de un `dict` ni
de un `set`. El orden final es por score descendente y, si hay empate, por
`producto_id` ascendente. Los scores se redondean a 6 decimales antes de
comparar, para que un error de punto flotante no voltee un empate.

**La huella.** Cada respuesta trae un SHA-256 recortado a 16 caracteres de
`sucursal_id | canasta ordenada | modo | version_config | ventana |
version_modelo | limite`. Dos peticiones con la misma huella tienen que dar el
mismo resultado. Es la llave de caché y es lo que el laboratorio muestra en
pantalla para comparar. `version_modelo` sube cuando cambian los pesos o el
algoritmo, así una decisión vieja no se confunde con una nueva.

La caché usa esa huella como llave y vive en el micro con TTL de 5 minutos.
Checkout y laboratorio pegan a la misma entrada, así que dentro de esa ventana
la respuesta es literalmente la misma, no nada más equivalente.

**La prueba que lo vigila.** En cada commit se generan 200 canastas al azar y se
pide la recomendación por las dos rutas. Si alguna difiere en contenido o en
orden, falla. Es barata y se da cuenta al instante si alguien rompió la regla de
la ruta única.

## Feature flag

Bandera `intel_recomendaciones` por restaurante, en el módulo de feature flags
que ya está en el CRM. Prendida, el checkout le pide las sugerencias al micro.
Apagada, usa el resolver de siempre.

Sirve para encender clientes de uno en uno, para apagar todo en segundos si algo
sale mal, y para hacer el comparativo en vivo delante de la maestra.

El laboratorio funciona con el flag apagado. Así puedo ver qué recomendaría el
micro para un restaurante antes de encendérselo.

## Restaurantes con pocos pedidos

Un restaurante con 40 pedidos en tres meses no tiene co-ocurrencias, tiene
ruido. Dos platillos que coincidieron dos veces no significan nada. Pero el
sistema no se puede quedar callado: una franja de upsell vacía se ve rota y baja
la conversión más de lo que la sube una sugerencia mediocre.

### Suavizado en vez de corte seco

En lugar de exigir un mínimo de pedidos y tirar todo lo que no llegue, la
confianza se jala hacia la popularidad general del producto:

```
conf_suavizada(A → B) = ( n(A ∩ B) + α · sop(B) ) / ( n(A) + α )
```

con α de unos 10 pedidos. Cuando hay pocos datos de A, la fórmula se apoya en
qué tan popular es B en general. Conforme A acumula pedidos, α pesa cada vez
menos y el resultado converge al valor real. No hay salto brusco entre "sin
datos" y "con datos". El lift se calcula sobre esa confianza suavizada.

### Cascada de respaldo

Aun con suavizado hay casos sin nada. La cascada va bajando de nivel hasta
encontrar algo, y siempre encuentra:

| Nivel | De dónde salen | Cuándo aplica |
|---|---|---|
| 1 | Co-ocurrencia de la sucursal | Hay señal suficiente |
| 2 | Co-ocurrencia del restaurante completo | La sucursal sola no alcanza |
| 3 | Co-ocurrencia con ventana de 365 días | Restaurante nuevo o de poco volumen |
| 4 | Afinidad por categoría | Sale del menú, no del historial |
| 5 | Más vendidos de la sucursal | Hay ventas pero no pares |
| 6 | Más vendidos del restaurante | Sucursal recién abierta |
| 7 | Productos destacados del menú | Restaurante sin un solo pedido |

El nivel 4 es el que casi siempre salva el día, porque no necesita historial.
Sale de cómo está armado el menú: si el cliente lleva un plato fuerte y no lleva
bebida, se le sugiere una bebida; si no lleva postre, un postre. Es lo que
cualquier mesero hace, y funciona desde el primer día del restaurante.

Cada sugerencia viaja con su nivel y con una etiqueta de confianza estadística.
El laboratorio la muestra sin adornos: *"Nivel 4, afinidad por categoría. Sólo
12 pedidos con este platillo en 90 días, no alcanza para co-ocurrencia."* Más
vale decirlo que fingir precisión.

Los umbrales se configuran por restaurante desde el CRM, con valores por defecto
razonables.

## Guardar las decisiones

Aparte del simulador, quiero poder decir "reprodúceme lo que pasó en el checkout
hace dos minutos". Para eso hay que guardar la decisión.

Quien escribe es el backend, no el micro. El micro sigue siendo de sólo lectura
y sin base de datos, tal como quedó en `SEGURIDAD.md`.

La tabla `intel_decisiones` guarda `id`, `restaurante_id`, `sucursal_id`,
`huella` (indexada), `origen` (checkout o laboratorio), `canasta` en jsonb con
puros IDs, `modo`, `version_modelo`, `sugerencias` en jsonb, `explicacion` en
jsonb (nula en checkout), `latencia_ms` y `creado_en`.

Sin PII: no se guarda teléfono, dirección, nombre ni el `pedido_id` del cliente.
Retención de 30 días con un cron de limpieza. RLS para service role y
superadmin.

Con eso, el laboratorio muestra un panel de últimas decisiones reales del
checkout. Armo el carrito en el celular, refresco el CRM, ahí aparece, le doy a
Reproducir y recalcula desde cero:

```
Huella:  7f3a9c2e1b4d8a60
Del checkout, hace 2 min    →  Gyoza, Té helado, Edamame
Recalculado ahora en el lab →  Gyoza, Té helado, Edamame
Coinciden
```

Ese cuadro es lo que le enseño a la maestra. No es captura ni promesa: es el
mismo hash recalculado enfrente de ella.

## Qué lleva la página

Arriba, el selector de sucursal y un badge con el estado del micro: versión,
latencia del último cálculo, si la caché está caliente.

Luego el simulador, que es lo principal: buscador de productos del menú real,
armas la canasta, botón de calcular.

El resultado muestra, por cada sugerencia, nombre, precio, imagen, soporte,
confianza, lift, score final y qué estrategia la propuso. Y abajo los
descartados con su motivo: "lift 0.83, por debajo de 1", "ya está en la
canasta", "inactivo en esta sucursal", "recortado por diversidad de categoría".
Eso es lo que convierte la caja negra en algo que puedo defender.

Después la traza del pipeline, con cuántos candidatos entraron y salieron de
cada etapa, y la clase y el archivo que la implementan:

```
filtrar_inactivos        18 → 15   CandidatoFiltro    domain/scoring/combinadores.py
penalizar_repetidos      15 → 15   Penalizador        domain/scoring/combinadores.py
escalar(1.0)             15 → 15   Escalador          domain/scoring/combinadores.py
diversificar(max 2/cat)  15 →  7   Diversificador     domain/scoring/combinadores.py
top_n(3)                  7 →  3   PipelineScoring    domain/scoring/pipeline.py
```

Esto responde directo a que necesito saber explicar el código. La pantalla me lo
va recordando.

El comparador de estrategias pone cuatro columnas lado a lado: auto, manual,
híbrido y popularidad. Mismo carrito, resultados distintos. Ahí explico
polimorfismo señalando la pantalla.

Las gráficas son tres: pronóstico de pedidos por hora contra lo real de la
semana pasada con su MAE, dispersión de margen contra popularidad con los cuatro
cuadrantes, y la serie de ventas con bandas de tres sigma y las anomalías
marcadas. Todo con Recharts, que ya está en el frontend. Ojo con poner
`height="100%"` dentro de un `motion.div`: eso fue lo que provocó el React #185
en la landing.

Y al final la caja de cálculo lambda. Escribes un término y ves la secuencia de
reducciones, cada paso etiquetado como alfa, beta o eta, con botones de ejemplos
cargados: I, K, S, numerales de Church y el pipeline de scoring real expresado
como composición. Es la Unidad 3, demostrable en diez segundos, en producción.

## Seguridad del laboratorio

Es superficie nueva en el CRM, así que hereda sus controles y suma los suyos.

La ruta va bajo `/admin`, que ya exige sesión de superadmin, y la validación se
hace en el servidor en cada endpoint, no escondiendo el enlace. El
`restaurante_id` se toma de la sesión y del path, nunca del cuerpo de la
petición, para que el laboratorio no pueda pedir datos de otro restaurante. El
micro sigue sin exposición pública: el laboratorio pega al backend y el backend
al micro.

El simulador no crea pedidos, no toca saldo, no manda WhatsApp y no escribe en
el menú. Sólo lee y calcula. Tiene rate limit propio porque el cálculo cuesta
más que una lectura normal. La tabla de decisiones guarda IDs y números, nada de
cliente. Y el endpoint de reproducción valida que la decisión pertenezca al
restaurante de la ruta antes de devolverla.

## Reparto por unidad

Cada unidad entrega algo que se puede enseñar ese mismo día, sin que el resto
exista todavía. Si la Unidad 1 sólo se pudiera demostrar cuando todo esté armado
en diciembre, no me sirve como evidencia en septiembre.

**Unidad 1**, rama `unidad-1`, tag `v0.1-u1`. El dominio en Python: value
objects, entidades, agregado, encapsulación con copias defensivas. Sin red, sin
FastAPI. La demo es `python -m demos.u1`: carga un volcado real de pedidos, arma
los objetos, imprime totales por sucursal, y al final intenta mutar las líneas
de un pedido y truena. Entrego diagrama de clases, tests verdes y la sección 1
del PDF.

**Unidad 2**, rama `unidad-2`, tag `v0.2-u2`. Las jerarquías abstractas con sus
subclases, las colecciones y el top-N. La demo es
`python -m demos.u2 --modo auto|manual|hibrido`: mismos datos, tres salidas, una
sola línea de código llamador. Entrego diagrama, tests y sección 2.

**Unidad 3**, rama `unidad-3`, tag `v0.3-u3`. El intérprete de lambda y el
pipeline de scoring. La demo es `python -m demos.u3`, que abre el REPL donde
reduzco I, K, S y numerales de Church viendo cada paso etiquetado. Entrego
diagrama, tests de reducción y la sección 3 con la parte matemática.

**Unidad 4**, rama `unidad-4`, tag `v1.0`. Infraestructura, endpoint
despersonalizado, tabla de decisiones, laboratorio, integración con el checkout,
Docker y despliegue. La demo es la completa, en producción, con el cuadro de
huella. Entrego todo lo anterior más el PDF y el repo con sus cuatro tags.

## Orden de construcción

No es el orden de las unidades. Para que la Unidad 1 se pueda demostrar con
datos reales, primero hay que poder sacarlos.

1. Endpoint `/api/internal/intel/ventas` en el backend, despersonalizado, y un
   script que vuelque un CSV anónimo para desarrollo local.
2. Unidad 1: dominio y demo.
3. Unidad 2: estrategias y demo.
4. Unidad 3: lambda y scoring.
5. Infraestructura del micro y su API.
6. Tabla `intel_decisiones` y escritura desde el backend.
7. Laboratorio en el CRM.
8. Integración con el checkout detrás del feature flag.
9. Docker y despliegue.
10. Documento y diagramas finales.

Del 1 al 4 no se toca producción. El riesgo empieza en el 6.

# Guía para exponer y para defender

Dos partes. La primera es el guion de la demo. La segunda es lo que tengo que
poder contestar sin dudar, porque si no lo entiendo no lo puedo defender.

---

# Parte 1. El guion, en diez minutos

## Antes de empezar

Tener abiertas cuatro pestañas y una terminal:

1. El menú público de Sushi Soru en el celular.
2. El CRM en `/admin/clientes/<id>/inteligencia`.
3. GitHub, en la vista de ramas del repo.
4. El PDF.
5. Terminal en la carpeta del microservicio.

Y el video de respaldo grabado. Si falla el wifi del salón, se enseña el video.

## Minuto 0 a 1: el problema, sin tecnicismos

> "cEats ya sugiere productos en el checkout. El problema es cómo los escoge:
> cuenta cuántas veces dos productos salieron juntos en el mismo pedido. Con
> eso, el refresco gana siempre, porque el refresco sale con todo. No porque el
> cliente haya pedido ramen, sino porque casi todos piden refresco."

Enseñar la tabla del demo de la Unidad 2:

```
producto              juntos   sop(B)     conf    lift
Gyoza 6 pz                50    0.385    0.769   2.000
Refresco                  50    0.846    0.835   0.987
```

> "Los dos acompañaron al ramen exactamente 50 veces. Contar los deja
> empatados. Pero el refresco aparece en el 85% de todos los pedidos y la gyoza
> en el 38%. Al dividir entre eso, la gyoza da 2.00 y el refresco 0.99."

Es el momento más importante de la exposición. Si eso queda claro, lo demás se
entiende solo.

## Minuto 1 a 3: funciona en producción

Armar un carrito real en el celular. Sale el interstitial de upsell.

> "Esto es producción, con un restaurante real y un cliente real."

## Minuto 3 a 5: no es una caja negra

Ir al CRM, pestaña Inteligencia. Escoger la misma sucursal y el mismo platillo.

> "Aquí escojo cualquier platillo del menú, sin necesidad de que exista un
> pedido, y veo exactamente lo que vería el cliente."

Enseñar tres cosas de la pantalla:

1. **La evidencia.** Soporte, confianza, lift y la etiqueta de confianza
   estadística de cada sugerencia.
2. **Los descartados con su motivo.** "lift 0.83, por debajo de 1", "ya está en
   la canasta", "recortado por diversidad de categoría".
3. **La traza del pipeline.** Cuántos candidatos entraron y salieron de cada
   etapa, con la clase y el archivo que la implementa.

Después el panel de decisiones reales: darle a Reproducir en la del carrito que
acabo de hacer.

```
Huella: 7f3a9c2e1b4d8a60
Del checkout          ->  Gyoza, Té helado, Edamame
Recalculado ahora     ->  Gyoza, Té helado, Edamame
Coinciden
```

> "Es el mismo hash, recalculado enfrente de usted. No es una captura."

## Minuto 5 a 7: el POO, señalando la pantalla

El comparador de estrategias: cuatro columnas, misma canasta, resultados
distintos.

> "El código que llama es una sola línea, la misma en las cuatro columnas:
>
>     estrategia = fabrica.crear(modo, reglas, objetivo=3)
>     sugerencias = estrategia.puntuar(ctx, limite=3)
>
> Nunca pregunto de qué tipo es. Detrás puede haber una co-ocurrencia sola, un
> composite con reglas manuales encima, o una cascada de siete escalones."

Enseñar el diagrama de la Unidad 2 en el PDF, con la clase abstracta arriba y
las siete subclases colgando.

## Minuto 7 a 8: el cálculo lambda

La caja de lambda en el CRM.

> "Escribo la suma de Church de 2 más 3."

Sale la secuencia de pasos, cada uno etiquetado como alfa, beta o eta, y el
resultado es el numeral 5.

Después Omega:

> "Este término se reduce a sí mismo para siempre. El evaluador corta a diez mil
> pasos. Sin eso, cualquiera tumba el servicio con doce caracteres."

Y cerrar con la conexión al negocio:

> "Esto no es un adorno. El puntaje del upsell se calcula componiendo funciones
> puras, que es la misma reducción beta aplicada al problema. Y de que sean
> puras depende que el checkout y este laboratorio den lo mismo."

## Minuto 8 a 10: el proceso

En la terminal:

```bash
pytest                       # 157 pruebas verdes
git log --graph --oneline    # la historia
git tag                      # v0.1-u1, v0.2-u2, v0.3-u3, v1.0
```

> "Cada unidad cerró en su rama con su tag. Si quiere ver qué entregué en la
> unidad dos, `git checkout v0.2-u2` y ahí está, congelado."

Y el cierre honesto:

> "Lo que más me sirvió fue un bug que encontré corriendo la demo, no
> escribiendo pruebas. Está en la bitácora."

---

# Parte 2. Lo que tengo que dominar

## Las diez preguntas que me va a hacer

### 1. ¿Por qué lift y no nada más contar?

Contar mide cuántas veces salieron juntos. El lift mide cuánto sube la
probabilidad de B **porque** pidieron A, comparada con la probabilidad de B a
secas.

```
soporte(B)      = n(B) / N
confianza(A→B)  = n(A∩B) / n(A)
lift(A→B)       = confianza(A→B) / soporte(B)
```

Lift 1 es indiferencia: B sale igual de seguido lleve A o no. Arriba de 1 hay
atracción, abajo hay rechazo.

Ejemplo concreto: el refresco acompaña al ramen 50 de 60 veces, o sea confianza
0.83. Suena altísimo. Pero el refresco sale en el 85% de todos los pedidos, así
que 0.83 es incluso un poco menos de lo normal. Lift 0.99.

### 2. ¿Qué pasa con un restaurante que casi no tiene pedidos?

Dos cosas.

Primero, el suavizado. En vez de un mínimo duro, la confianza se estima así:

```
conf_α(A→B) = ( n(A∩B) + α · soporte(B) ) / ( n(A) + α )
```

con α de unos 10 pedidos. Con poca evidencia sobre A, el resultado se apoya en
qué tan popular es B en general; conforme A junta pedidos, α pesa menos y
converge al valor real. Es un estimador m. La gracia es que no hay salto entre
"sin datos" y "con datos".

Caso bonito: si n(A) = 0, la fórmula da exactamente soporte(B), y entonces el
lift es 1. Sin evidencia, la respuesta honesta es "no sé", no "sí".

Segundo, la cascada de siete escalones. Baja de nivel hasta encontrar algo: de
la sucursal al restaurante, luego ventana larga, luego afinidad por categoría,
luego más vendidos, y al final productos destacados. Nunca devuelve una franja
vacía.

### 3. ¿Cómo sabe qué es una bebida y qué un plato fuerte? ¿Es inteligencia artificial?

No, y es a propósito. Las categorías en cEats son texto libre, cada restaurante
escribe lo que quiere. El tipo se deduce en tres pasos, de más confiable a
menos:

1. Lo que el superadmin confirmó en el CRM. Dato duro.
2. El precio relativo a la mediana del menú. Lo barato acompaña a lo caro.
3. Un diccionario de palabras, como último recurso.

Por qué no un modelo entrenado: con cuarenta pedidos, un modelo es peor que una
regla, y además tengo que poder explicarle al restaurantero por qué le sugerimos
lo que le sugerimos. Un lift se defiende en dos frases; un clasificador
entrenado con cuarenta filas, no.

### 4. ¿Dónde está el polimorfismo?

En `EstrategiaRecomendacion`, que es abstracta. Tiene tres métodos abstractos
(`candidatos`, `origen`, `nivel`) y uno concreto, `puntuar`, que es método
plantilla: aplica el peso, quita lo que el cliente ya trae, quita los
descartados y recorta al top-N. Las subclases sólo dicen cómo puntuar.

Siete subclases: co-ocurrencia, afinidad por categoría, popularidad, reglas
manuales, destacados, y dos compuestas (híbrida y cascada). Las compuestas
heredan de la misma abstracta, así que se pueden pasar donde iba una hoja y
nadie se entera. Eso es el patrón Composite.

El caso de uso nunca pregunta el tipo: `fabrica.crear(modo)` devuelve el tipo
abstracto y se le llama `puntuar`.

### 5. ¿Dónde está la encapsulación?

Todos los atributos son privados por convención (`_atributo`) y con `__slots__`.
Pero lo importante es la copia defensiva: `Pedido` recibe una lista de líneas y
guarda una **tupla**. Si guardara la lista, quien la pasó conserva una
referencia al estado interno y puede mutarlo por fuera sin pasar por ningún
método. Hay dos pruebas para eso, y la demo de la Unidad 1 lo enseña tronando en
vivo.

### 6. ¿Qué es la conversión alfa y por qué la necesitas?

Renombrar la variable ligada. `λx.x` y `λy.y` son el mismo término.

Se necesita para evitar **captura de variable**. Si sustituyo `y` por `x` en
`λx. y`, el resultado no puede ser `λx. x`: la `x` que entró era libre y quedaría
atrapada por el lambda, cambiando de significado. Antes de sustituir hay que
renombrar el parámetro.

En mi código eso lo hace `Abs.sustituir`, que revisa si el parámetro aparece
libre en lo que voy a meter y si sí, genera un nombre fresco.

### 7. ¿Cómo compara dos términos?

Con índices de De Bruijn. Cada variable ligada se escribe como la distancia al
lambda que la liga: en `λx. x` la x es `#0`; en `λx. λy. x` la x es `#1`. Las
libres conservan su nombre, porque ésas sí forman parte del significado.

Así, `λx.x` y `λy.y` tienen la misma forma canónica `(\. #0)` y salen iguales.

Esto no lo diseñé: salió de una prueba en rojo. Yo comparaba por texto y la
prueba de conversión alfa falló. La prueba tenía razón.

### 8. ¿Por qué orden normal y no llamada por valor?

Orden normal reduce siempre el redex de más a la izquierda y más afuera.
Propiedad clave: si el término tiene forma normal, el orden normal la encuentra.
Con llamada por valor hay términos que se cuelgan aunque la respuesta exista.

Ejemplo: `(λx y. x) a ((λx. x) b)` da `a`, aunque el segundo argumento nunca se
use. Llamada por valor lo evaluaría primero sin necesidad.

### 9. ¿Qué patrones usaste y por qué?

- **Strategy**: `EstrategiaRecomendacion`, `ModeloPronostico`. Intercambiar el
  algoritmo sin tocar el caso de uso.
- **Composite**: `HibridaStrategy`, `CascadaStrategy`. Tratar un grupo igual que
  una pieza suelta.
- **Template Method**: `puntuar` y `entrenar`. Lo común arriba, lo propio abajo.
- **Factory Method**: `FabricaEstrategias`. Del modo configurado al objeto.
- **Repository / Puerto y adaptador**: el dominio declara `RepositorioVentas`,
  la infraestructura lo implementa con HTTP. Por eso el dominio no importa httpx.
- **Decorator**: `RepositorioCacheado` y el circuit breaker. Agregan caché y
  tolerancia a fallos sin modificar el adaptador.
- **Parameter Object**: `ContextoRecomendacion`. Empecé pasando historial y
  canasta sueltos y cuando entró la cascada la firma se volvió impresentable.

### 10. ¿Cómo garantizas que el laboratorio y el menú público den lo mismo?

Cuatro cosas, y hay una prueba que las vigila.

1. **Una sola ruta de código.** El laboratorio llama el mismo caso de uso que el
   checkout. Lo único que cambia es la bandera `explicar`, que agrega detalle
   pero no toca la lista.
2. **La ventana se corta a medianoche.** Si pidiera "últimos 90 días" al
   instante exacto, dos consultas del mismo día verían pedidos distintos.
3. **Desempate determinista.** Orden por `(score desc, producto_id asc)`, con el
   score redondeado a seis decimales. Nunca dependo del orden de iteración de un
   diccionario.
4. **Huella.** Un hash de sucursal, canasta ordenada, modo, versión de config,
   ventana, versión del modelo y límite. Misma huella, mismo resultado.

La prueba genera 200 canastas al azar y las pide por los dos caminos; falla si
alguna difiere en contenido u orden.

---

## Los dos bugs que debo contar

Contar errores propios da más credibilidad que presumir aciertos, y además a mí
me sirven para explicar el diseño.

### El de las bandas

En modo automático, con ramen en el carrito, sugería refresco por afinidad de
categoría en vez de la gyoza que tenía lift 2.0.

Causa: la afinidad puntúa 3.0 (por ser bebida, el tipo que mejor acompaña a un
fuerte) y el lift puntúa 2.0. Comparados a pelo, gana el 3. El error de fondo es
que los puntajes de escalones distintos no miden lo mismo y no se pueden
comparar.

Solución: cada escalón tiene su banda de cien puntos, el de arriba siempre gana
al de abajo, y dentro de la banda el puntaje original sigue ordenando.

Lo importante: ninguna prueba unitaria lo habría encontrado, porque cada pieza
estaba bien por separado. Salió corriendo la demo.

### El de la igualdad de términos

Ya está arriba, en la pregunta 7.

---

## Números que debo traer memorizados

- 157 pruebas, todas verdes.
- Cuatro ramas con cuatro tags, una por unidad.
- Siete escalones en la cascada.
- α igual a 10 pedidos en el suavizado.
- Ventana de 90 días, cortada a medianoche.
- Timeout de 2 segundos y caída al resolutor anterior.
- El micro no se publica a internet y no recibe ningún dato personal.

## Lo que NO debo decir

- No decir "inteligencia artificial". Esto es estadística de canasta y reglas.
  Si me preguntan por qué no IA, ya tengo la respuesta de la pregunta 3.
- No decir que es perfecto. Las limitaciones están en la bitácora: el costo de
  insumos está fijo en 35%, el detector de anomalías se tapa con sus propios
  outliers, el diccionario de categorías está pensado para menús mexicanos.
  Decirlas de frente se ve mejor que si las descubre ella.
- No prometer que la demo en vivo va a jalar. Tener el video.

## Si algo falla en vivo

- Si el micro no responde: es la oportunidad perfecta. Enseñar que el checkout
  sigue funcionando con el resolutor anterior. Eso es diseño, no suerte.
- Si el wifi falla: el video, y `pytest` en local, que no necesita red.
- Si pregunta algo que no sé: "no lo verifiqué, lo reviso y le confirmo". Es
  mejor que inventar y quedar en evidencia en la siguiente pregunta.

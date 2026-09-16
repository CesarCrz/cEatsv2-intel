# Bitácora

Lo que me fui encontrando mientras construía esto. Incluye lo que no funcionó,
que suele ser lo más útil de releer.

---

## 14 de septiembre

**Por qué un servicio aparte y no una función más en el backend.**
Lo primero que pensé fue meter el cálculo en `upsell.service.ts` y ya. El
problema es que ahí no se puede probar nada sin levantar Next.js entero y pegarle
a Supabase. Separándolo, el dominio corre con `pytest` en menos de un segundo y
sin red. El costo es una llamada HTTP más que puede fallar, y eso se paga con el
fallback al resolver viejo.

**Centavos y no pesos.**
Arranqué con `float` para los precios. Escribí la prueba que suma mil líneas de
$19.99 y no daba $19,990.00. Cambié a centavos enteros. Es la clase de error que
no se ve hasta que alguien compara el reporte del mes con lo que dice la app.

**Los IDs como tipos separados.**
Al principio eran `str`. Me equivoqué una vez pasando una sucursal donde iba un
producto y el resultado fue una lista vacía, sin error. Media hora buscándolo.
Con tipos separados truena al construir.

**El corte de la ventana a medianoche.**
Esto no lo tenía pensado y salió al escribir el plan del laboratorio. Si el
checkout pide "últimos 90 días" a las 14:03 y yo abro el CRM a las 14:07, son
ventanas distintas. Basta un pedido nuevo en medio para que dos candidatos
empatados se inviertan y la demo se caiga justo enfrente de la maestra. La
ventana se corta al día y listo.

---

## 16 de septiembre

**El lift, y por qué no bastaba contar.**
El resolver actual cuenta cuántas veces salieron juntos dos productos. Con los
datos de prueba, gyoza y refresco salen 50 veces junto al ramen: empate. Pero el
refresco sale en el 85% de todos los pedidos y la gyoza en el 38%. El lift da
2.00 para la gyoza y 0.99 para el refresco. Ahí se ve que contar no distingue
entre "acompaña al ramen" y "lo piden todos".

**Primer intento del poco volumen: un mínimo duro. No sirvió.**
Puse "si el producto no aparece en al menos 20 pedidos, no lo considero". El
resultado fue que los restaurantes chicos se quedaban sin ninguna sugerencia, y
son justo los que más la necesitan. Además había un salto feo: con 19 pedidos
nada, con 20 de golpe todo.

Lo cambié por suavizado. La confianza se jala hacia la popularidad del candidato
con un α de 10 pedidos, y conforme hay más datos converge sola al valor real.
Sin salto. Me gustó que además cae en el caso bonito: si el ancla nunca se ha
vendido, la fórmula da exactamente el soporte y el lift queda en 1, que es la
respuesta honesta.

**Segundo intento: promediar el lift sobre toda la canasta. Tampoco.**
Si el cliente trae cinco cosas, promediar castiga al acompañante perfecto de una
sola de ellas, que es justo el que le quiero ofrecer. Me quedé con el máximo.

**El bug de las bandas.** Este salió corriendo la demo de la Unidad 2, no
escribiendo pruebas.

En modo `auto`, con un ramen en el carrito, el sistema sugería refresco por
afinidad de categoría en vez de la gyoza que tenía lift 2.0. Tardé en verlo:
la afinidad puntúa 3.0 (por ser bebida, que es lo que mejor acompaña a un
fuerte) y el lift puntúa 2.0. Comparados a pelo, gana el 3.

El error de fondo es que los scores de escalones distintos no significan lo
mismo y no se pueden comparar. Cada escalón se quedó con su banda de cien
puntos, y adentro de la banda el score original sigue mandando. Le dejé prueba
de regresión.

Me sirve de anécdota para la exposición: es el tipo de bug que no encuentra una
prueba unitaria, porque cada pieza estaba bien por separado.

**La igualdad de términos lambda.**
Tenía `__eq__` comparando `str(self)`. La prueba de conversión alfa se puso roja:
`\x. x` y `\y. y` salían distintos. Pero son el mismo término, eso es
exactamente lo que dice la conversión alfa. Lo resolví con índices de De Bruijn:
cada variable ligada se escribe como la distancia al lambda que la liga, y el
nombre desaparece. La prueba tenía razón y el código no.

**Escapar backslashes dentro de f-strings.**
Media hora perdida con `parsear(r'\\x. x')` dentro de un f-string, que da dos
backslashes y el parser no lo entiende. Lo saqué del f-string y ya.

**El endpoint del backend incluía el día de `hasta`.**
Le sumaba 24 horas al límite. Eso mata el corte a medianoche: cada pedido que
entrara durante la tarde cambiaría el resultado y el laboratorio dejaría de
coincidir con el menú público. Lo dejé exclusivo y escribí el porqué en el
comentario, porque es la clase de línea que alguien "arregla" después sin saber
qué rompe.

**Paginación inestable en `pedido_items`.**
Se paginaba con `.range()` ordenando por `created_at`, y esa columna empata
entre renglones del mismo pedido. Con empates, el corte entre páginas puede
repetir o saltarse renglones, y un renglón de más mueve los conteos de
co-ocurrencia. No hay columna que dé un orden total confiable, así que quité la
paginación y traigo cada lote de un jalón con un tope.

---

## Pendientes y cosas que no me convencen

- El costo de insumos en menu engineering está fijo en 35% para todos los
  productos. Es una simplificación grande y hay que decirla. Se arregla cuando
  el restaurante capture costos reales en el CRM.
- El detector de anomalías usa media y desviación, y los outliers inflan la
  desviación y se tapan solos. Con series cortas es aceptable. Si empieza a
  fallar, el reemplazo es la mediana absoluta de desviaciones.
- El diccionario de palabras para clasificar categorías está pensado para menús
  mexicanos. Con un menú en otro idioma se cae al precio relativo, que funciona
  pero es menos preciso.
- La caché es por proceso. Si algún día hay más de un worker, dos peticiones
  iguales pueden pegarle dos veces al backend. No rompe nada, sólo gasta.

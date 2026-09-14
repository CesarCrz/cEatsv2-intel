# Seguridad de cEatsv2-intel

Esto se enchufa a una plataforma que ya está en producción y que maneja pagos,
datos de clientes y CLABEs. La regla con la que diseñé todo es simple: si
alguien se apodera por completo de este servicio, no debe sacar nada que
importe.

La forma de lograrlo no es blindar el servicio. Es no darle nada que valga la
pena robar.

## La idea de fondo

El micro recibe números y devuelve números. Nunca sabe de quién son.

## Controles

### Sin exposición pública

El contenedor no se publica en el proxy. No tiene dominio, no tiene regla en
Traefik y no mapea puertos al host. Sólo se alcanza por el nombre de servicio
dentro de la red de Docker, `http://ceatsv2-intel:8000`, y el único que lo llama
es el backend.

Para verificarlo: desde fuera del VPS, ningún puerto del servicio debe
responder.

### Quién llama a quién

El backend le pide cálculos al micro (`POST /v1/recomendaciones`). El micro le
pide datos al backend (`GET /api/internal/intel/*`). Eso es todo. El frontend no
lo toca, WhatsApp no lo toca, internet no lo toca.

### Autenticación de entrada

Cada petición al micro trae `X-Intel-Key`, y la comparación es en tiempo
constante con `hmac.compare_digest`. Si la variable de entorno no está puesta,
el servicio rechaza todo en lugar de abrirse. Es el mismo criterio que ya usa
`app/api/internal/sucursales/ws-status/route.ts` del backend.

### Clave separada para salir

El micro usa `INTEL_SERVICE_KEY`, que no es `API_SECRET_KEY`. La razón es
práctica: si esa clave se filtra, sólo abre los endpoints de lectura de
inteligencia, y la roto sin tocar los crons ni los otros microservicios.

Del lado del backend, `/api/internal/intel/*` la valida con
`crypto.timingSafeEqual`, igual que los crons que ya existen.

### Despersonalización en el origen

Este es el control que más me importa. El endpoint `/api/internal/intel/ventas`
devuelve solamente `pedido_id`, `sucursal_id`, `producto_id`, `cantidad`,
`precio_unitario` y `creado_en`.

Nada de teléfono, nombre, dirección, correo, notas del cliente, CLABE,
beneficiario, datos de Stripe o tokens de sesión. Si el micro cae, no hay PII
que exfiltrar porque nunca la tuvo.

Ya me pasó una fuga de CLABE y tarifas por el menú público en septiembre. La
lección fue proyectar columnas de forma explícita y jamás hacer `select *`. Aquí
va aplicada desde el primer día.

### Sólo lectura

El micro no tiene credenciales de Supabase, no usa la service role y no llama
ningún `POST`, `PUT` ni `DELETE` del backend. El backend debe rechazar esos
métodos bajo `/api/internal/intel/*`.

### Sin nada guardado

Sin base de datos propia, sin volúmenes. La caché vive en memoria con TTL corto
y se pierde al reiniciar. No hay disco que robar.

### El contenedor

Imagen `python:3.12-slim` en dos etapas, usuario no-root, sistema de archivos
raíz de sólo lectura con un `tmpfs` para `/tmp`, `cap_drop: ALL` y
`no-new-privileges`. Los secretos llegan por variables de entorno de EasyPanel,
nunca horneados en la imagen. El healthcheck pega a `/healthz`, que no pide
autenticación y no revela nada.

### Validación de entrada

Todo se valida con Pydantic: UUIDs con formato estricto, tope al tamaño de la
canasta, `limite` acotado entre 1 y 10, rango de fechas acotado. Los cuerpos que
pasan del límite se rechazan con 413 antes de parsear.

### Qué pasa cuando falla

Timeout de 2 segundos en el cliente HTTP y circuit breaker. Rate limit propio
por clave. Y lo importante: si el micro tarda o se cae, el backend se va al
resolver de siempre, `lib/services/upsell.service.ts`. El checkout no se rompe
por culpa de este servicio.

### Nada de ejecución dinámica

El intérprete de lambda de la Unidad 3 trabaja sobre un AST propio. No hay
`eval`, no hay `exec`, no hay `pickle` ni deserialización de código. El
evaluador corta a `MAX_PASOS` reducciones para no colgarse con términos que no
tienen forma normal.

### Logs

Sin PII, sin claves, sin cuerpos completos. IDs, conteos y tiempos. El manejador
de errores nunca devuelve trazas al cliente.

## Antes de desplegar

- [ ] El servicio no tiene dominio ni puerto publicado en EasyPanel.
- [ ] `INTEL_SERVICE_KEY` generada con 32 bytes aleatorios y distinta de `API_SECRET_KEY`.
- [ ] `INTEL_INBOUND_KEY` generada aparte y cargada en el backend.
- [ ] `/api/internal/intel/ventas` responde 401 sin cabecera y 405 a los métodos de escritura.
- [ ] Revisar a mano el JSON de ese endpoint y confirmar que no trae ningún campo de cliente.
- [ ] El contenedor corre como no-root y con el rootfs de sólo lectura.
- [ ] Apagar el micro y comprobar que el checkout sigue funcionando con el resolver viejo.
- [ ] Ninguna clave quedó en el repo: `.env` ignorado, `.env.example` sin valores.

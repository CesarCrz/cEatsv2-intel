# syntax=docker/dockerfile:1

# Etapa de build: instala dependencias en un venv aislado para no arrastrar
# compiladores ni cache de pip a la imagen final.
FROM python:3.12-slim AS build

WORKDIR /build
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir ".[api]"

# Etapa de runtime: solo el venv ya armado y el codigo fuente. Nada de
# herramientas de compilacion, nada de secretos horneados en la imagen (llegan
# por variables de entorno de EasyPanel, ver .env.example).
FROM python:3.12-slim AS runtime

RUN groupadd --system ceats \
    && useradd --system --gid ceats --home-dir /app --no-create-home ceats

WORKDIR /app
COPY --from=build /venv /venv
COPY src ./src
COPY pyproject.toml README.md ./

ENV PATH="/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER ceats

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)" || exit 1

# Un solo worker, a proposito. La cache de RepositorioCacheado (ver
# infrastructure/cache.py) vive en memoria de proceso: con mas de un worker
# cada uno tendria su propia cache y el TTL efectivo se volveria
# impredecible entre peticiones que caen en workers distintos. Si algun dia
# hace falta escalar horizontalmente, la cache tiene que salir del proceso
# (Redis u otro almacen compartido) antes de subir --workers.
CMD ["uvicorn", "ceats_intel.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

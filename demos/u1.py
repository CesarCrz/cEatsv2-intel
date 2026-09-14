"""Demo de la Unidad 1: clases, encapsulamiento y referencias.

Se corre asi:

    python -m demos.u1                      # con datos de ejemplo
    python -m demos.u1 --csv datos/ventas.csv   # con un volcado real

El CSV es el que produce `scripts/volcar-ventas-intel.mjs` del backend, con
columnas pedido_id, producto_id, cantidad, precio_unitario, creado_en.

La ultima parte es la que me interesa ensenar: intentar romper el pedido desde
fuera y ver que no se deja.
"""

from __future__ import annotations

import argparse
import csv
import random
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ceats_intel.domain.entidades import HistorialVentas, LineaPedido, Pedido
from ceats_intel.domain.valueobjects import Dinero, ProductoId, SucursalId, VentanaTemporal

SUCURSAL = SucursalId("00000000-0000-4000-8000-000000000001")

# Menu inventado para cuando no hay CSV a la mano. Los precios son realistas
# porque el punto de la demo es que los totales se vean creibles.
MENU_EJEMPLO = [
    ("Yakimeshi Crispy", 189.0),
    ("Ramen Tonkotsu", 215.0),
    ("Gyoza (6 pz)", 95.0),
    ("Edamame", 65.0),
    ("Te helado", 45.0),
    ("Refresco", 35.0),
    ("Mochi de matcha", 70.0),
]


def _uuid(n: int) -> str:
    return f"00000000-0000-4000-8000-{n:012d}"


def generar_pedidos(cuantos: int = 400) -> tuple[list[Pedido], dict[ProductoId, str]]:
    """Pedidos sinteticos con algo de estructura, no ruido puro.

    Meto a proposito dos sesgos: el refresco sale en casi todo (para que se vea
    el problema que motiva el lift) y la gyoza acompana al ramen mas de lo
    normal (para que haya al menos una co-ocurrencia con sentido).
    """
    azar = random.Random(42)
    nombres = {ProductoId(_uuid(i + 1)): nombre for i, (nombre, _) in enumerate(MENU_EJEMPLO)}
    precios = {ProductoId(_uuid(i + 1)): p for i, (_, p) in enumerate(MENU_EJEMPLO)}
    fuertes = [ProductoId(_uuid(1)), ProductoId(_uuid(2))]
    gyoza, edamame = ProductoId(_uuid(3)), ProductoId(_uuid(4))
    te, refresco, mochi = ProductoId(_uuid(5)), ProductoId(_uuid(6)), ProductoId(_uuid(7))

    pedidos: list[Pedido] = []
    arranque = datetime(2026, 6, 16, tzinfo=UTC)

    for n in range(cuantos):
        elegidos: list[ProductoId] = [azar.choice(fuertes)]
        if elegidos[0] == fuertes[1] and azar.random() < 0.55 or azar.random() < 0.18:
            elegidos.append(gyoza)
        if azar.random() < 0.20:
            elegidos.append(edamame)
        if azar.random() < 0.72:
            elegidos.append(azar.choice([refresco, refresco, te]))
        if azar.random() < 0.12:
            elegidos.append(mochi)

        momento = arranque + timedelta(
            days=azar.randint(0, 89),
            hours=azar.choice([13, 14, 14, 19, 20, 20, 21]),
            minutes=azar.randint(0, 59),
        )
        pedidos.append(
            Pedido(
                id_=f"demo-{n:04d}",
                sucursal_id=SUCURSAL,
                creado_en=momento,
                lineas=[
                    LineaPedido(p, azar.randint(1, 2), Dinero.desde_pesos(precios[p]))
                    for p in dict.fromkeys(elegidos)
                ],
            )
        )
    return pedidos, nombres


def leer_csv(ruta: Path) -> tuple[list[Pedido], dict[ProductoId, str]]:
    agrupados: dict[str, list[LineaPedido]] = defaultdict(list)
    fechas: dict[str, datetime] = {}
    with ruta.open(encoding="utf-8", newline="") as f:
        for fila in csv.DictReader(f):
            pedido_id = fila["pedido_id"]
            agrupados[pedido_id].append(
                LineaPedido(
                    ProductoId(fila["producto_id"]),
                    int(fila["cantidad"]),
                    Dinero.desde_pesos(fila["precio_unitario"]),
                )
            )
            fechas[pedido_id] = datetime.fromisoformat(fila["creado_en"])
    pedidos = [Pedido(pid, SUCURSAL, fechas[pid], lineas) for pid, lineas in agrupados.items()]
    return pedidos, {}


def titulo(texto: str) -> None:
    print(f"\n{texto}")
    print("-" * len(texto))


def main() -> None:
    parser = argparse.ArgumentParser(description="Demo de la Unidad 1")
    parser.add_argument("--csv", type=Path, help="volcado de ventas real")
    args = parser.parse_args()

    if args.csv:
        pedidos, nombres = leer_csv(args.csv)
        print(f"Cargados {len(pedidos)} pedidos desde {args.csv}")
    else:
        pedidos, nombres = generar_pedidos()
        print(f"Generados {len(pedidos)} pedidos de ejemplo (sin CSV)")

    historial = HistorialVentas(
        SUCURSAL,
        VentanaTemporal.ultimos_dias(90, hoy=datetime(2026, 9, 14, tzinfo=UTC).date()),
        pedidos,
    )

    titulo("1. Los objetos se arman y saben calcular lo suyo")
    primero = historial.pedidos[0]
    print(f"Pedido {primero.id}, {len(primero.lineas)} lineas, total {primero.total()}")
    for linea in primero.lineas:
        etiqueta = nombres.get(linea.producto_id, str(linea.producto_id)[:8])
        print(f"   {linea.cantidad} x {etiqueta:<20} {linea.subtotal()}")

    facturado = Dinero.cero()
    for p in historial.pedidos:
        facturado = facturado.mas(p.total())
    print(f"\nVentana {historial.ventana.clave()}")
    print(f"Pedidos {historial.total_pedidos}, facturado {facturado}")

    titulo("2. El agregado responde por sus conteos")
    for producto in sorted(historial.productos_vistos(), key=historial.frecuencia, reverse=True):
        etiqueta = nombres.get(producto, str(producto)[:8])
        print(
            f"   {etiqueta:<20} en {historial.frecuencia(producto):>4} pedidos "
            f"(soporte {historial.soporte(producto):.0%}), "
            f"{historial.unidades(producto):>4} piezas"
        )

    titulo("3. Por que hace falta el lift (el problema del refresco)")
    ramen = next((p for p, n in nombres.items() if n.startswith("Ramen")), None)
    if ramen is not None:
        acompana = historial.acompanantes(ramen)
        print(f"Lo que mas sale junto al {nombres[ramen]}, contando nada mas:")
        for producto, veces in sorted(acompana.items(), key=lambda x: -x[1])[:3]:
            etiqueta = nombres.get(producto, str(producto)[:8])
            soporte_solo = historial.soporte(producto)
            print(
                f"   {etiqueta:<20} {veces:>4} veces juntos "
                f"(y sale en el {soporte_solo:.0%} de TODOS los pedidos)"
            )
        print("\nLa columna de la derecha es el problema. Un producto puede salir")
        print("mucho junto al ramen simplemente porque sale mucho, punto. Contar")
        print("no distingue entre 'acompana al ramen' y 'lo piden todos'. Para")
        print("separar las dos cosas hace falta dividir entre el soporte, que es")
        print("exactamente lo que hace el lift en la Unidad 2.")

    titulo("4. El pedido no se deja modificar desde fuera")
    prueba = historial.pedidos[0]
    print(f"Antes: {len(prueba.lineas)} lineas, total {prueba.total()}")
    try:
        prueba.lineas.append(  # type: ignore[attr-defined]
            LineaPedido(ProductoId(_uuid(99)), 1, Dinero.desde_pesos(9999))
        )
    except AttributeError as e:
        print(f"Intento de agregar una linea por fuera -> AttributeError: {e}")
    print(f"Despues: {len(prueba.lineas)} lineas, total {prueba.total()}")
    print("\n`lineas` devuelve una tupla, no la lista interna. Y el constructor")
    print("copia con tuple(lineas), asi que el pedido tampoco comparte")
    print("referencia con la lista que le pasaron. Ese es el tema 1.6.")


if __name__ == "__main__":
    main()

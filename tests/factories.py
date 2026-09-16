"""Armadores de escenarios para las pruebas.

Un menu de sushi chiquito pero con estructura: dos fuertes, dos entradas, dos
bebidas y un postre. Alcanza para probar afinidad por categoria, diversidad y
lift sin tener que leer veinte lineas de setup en cada prueba.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from conftest import pid, sid, uuid_de

from ceats_intel.domain.catalogo import Catalogo
from ceats_intel.domain.entidades import Canasta, HistorialVentas, LineaPedido, Pedido, Producto
from ceats_intel.domain.valueobjects import CategoriaId, Dinero, ProductoId, VentanaTemporal

CAT_FUERTE = CategoriaId(uuid_de(9001))
CAT_ENTRADA = CategoriaId(uuid_de(9002))
CAT_BEBIDA = CategoriaId(uuid_de(9003))
CAT_POSTRE = CategoriaId(uuid_de(9004))

# (numero, nombre, precio, categoria, nombre de la categoria)
MENU = [
    (1, "Yakimeshi Crispy", 189.0, CAT_FUERTE, "Platos fuertes"),
    (2, "Ramen Tonkotsu", 215.0, CAT_FUERTE, "Platos fuertes"),
    (3, "Gyoza 6 pz", 95.0, CAT_ENTRADA, "Entradas"),
    (4, "Edamame", 65.0, CAT_ENTRADA, "Entradas"),
    (5, "Te helado", 45.0, CAT_BEBIDA, "Bebidas"),
    (6, "Refresco", 35.0, CAT_BEBIDA, "Bebidas"),
    (7, "Mochi de matcha", 70.0, CAT_POSTRE, "Postres"),
]

YAKIMESHI, RAMEN, GYOZA, EDAMAME, TE, REFRESCO, MOCHI = (pid(n) for n, *_ in MENU)


def catalogo(inactivos: set[ProductoId] | None = None) -> Catalogo:
    inactivos = inactivos or set()
    productos = [
        Producto(
            pid(n),
            nombre,
            Dinero.desde_pesos(precio),
            categoria_id=cat,
            categoria_nombre=cat_nombre,
            activo=pid(n) not in inactivos,
        )
        for n, nombre, precio, cat, cat_nombre in MENU
    ]
    return Catalogo(productos)


def historial(combinaciones: list[tuple[list[ProductoId], int]]) -> HistorialVentas:
    """Arma un historial repitiendo cada combinacion las veces que se pida."""
    precios = {pid(n): precio for n, _, precio, _, _ in MENU}
    pedidos: list[Pedido] = []
    arranque = datetime(2026, 7, 1, 13, 0, tzinfo=UTC)
    contador = 0
    for productos, veces in combinaciones:
        for _ in range(veces):
            pedidos.append(
                Pedido(
                    f"p{contador}",
                    sid(),
                    arranque + timedelta(hours=contador % 400),
                    [LineaPedido(p, 1, Dinero.desde_pesos(precios[p])) for p in productos],
                )
            )
            contador += 1
    return HistorialVentas(sid(), VentanaTemporal.ultimos_dias(90, hoy=date(2026, 9, 14)), pedidos)


def historial_del_refresco() -> HistorialVentas:
    """El escenario que motiva todo el proyecto.

    El refresco sale en el 80% de los pedidos, con todo. La gyoza sale menos,
    pero casi siempre pegada al ramen. Contando a secas gana el refresco; con
    lift gana la gyoza, que es la respuesta correcta.
    """
    return historial(
        [
            ([RAMEN, GYOZA, REFRESCO], 40),
            ([RAMEN, REFRESCO], 10),
            ([RAMEN, GYOZA], 10),
            ([YAKIMESHI, REFRESCO], 40),
            ([YAKIMESHI, TE], 10),
            ([YAKIMESHI, MOCHI, REFRESCO], 10),
            ([EDAMAME, REFRESCO], 10),
        ]
    )


def canasta(*productos: ProductoId) -> Canasta:
    return Canasta(sid(), list(productos))

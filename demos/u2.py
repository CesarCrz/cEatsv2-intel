"""Demo de la Unidad 2: herencia, polimorfismo y por que el lift.

    python -m demos.u2                  # el comparativo completo
    python -m demos.u2 --modo auto      # una sola estrategia
    python -m demos.u2 --modo manual
    python -m demos.u2 --modo hibrido
    python -m demos.u2 --sin-datos      # restaurante recien abierto

Lo que hay que ver en la parte 3: la linea que llama a la estrategia es la
misma en los cuatro modos. Nunca se pregunta de que tipo es.
"""

from __future__ import annotations

import argparse
from datetime import UTC, date, datetime, timedelta

from ceats_intel.application.fabrica import FabricaEstrategias, ModoUpsell
from ceats_intel.domain.catalogo import Catalogo
from ceats_intel.domain.entidades import (
    Canasta,
    HistorialVentas,
    LineaPedido,
    Pedido,
    Producto,
)
from ceats_intel.domain.recomendacion import (
    ContextoRecomendacion,
    ReglaUpsell,
    confianza_suavizada,
)
from ceats_intel.domain.valueobjects import (
    CategoriaId,
    Dinero,
    ProductoId,
    SucursalId,
    VentanaTemporal,
)

SUCURSAL = SucursalId("00000000-0000-4000-8000-000000000001")

CAT = {
    "fuerte": CategoriaId("00000000-0000-4000-8000-000000009001"),
    "entrada": CategoriaId("00000000-0000-4000-8000-000000009002"),
    "bebida": CategoriaId("00000000-0000-4000-8000-000000009003"),
    "postre": CategoriaId("00000000-0000-4000-8000-000000009004"),
}

MENU = [
    (1, "Yakimeshi Crispy", 189.0, "fuerte", "Platos fuertes"),
    (2, "Ramen Tonkotsu", 215.0, "fuerte", "Platos fuertes"),
    (3, "Gyoza 6 pz", 95.0, "entrada", "Entradas"),
    (4, "Edamame", 65.0, "entrada", "Entradas"),
    (5, "Te helado", 45.0, "bebida", "Bebidas"),
    (6, "Refresco", 35.0, "bebida", "Bebidas"),
    (7, "Mochi de matcha", 70.0, "postre", "Postres"),
]

NOMBRES = {ProductoId(f"00000000-0000-4000-8000-{n:012d}"): nombre for n, nombre, *_ in MENU}
P = {nombre: ProductoId(f"00000000-0000-4000-8000-{n:012d}") for n, nombre, *_ in MENU}


def catalogo() -> Catalogo:
    return Catalogo(
        [
            Producto(
                ProductoId(f"00000000-0000-4000-8000-{n:012d}"),
                nombre,
                Dinero.desde_pesos(precio),
                categoria_id=CAT[clave],
                categoria_nombre=cat_nombre,
            )
            for n, nombre, precio, clave, cat_nombre in MENU
        ]
    )


def historial(combinaciones) -> HistorialVentas:
    precios = {ProductoId(f"00000000-0000-4000-8000-{n:012d}"): p for n, _, p, _, _ in MENU}
    pedidos = []
    arranque = datetime(2026, 7, 1, 13, 0, tzinfo=UTC)
    i = 0
    for productos, veces in combinaciones:
        for _ in range(veces):
            pedidos.append(
                Pedido(
                    f"p{i}",
                    SUCURSAL,
                    arranque + timedelta(hours=i % 1000),
                    [LineaPedido(p, 1, Dinero.desde_pesos(precios[p])) for p in productos],
                )
            )
            i += 1
    return HistorialVentas(
        SUCURSAL, VentanaTemporal.ultimos_dias(90, hoy=date(2026, 9, 14)), pedidos
    )


def escenario_real() -> HistorialVentas:
    """El refresco sale con todo. La gyoza va pegada al ramen."""
    return historial(
        [
            ([P["Ramen Tonkotsu"], P["Gyoza 6 pz"], P["Refresco"]], 40),
            ([P["Ramen Tonkotsu"], P["Refresco"]], 10),
            ([P["Ramen Tonkotsu"], P["Gyoza 6 pz"]], 10),
            ([P["Yakimeshi Crispy"], P["Refresco"]], 40),
            ([P["Yakimeshi Crispy"], P["Te helado"]], 10),
            ([P["Yakimeshi Crispy"], P["Mochi de matcha"], P["Refresco"]], 10),
            ([P["Edamame"], P["Refresco"]], 10),
        ]
    )


def titulo(texto: str) -> None:
    print(f"\n{texto}")
    print("-" * len(texto))


def main() -> None:
    parser = argparse.ArgumentParser(description="Demo de la Unidad 2")
    parser.add_argument("--modo", choices=[str(m) for m in ModoUpsell])
    parser.add_argument("--sin-datos", action="store_true", help="restaurante recien abierto")
    args = parser.parse_args()

    cat = catalogo()
    hist = historial([]) if args.sin_datos else escenario_real()
    carrito = Canasta(SUCURSAL, [P["Ramen Tonkotsu"]])
    fabrica = FabricaEstrategias()
    reglas = [ReglaUpsell("r-demo", P["Ramen Tonkotsu"], P["Edamame"], prioridad=5)]
    ctx = ContextoRecomendacion(canasta=carrito, historial=hist, catalogo=cat)

    print(f"Sucursal con {hist.total_pedidos} pedidos en la ventana")
    print(f"El cliente trae: {NOMBRES[P['Ramen Tonkotsu']]}")

    if not args.sin_datos:
        titulo("1. El problema del conteo")
        ancla = P["Ramen Tonkotsu"]
        print(f"{'producto':<20} {'juntos':>7} {'sop(B)':>8} {'conf':>8} {'lift':>7}")
        for nombre in ("Gyoza 6 pz", "Refresco", "Te helado", "Mochi de matcha"):
            producto = P[nombre]
            lift, ev = confianza_suavizada(hist, ancla, producto, alfa=10.0)
            print(
                f"{nombre:<20} {ev.juntos:>7} {ev.soporte_candidato:>8.3f} "
                f"{ev.confianza:>8.3f} {lift:>7.3f}"
            )
        print()
        print("Gyoza y refresco salieron 50 veces junto al ramen, el mismo conteo.")
        print("Pero el refresco sale en el 76% de TODOS los pedidos y la gyoza en")
        print("el 30%. Dividir entre el soporte separa 'acompana al ramen' de")
        print("'lo piden todos'. Por eso el lift de la gyoza es el doble.")

    titulo("2. La cascada de respaldo")
    modos = [ModoUpsell(args.modo)] if args.modo else list(ModoUpsell)
    for modo in modos:
        # La misma linea para los cinco modos. Eso es todo el punto.
        estrategia = fabrica.crear(modo, reglas, objetivo=3)
        sugerencias = estrategia.puntuar(ctx, limite=3)

        etiquetas = ", ".join(
            f"{NOMBRES.get(c.producto_id, '?')} ({c.score:.2f}, {c.origen})"
            for c in sugerencias
        )
        nivel = min((int(c.nivel) for c in sugerencias), default=7)
        print(f"{str(modo):<12} nivel {nivel}  ->  {etiquetas}")

    if args.sin_datos:
        print()
        print("Sin un solo pedido, la co-ocurrencia no tiene de donde salir y la")
        print("cascada baja hasta la afinidad por categoria: el cliente trae un")
        print("plato fuerte y no trae bebida, asi que se le ofrece una bebida.")
        print("Ninguna franja de sugerencias se queda vacia.")

    titulo("3. Polimorfismo: una sola linea llamadora")
    print("El codigo que produjo las cuatro filas de arriba es este, siempre:")
    print()
    print("    estrategia = fabrica.crear(modo, reglas, objetivo=3)")
    print("    sugerencias = estrategia.puntuar(ctx, limite=3)")
    print()
    print("No hay un solo isinstance ni un if por tipo. Detras puede haber una")
    print("co-ocurrencia sola, un composite con reglas manuales encima, o una")
    print("cascada de siete escalones. El caso de uso no se entera.")

    titulo("4. Afinidad por categoria, sin aprendizaje automatico")
    print("Las categorias en cEats son texto libre. El tipo se deduce asi:")
    for categoria_id, tipo in sorted(cat.tipos_por_categoria().items(), key=lambda x: str(x[1])):
        nombre = next(
            (c for _, _, _, clave, c in MENU if CAT[clave] == categoria_id), str(categoria_id)
        )
        print(f"   {nombre:<18} -> {tipo}")
    print()
    tipos_carrito = [cat.tipo_de(p) for p in carrito]
    buscados = cat.tipos_que_acompanan(tipos_carrito)
    print(f"El carrito trae: {', '.join(str(t) for t in tipos_carrito)}")
    print(f"Entonces se le ofrece: {', '.join(str(t) for t in buscados)}")
    print()
    print("Es la regla del mesero, no un modelo. Y funciona desde el primer dia")
    print("porque sale del menu, no del historial.")


if __name__ == "__main__":
    main()

"""Demo de la Unidad 3: calculo lambda y composicion de funciones.

    python -m demos.u3            # el recorrido completo
    python -m demos.u3 --repl     # para escribir terminos a mano

Los cuatro bloques son: sintaxis, alfa, beta, eta. Y al final la parte que
importa para el proyecto: el score del upsell escrito como composicion de
funciones puras, que es la misma idea aplicada al negocio.
"""

from __future__ import annotations

import argparse

from ceats_intel.domain.lambdacalc import (
    COMBINADORES,
    ErrorDeSintaxis,
    Evaluador,
    LimiteReduccionError,
    church,
    parsear,
)


def titulo(texto: str) -> None:
    print(f"\n{texto}")
    print("-" * len(texto))


def reducir(ev: Evaluador, fuente: str, mostrar_pasos: bool = True) -> None:
    termino = parsear(fuente)
    try:
        resultado, pasos = ev.reducir_con_pasos(termino)
    except LimiteReduccionError as e:
        print(f"  {fuente}")
        print(f"  -> se corto: {e}")
        return
    print(f"  {fuente}")
    if mostrar_pasos:
        for paso in pasos[:8]:
            print(f"    {paso}")
        if len(pasos) > 8:
            print(f"    ... y {len(pasos) - 8} pasos mas")
    print(f"  = {resultado}   ({len(pasos)} pasos)")


def recorrido() -> None:
    ev = Evaluador(max_pasos=1000)

    titulo("1. Sintaxis: solo hay tres formas")
    print("  M ::= x  |  (\\x. M)  |  (M N)")
    print()
    print(f"  variable     {parsear('x')}")
    print("  abstraccion ", parsear(r"\x. x"))
    print("  aplicacion  ", parsear("f x"))
    print()
    print("  \\x y. x  es azucar de ", parsear(r"\x y. x"))

    titulo("2. Conversion alfa: el nombre de la ligada da igual")
    identidad = parsear(r"\x. x")
    renombrada = ev.alfa_convertir(identidad, "y")
    print(f"  {identidad}  y  {renombrada}  son el mismo termino")
    print(f"  ¿iguales?  {identidad == renombrada}")
    print(f"  forma canonica de los dos: {identidad.canonico()}")
    print()
    print("  La igualdad se decide con indices de De Bruijn: cada variable")
    print("  ligada se escribe como la distancia al lambda que la liga. Asi el")
    print("  nombre desaparece y solo queda la estructura.")
    print()
    print("  Y por eso la sustitucion tiene que renombrar sola:")
    capturaria = parsear(r"\x. y")
    print(f"    ({capturaria})[y := x]  =  {capturaria.sustituir('y', parsear('x'))}")
    print("    No da (\\x. x). Si diera, la x que entro libre habria quedado")
    print("    atrapada por el lambda y cambiaria de significado.")

    titulo("3. Reduccion beta: aplicar una funcion")
    print("  (\\x. M) N  ->  M[x := N]")
    print()
    reducir(ev, r"(\x. x) y")
    print()
    reducir(ev, r"(\x y. x) a b")
    print()
    print("  Los combinadores de siempre:")
    s, k = COMBINADORES["S"], COMBINADORES["K"]
    reducir(ev, f"({s}) ({k}) ({k}) z", mostrar_pasos=False)
    print("  S K K = I, la identidad.")

    titulo("4. Conversion eta: quitar el envoltorio")
    print("  \\x. (f x)  ->  f    si x no aparece libre en f")
    print()
    con_eta = parsear(r"\x. f x")
    print(" ", con_eta, " -> ", ev.eta_reducir(con_eta))
    sin_eta = parsear(r"\x. x x")
    print(f"  {sin_eta}  ->  {ev.eta_reducir(sin_eta)}   (no aplica: x es libre en la funcion)")

    titulo("5. Numerales de Church: los numeros son funciones")
    for n in (0, 1, 2, 3):
        print(f"  {n} = {church(n)}")
    print()
    suma = COMBINADORES["suma"]
    resultado, pasos = ev.reducir_con_pasos(parsear(f"({suma}) ({church(2)}) ({church(3)})"))
    print(f"  2 + 3 en {len(pasos)} pasos beta")
    print(f"  resultado: {resultado}")
    print(f"  ¿es el numeral 5?  {resultado == church(5)}")

    titulo("6. Omega: lo que no termina")
    print("  (\\x. x x) (\\x. x x) se reduce a si mismo, para siempre.")
    print()
    reducir(ev, COMBINADORES["Omega"], mostrar_pasos=False)
    print()
    print("  Por eso el evaluador corta a max_pasos. El laboratorio del CRM")
    print("  acepta terminos escritos a mano, y sin ese corte cualquiera tumba")
    print("  el servicio con doce caracteres.")

    titulo("7. Donde vive esto en el proyecto")
    print("  El score del upsell es composicion de funciones puras:")
    print()
    print("    pipeline = (PipelineScoring.identidad()")
    print("        .then('filtrar_inactivos', comb.filtrar_inactivos(catalogo))")
    print("        .then('quitar_canasta',    comb.quitar_los_de_la_canasta(canasta))")
    print("        .then('penalizar_caros',   comb.penalizar_caros(catalogo))")
    print("        .then('diversificar',      comb.diversificar_por_categoria(catalogo, 2))")
    print("        .then('top_n',             comb.top_n(limite)))")
    print()
    print("  Cada combinador es de orden superior: top_n(3) no recorta nada,")
    print("  devuelve el recortador. Eso es currificacion.")
    print()
    print("  Armar la cadena y despues aplicarla a los candidatos es lo mismo")
    print("  que componer terminos y beta-reducirlos. La diferencia es que en")
    print("  lambdacalc las funciones las reduzco yo, y aqui las reduce el")
    print("  intérprete de Python.")
    print()
    print("  Que sean puras no es adorno: es de lo que depende que el mismo")
    print("  carrito de lo mismo en el checkout y en el laboratorio del CRM.")


def repl() -> None:
    ev = Evaluador(max_pasos=10_000)
    print("Escribe un termino lambda. 'salir' para terminar, 'ej' para ejemplos.")
    while True:
        try:
            fuente = input("λ> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not fuente:
            continue
        if fuente in ("salir", "exit", "quit"):
            return
        if fuente == "ej":
            for nombre, cuerpo in COMBINADORES.items():
                print(f"  {nombre:<10} {cuerpo}")
            continue
        try:
            reducir(ev, fuente)
        except ErrorDeSintaxis as e:
            print(f"  error de sintaxis: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Demo de la Unidad 3")
    parser.add_argument("--repl", action="store_true", help="modo interactivo")
    args = parser.parse_args()
    if args.repl:
        repl()
    else:
        recorrido()


if __name__ == "__main__":
    main()

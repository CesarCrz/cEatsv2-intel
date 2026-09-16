"""El menu de una sucursal, y como adivinar de que tipo es cada categoria.

Las categorias en cEats son texto libre: cada restaurante pone lo que quiere.
Uno escribe "Bebidas", otro "Refrescos y mas", otro "Ramen". No hay taxonomia.

Para la afinidad por categoria hace falta saber que acompana a que, y hay tres
formas de averiguarlo, de mas confiable a menos:

1. El superadmin lo dijo en el CRM. Dato duro, se respeta siempre.
2. El precio relativo. Lo barato acompana a lo caro. Funciona con cualquier
   nombre, en cualquier idioma.
3. Un diccionario de palabras. Es lo ultimo, para un restaurante que no tiene
   ni un pedido todavia.

Nada de esto es aprendizaje automatico, y es a proposito: con 40 pedidos un
modelo entrenado es peor que una regla, y ademas hay que poder explicarle al
restaurantero por que le sugerimos lo que le sugerimos.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from enum import Enum
from statistics import median

from ceats_intel.domain.entidades import Producto
from ceats_intel.domain.valueobjects import CategoriaId, ProductoId


class TipoCategoria(str, Enum):
    ENTRADA = "entrada"
    FUERTE = "fuerte"
    BEBIDA = "bebida"
    POSTRE = "postre"
    EXTRA = "extra"
    DESCONOCIDO = "desconocido"

    def __str__(self) -> str:
        return self.value


# Que acompana bien a que. Sale de como funciona una comida, no de los datos.
# Es la regla que aplica cualquier mesero: si ya traes el fuerte, te ofrece
# bebida, entrada o postre, en ese orden.
ACOMPANA_A: dict[TipoCategoria, tuple[TipoCategoria, ...]] = {
    TipoCategoria.FUERTE: (TipoCategoria.BEBIDA, TipoCategoria.ENTRADA, TipoCategoria.POSTRE),
    TipoCategoria.ENTRADA: (TipoCategoria.FUERTE, TipoCategoria.BEBIDA),
    TipoCategoria.BEBIDA: (TipoCategoria.FUERTE, TipoCategoria.POSTRE),
    TipoCategoria.POSTRE: (TipoCategoria.BEBIDA,),
    TipoCategoria.EXTRA: (TipoCategoria.BEBIDA, TipoCategoria.FUERTE),
    TipoCategoria.DESCONOCIDO: (TipoCategoria.BEBIDA, TipoCategoria.POSTRE),
}

# Diccionario de ultimo recurso. Se compara contra el nombre en minusculas y
# sin acentos. No pretende ser exhaustivo: cubre lo que se repite en los menus
# mexicanos que ya estan en la plataforma.
PALABRAS: dict[TipoCategoria, tuple[str, ...]] = {
    TipoCategoria.BEBIDA: (
        "bebida", "refresco", "soda", "agua", "jugo", "cerveza", "vino", "coctel",
        "cafe", "te ", "tea", "smoothie", "licuado", "malteada", "frappe", "limonada",
        "michelada", "chelas", "drink", "liquido",
    ),
    TipoCategoria.POSTRE: (
        "postre", "dulce", "helado", "pastel", "pay", "flan", "mochi", "dessert",
        "nieve", "brownie", "cheesecake", "gelatina", "churro",
    ),
    TipoCategoria.ENTRADA: (
        "entrada", "botana", "aperitivo", "snack", "starter", "appetizer",
        "sopa", "crema", "ensalada", "salad", "guarnicion", "side",
    ),
    TipoCategoria.EXTRA: (
        "extra", "adicional", "complemento", "salsa", "aderezo", "topping",
        "acompanamiento", "agregado",
    ),
    TipoCategoria.FUERTE: (
        "plato", "fuerte", "principal", "especialidad", "main", "hamburguesa",
        "pizza", "taco", "torta", "ramen", "sushi", "roll", "pasta", "carne",
        "pollo", "pescado", "mariscos", "combo", "paquete", "menu", "comida",
        "desayuno", "cena", "parrilla", "bowl", "baguette", "burrito",
    ),
}

_ACENTOS = str.maketrans("áéíóúüñ", "aeiouun")


def _normalizar(texto: str) -> str:
    return texto.lower().strip().translate(_ACENTOS)


def tipo_por_nombre(nombre: str) -> TipoCategoria:
    """Adivina el tipo por el nombre de la categoria.

    Recorre en un orden fijo a proposito: "agua de horchata" tiene que caer en
    bebida antes de que "horchata" toque cualquier otra lista. Los tipos mas
    especificos van primero y el fuerte al final, porque su lista es la mas
    ancha y se comeria a los demas.
    """
    limpio = _normalizar(nombre)
    for tipo in (
        TipoCategoria.BEBIDA,
        TipoCategoria.POSTRE,
        TipoCategoria.ENTRADA,
        TipoCategoria.EXTRA,
        TipoCategoria.FUERTE,
    ):
        if any(palabra in limpio for palabra in PALABRAS[tipo]):
            return tipo
    return TipoCategoria.DESCONOCIDO


class Catalogo:
    """Los productos de una sucursal, con sus categorias ya clasificadas."""

    __slots__ = ("_productos", "_por_id", "_tipos", "_destacados")

    def __init__(
        self,
        productos: Iterable[Producto],
        tipos_confirmados: dict[CategoriaId, TipoCategoria] | None = None,
        destacados: Iterable[ProductoId] = (),
    ) -> None:
        self._productos = tuple(productos)
        self._por_id = {p.id: p for p in self._productos}
        self._destacados = tuple(destacados)
        self._tipos = self._clasificar(tipos_confirmados or {})

    # ------------------------------------------------------------- consultas

    @property
    def productos(self) -> Sequence[Producto]:
        return self._productos

    def producto(self, producto_id: ProductoId) -> Producto | None:
        return self._por_id.get(producto_id)

    def existe(self, producto_id: ProductoId) -> bool:
        return producto_id in self._por_id

    def activos(self) -> tuple[Producto, ...]:
        return tuple(p for p in self._productos if p.es_sugerible())

    def destacados(self) -> tuple[ProductoId, ...]:
        """Los marcados por el restaurante. Si no hay, los primeros activos.

        Es el ultimo escalon de la cascada: un restaurante recien dado de alta,
        sin un solo pedido, tiene que ver algo en la franja de sugerencias.
        """
        if self._destacados:
            return self._destacados
        return tuple(p.id for p in self.activos()[:8])

    def tipo_de(self, producto_id: ProductoId) -> TipoCategoria:
        producto = self._por_id.get(producto_id)
        if producto is None or producto.categoria_id is None:
            return TipoCategoria.DESCONOCIDO
        return self._tipos.get(producto.categoria_id, TipoCategoria.DESCONOCIDO)

    def tipos_que_acompanan(
        self, tipos_en_canasta: Iterable[TipoCategoria]
    ) -> tuple[TipoCategoria, ...]:
        """Que tipos tiene sentido ofrecer, dado lo que ya trae el cliente.

        Los que ya estan en la canasta se caen: si ya lleva bebida, ofrecerle
        otra bebida es lo que hace ver tonto al sistema.
        """
        presentes = set(tipos_en_canasta)
        ordenados: list[TipoCategoria] = []
        for tipo in presentes:
            for sugerido in ACOMPANA_A.get(tipo, ()):
                if sugerido not in presentes and sugerido not in ordenados:
                    ordenados.append(sugerido)
        return tuple(ordenados)

    def productos_de_tipo(self, tipo: TipoCategoria) -> tuple[Producto, ...]:
        return tuple(p for p in self.activos() if self.tipo_de(p.id) is tipo)

    def tipos_por_categoria(self) -> dict[CategoriaId, TipoCategoria]:
        return dict(self._tipos)

    # -------------------------------------------------------------- internos

    def _clasificar(
        self, confirmados: dict[CategoriaId, TipoCategoria]
    ) -> dict[CategoriaId, TipoCategoria]:
        activos = [p for p in self._productos if p.es_sugerible()]
        if not activos:
            return dict(confirmados)

        mediana_menu = median([p.precio.centavos for p in activos])
        por_categoria: dict[CategoriaId, list[Producto]] = {}
        for producto in activos:
            if producto.categoria_id is not None:
                por_categoria.setdefault(producto.categoria_id, []).append(producto)

        tipos: dict[CategoriaId, TipoCategoria] = {}
        for categoria_id, miembros in por_categoria.items():
            if categoria_id in confirmados:
                tipos[categoria_id] = confirmados[categoria_id]
                continue

            supuesto = tipo_por_nombre(miembros[0].categoria_nombre)
            if supuesto is not TipoCategoria.DESCONOCIDO:
                tipos[categoria_id] = supuesto
                continue

            # El nombre no dijo nada. Queda el precio: si la categoria cuesta
            # menos de la mitad de la mediana del menu, es de las que
            # acompanan; si cuesta mas, es de las que el cliente vino a comer.
            mediana_categoria = median([p.precio.centavos for p in miembros])
            if mediana_categoria <= mediana_menu * 0.4:
                tipos[categoria_id] = TipoCategoria.EXTRA
            elif mediana_categoria >= mediana_menu * 0.9:
                tipos[categoria_id] = TipoCategoria.FUERTE
            else:
                tipos[categoria_id] = TipoCategoria.DESCONOCIDO

        tipos.update(confirmados)
        return tipos

    def __repr__(self) -> str:
        return f"Catalogo({len(self._productos)} productos)"

"""Sucursal. Casi un value object, pero tiene identidad propia."""

from __future__ import annotations

from ceats_intel.domain.valueobjects import RestauranteId, SucursalId


class Sucursal:
    __slots__ = ("_id", "_restaurante_id", "_nombre", "_zona_horaria")

    def __init__(
        self,
        id_: SucursalId,
        restaurante_id: RestauranteId,
        nombre: str,
        zona_horaria: str = "America/Mexico_City",
    ) -> None:
        if not nombre.strip():
            raise ValueError("La sucursal necesita nombre")
        self._id = id_
        self._restaurante_id = restaurante_id
        self._nombre = nombre.strip()
        self._zona_horaria = zona_horaria

    @property
    def id(self) -> SucursalId:
        return self._id

    @property
    def restaurante_id(self) -> RestauranteId:
        return self._restaurante_id

    @property
    def nombre(self) -> str:
        return self._nombre

    @property
    def zona_horaria(self) -> str:
        return self._zona_horaria

    def __eq__(self, otro: object) -> bool:
        if not isinstance(otro, Sucursal):
            return NotImplemented
        return self._id == otro._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"Sucursal({self._nombre!r})"

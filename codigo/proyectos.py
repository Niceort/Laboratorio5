from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import List, Optional


class ValidacionProyectoError(Exception):
    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje


class Proyecto:
    def __init__(
        self,
        referencia: str,
        area: str,
        entidad_solicitante: str,
        comunidad_autonoma: str,
        concedido: bool = False,
    ) -> None:
        self.referencia = self._validar_texto(referencia, "referencia")
        self.area = self._validar_texto(area, "area")
        self.entidad_solicitante = self._validar_texto(entidad_solicitante, "entidad_solicitante")
        self.comunidad_autonoma = self._validar_texto(comunidad_autonoma, "comunidad_autonoma")
        self.concedido = bool(concedido)

    def _validar_texto(self, valor: str, nombre: str) -> str:
        if valor is None:
            raise ValidacionProyectoError("El atributo '{0}' no puede ser nulo.".format(nombre))
        texto = str(valor).strip()
        if texto == "":
            raise ValidacionProyectoError("El atributo '{0}' no puede estar vacio.".format(nombre))
        return texto

    @property
    def identificador(self) -> str:
        return self.referencia

    @property
    def nombre_resumido(self) -> str:
        return "{0} - {1}".format(self.referencia, self.entidad_solicitante)

    def to_dict(self) -> dict:
        return {
            "referencia": self.referencia,
            "area": self.area,
            "entidad_solicitante": self.entidad_solicitante,
            "comunidad_autonoma": self.comunidad_autonoma,
            "concedido": self.concedido,
        }


class ProyectoConcedido(Proyecto):
    def __init__(
        self,
        referencia: str,
        area: str,
        entidad_solicitante: str,
        comunidad_autonoma: str,
        costes_directos: Decimal,
        costes_indirectos: Decimal,
        anticipo: Decimal,
        subvencion: Decimal,
        anualidades: List[Decimal],
        contratado_predoctoral: bool,
        numero_contratos_predoc: int = 0,
    ) -> None:
        super().__init__(referencia, area, entidad_solicitante, comunidad_autonoma, True)
        self.costes_directos = self._validar_decimal(costes_directos, "costes_directos")
        self.costes_indirectos = self._validar_decimal(costes_indirectos, "costes_indirectos")
        self.anticipo = self._validar_decimal(anticipo, "anticipo")
        self.subvencion = self._validar_decimal(subvencion, "subvencion")
        self.anualidades = self._validar_anualidades(anualidades)
        self.numero_contratos_predoc = self._validar_entero_no_negativo(
            numero_contratos_predoc,
            "numero_contratos_predoc",
        )
        self.contratado_predoctoral = bool(contratado_predoctoral)
        if self.numero_contratos_predoc > 0:
            self.contratado_predoctoral = True
        self._validar_coherencia_economica()

    def _validar_decimal(self, valor: Decimal, nombre: str) -> Decimal:
        if valor is None:
            raise ValidacionProyectoError("El atributo '{0}' no puede ser nulo.".format(nombre))
        if isinstance(valor, Decimal):
            decimal_valor = valor
        else:
            try:
                decimal_valor = Decimal(str(valor))
            except (InvalidOperation, ValueError):
                raise ValidacionProyectoError(
                    "El atributo '{0}' debe ser numerico.".format(nombre)
                )
        return decimal_valor.quantize(Decimal("0.01"))

    def _validar_entero_no_negativo(self, valor: int, nombre: str) -> int:
        try:
            entero = int(valor)
        except (TypeError, ValueError):
            raise ValidacionProyectoError("El atributo '{0}' debe ser un entero.".format(nombre))
        if entero < 0:
            raise ValidacionProyectoError(
                "El atributo '{0}' no puede ser negativo.".format(nombre)
            )
        return entero

    def _validar_anualidades(self, anualidades: List[Decimal]) -> List[Decimal]:
        if anualidades is None:
            raise ValidacionProyectoError("La lista de anualidades no puede ser nula.")
        if len(anualidades) != 4:
            raise ValidacionProyectoError("La lista de anualidades debe contener exactamente 4 valores.")
        valores = []
        indice = 0
        while indice < len(anualidades):
            valores.append(self._validar_decimal(anualidades[indice], "anualidad_{0}".format(indice + 2025)))
            indice += 1
        return valores

    def _validar_coherencia_economica(self) -> None:
        suma_costes = self.costes_directos + self.costes_indirectos
        suma_financiacion = self.anticipo + self.subvencion
        if suma_costes != suma_financiacion:
            raise ValidacionProyectoError(
                "Incoherencia economica en {0}: costes ({1}) != financiacion ({2}).".format(
                    self.referencia,
                    suma_costes,
                    suma_financiacion,
                )
            )
        if suma_costes != self.presupuesto:
            raise ValidacionProyectoError(
                "Incoherencia economica en {0}: presupuesto derivado incorrecto.".format(
                    self.referencia
                )
            )

    @property
    def presupuesto(self) -> Decimal:
        return (self.costes_directos + self.costes_indirectos).quantize(Decimal("0.01"))

    @property
    def total_anualidades(self) -> Decimal:
        total = Decimal("0.00")
        for anualidad in self.anualidades:
            total += anualidad
        return total.quantize(Decimal("0.01"))

    @property
    def resumen_financiero(self) -> str:
        return "Presupuesto {0} | Anticipo {1} | Subvencion {2}".format(
            self.presupuesto,
            self.anticipo,
            self.subvencion,
        )

    def to_dict(self) -> dict:
        datos = super().to_dict()
        datos.update(
            {
                "costes_directos": str(self.costes_directos),
                "costes_indirectos": str(self.costes_indirectos),
                "anticipo": str(self.anticipo),
                "subvencion": str(self.subvencion),
                "anualidades": [str(valor) for valor in self.anualidades],
                "contratado_predoctoral": self.contratado_predoctoral,
                "numero_contratos_predoc": self.numero_contratos_predoc,
                "presupuesto": str(self.presupuesto),
            }
        )
        return datos


class ProyectoContrato(ProyectoConcedido):
    def __init__(
        self,
        referencia: str,
        area: str,
        entidad_solicitante: str,
        comunidad_autonoma: str,
        costes_directos: Decimal,
        costes_indirectos: Decimal,
        anticipo: Decimal,
        subvencion: Decimal,
        anualidades: List[Decimal],
        titulo_del_proyecto: str,
        numero_contratos_predoc: int = 1,
    ) -> None:
        self.titulo_del_proyecto = self._validar_titulo(titulo_del_proyecto)
        super().__init__(
            referencia,
            area,
            entidad_solicitante,
            comunidad_autonoma,
            costes_directos,
            costes_indirectos,
            anticipo,
            subvencion,
            anualidades,
            True,
            numero_contratos_predoc,
        )
        self.contratado_predoctoral = True

    def _validar_titulo(self, titulo: str) -> str:
        if titulo is None:
            raise ValidacionProyectoError("El titulo del proyecto no puede ser nulo.")
        texto = str(titulo).strip()
        if texto == "":
            raise ValidacionProyectoError("El titulo del proyecto no puede estar vacio.")
        return texto

    @property
    def descripcion_corta(self) -> str:
        if len(self.titulo_del_proyecto) <= 80:
            return self.titulo_del_proyecto
        return self.titulo_del_proyecto[:77] + "..."

    def to_dict(self) -> dict:
        datos = super().to_dict()
        datos["titulo_del_proyecto"] = self.titulo_del_proyecto
        return datos

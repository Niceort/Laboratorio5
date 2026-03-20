from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Optional, Type

from proyectos import Proyecto, ProyectoConcedido, ProyectoContrato, ValidacionProyectoError


class ResultadoOperacion:
    def __init__(self, exito: bool, mensaje: str, datos: Optional[dict] = None) -> None:
        self.exito = exito
        self.mensaje = mensaje
        self.datos = datos if datos is not None else {}


class GestorBase:
    def __init__(self, tipo_esperado: Type[Proyecto], nombre: str) -> None:
        self.tipo_esperado = tipo_esperado
        self.nombre = nombre
        self._proyectos: Dict[str, Proyecto] = {}

    def agregar(self, proyecto: Proyecto) -> ResultadoOperacion:
        if not isinstance(proyecto, self.tipo_esperado):
            return ResultadoOperacion(False, "Tipo no valido para el gestor '{0}'.".format(self.nombre))
        if proyecto.referencia in self._proyectos:
            return ResultadoOperacion(
                False,
                "La referencia '{0}' ya existe en el gestor '{1}'.".format(
                    proyecto.referencia,
                    self.nombre,
                ),
            )
        self._proyectos[proyecto.referencia] = proyecto
        return ResultadoOperacion(
            True,
            "Proyecto '{0}' agregado correctamente a '{1}'.".format(
                proyecto.referencia,
                self.nombre,
            ),
        )

    def obtener(self, referencia: str) -> Optional[Proyecto]:
        return self._proyectos.get(referencia)

    def existe(self, referencia: str) -> bool:
        return referencia in self._proyectos

    def cantidad(self) -> int:
        return len(self._proyectos)

    def listar(self) -> List[Proyecto]:
        return list(self._proyectos.values())

    def comunidades(self) -> List[str]:
        resultado = []
        vistos = set()
        for proyecto in self._proyectos.values():
            if proyecto.comunidad_autonoma not in vistos:
                vistos.add(proyecto.comunidad_autonoma)
                resultado.append(proyecto.comunidad_autonoma)
        resultado.sort()
        return resultado

    def contar_por_comunidad(self) -> Dict[str, int]:
        conteo: Dict[str, int] = {}
        for proyecto in self._proyectos.values():
            comunidad = proyecto.comunidad_autonoma
            if comunidad not in conteo:
                conteo[comunidad] = 0
            conteo[comunidad] += 1
        return conteo


class GestorProyecto(GestorBase):
    def __init__(self) -> None:
        super().__init__(Proyecto, "GestorProyecto")

    def calcular_tasa_concedidos(
        self,
        comunidad_autonoma: str,
        gestor_concedidos: "GestorProyectoConcedido",
    ) -> ResultadoOperacion:
        if comunidad_autonoma is None or str(comunidad_autonoma).strip() == "":
            return ResultadoOperacion(False, "La comunidad autonoma es obligatoria.")
        comunidad = str(comunidad_autonoma).strip().upper()
        total_solicitados = 0
        for proyecto in self._proyectos.values():
            if proyecto.comunidad_autonoma.upper() == comunidad:
                total_solicitados += 1
        if total_solicitados == 0:
            return ResultadoOperacion(False, "No hay proyectos para la comunidad indicada.")
        total_concedidos = 0
        for proyecto in gestor_concedidos.listar():
            if proyecto.comunidad_autonoma.upper() == comunidad:
                total_concedidos += 1
        tasa = (Decimal(total_concedidos) / Decimal(total_solicitados)) * Decimal("100")
        return ResultadoOperacion(
            True,
            "Tasa calculada correctamente.",
            {
                "comunidad_autonoma": comunidad,
                "solicitados": total_solicitados,
                "concedidos": total_concedidos,
                "tasa": tasa.quantize(Decimal("0.01")),
            },
        )


class GestorProyectoConcedido(GestorBase):
    def __init__(self) -> None:
        super().__init__(ProyectoConcedido, "GestorProyectoConcedido")

    def total_importe_global(self) -> Decimal:
        total = Decimal("0.00")
        for proyecto in self._proyectos.values():
            total += proyecto.presupuesto
        return total.quantize(Decimal("0.01"))

    def total_importe_por_comunidad(self) -> Dict[str, Decimal]:
        totales: Dict[str, Decimal] = {}
        for proyecto in self._proyectos.values():
            comunidad = proyecto.comunidad_autonoma
            if comunidad not in totales:
                totales[comunidad] = Decimal("0.00")
            totales[comunidad] += proyecto.presupuesto
        for comunidad in list(totales.keys()):
            totales[comunidad] = totales[comunidad].quantize(Decimal("0.01"))
        return dict(sorted(totales.items(), key=lambda item: item[0]))

    def validar_coherencia(self) -> ResultadoOperacion:
        errores = []
        for proyecto in self._proyectos.values():
            try:
                proyecto._validar_coherencia_economica()
            except ValidacionProyectoError as error:
                errores.append(error.mensaje)
        if errores:
            return ResultadoOperacion(False, "Se detectaron incoherencias economicas.", {"errores": errores})
        return ResultadoOperacion(True, "La coherencia economica es correcta.")


class GestorProyectoContrato(GestorBase):
    def __init__(self) -> None:
        super().__init__(ProyectoContrato, "GestorProyectoContrato")

    def validar_subconjunto(self, gestor_concedidos: GestorProyectoConcedido) -> ResultadoOperacion:
        referencias_no_encontradas = []
        for proyecto in self._proyectos.values():
            concedido = gestor_concedidos.obtener(proyecto.referencia)
            if concedido is None:
                referencias_no_encontradas.append(proyecto.referencia)
        if referencias_no_encontradas:
            return ResultadoOperacion(
                False,
                "Existen contratos que no pertenecen al subconjunto de concedidos.",
                {"referencias": referencias_no_encontradas},
            )
        return ResultadoOperacion(True, "Todos los contratos pertenecen al subconjunto de concedidos.")

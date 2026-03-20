from __future__ import annotations

import argparse
from decimal import Decimal

from factoria import Factoria
from interfaz import AplicacionLaboratorio


class ProgramaPrincipal:
    def __init__(self) -> None:
        self.argumentos = self._crear_argumentos()

    def _crear_argumentos(self):
        parser = argparse.ArgumentParser(
            description="Laboratorio 5 - Analisis de proyectos de investigacion"
        )
        parser.add_argument(
            "--modo",
            choices=["gui", "consola"],
            default="gui",
            help="Modo de ejecucion del programa.",
        )
        parser.add_argument(
            "--data-dir",
            default=None,
            help="Directorio que contiene los anexos Excel.",
        )
        parser.add_argument(
            "--comunidad",
            default="ANDALUCIA",
            help="Comunidad autonoma para la estadistica de consola.",
        )
        return parser.parse_args()

    def ejecutar(self) -> None:
        if self.argumentos.modo == "consola":
            self._ejecutar_consola()
            return
        self._ejecutar_gui()

    def _ejecutar_consola(self) -> None:
        factoria = Factoria(self.argumentos.data_dir)
        resultado = factoria.cargar()
        if not resultado.exito:
            print("ERROR: {0}".format(resultado.mensaje))
            return

        gestor_proyectos = resultado.datos["gestor_proyectos"]
        gestor_concedidos = resultado.datos["gestor_concedidos"]
        gestor_contratos = resultado.datos["gestor_contratos"]

        print("Carga completada correctamente.")
        print("- Total proyectos: {0}".format(gestor_proyectos.cantidad()))
        print("- Total concedidos: {0}".format(gestor_concedidos.cantidad()))
        print("- Total contratos predoctorales: {0}".format(gestor_contratos.cantidad()))

        estadistica = gestor_proyectos.calcular_tasa_concedidos(
            self.argumentos.comunidad,
            gestor_concedidos,
        )
        if estadistica.exito:
            print(
                "- Tasa de concedidos en {0}: {1}% ({2}/{3})".format(
                    estadistica.datos["comunidad_autonoma"],
                    estadistica.datos["tasa"],
                    estadistica.datos["concedidos"],
                    estadistica.datos["solicitados"],
                )
            )
        else:
            print("- Estadistica no disponible: {0}".format(estadistica.mensaje))

        print("- Importe global concedido: {0} EUR".format(self._formatear_decimal(gestor_concedidos.total_importe_global())))
        print("- Importes por comunidad autonoma:")
        for comunidad, importe in gestor_concedidos.total_importe_por_comunidad().items():
            print("  * {0}: {1} EUR".format(comunidad, self._formatear_decimal(importe)))

        validacion_subconjunto = gestor_contratos.validar_subconjunto(gestor_concedidos)
        print("- Validacion subconjunto contratos: {0}".format(validacion_subconjunto.mensaje))

    def _ejecutar_gui(self) -> None:
        aplicacion = AplicacionLaboratorio()
        if self.argumentos.data_dir is not None:
            aplicacion.ruta_datos.set(self.argumentos.data_dir)
        aplicacion.mainloop()

    def _formatear_decimal(self, valor: Decimal) -> str:
        texto = "{0:,.2f}".format(valor)
        texto = texto.replace(",", "X")
        texto = texto.replace(".", ",")
        texto = texto.replace("X", ".")
        return texto


if __name__ == "__main__":
    ProgramaPrincipal().ejecutar()

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from factoria import Factoria
from gestor import GestorProyecto, GestorProyectoConcedido, GestorProyectoContrato


class AplicacionLaboratorio(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self.title("Laboratorio 5 - Agencia Estatal de Investigacion")
        self.geometry("1280x820")
        self.minsize(1100, 720)

        self.ruta_datos = tk.StringVar(value=str(self._ruta_por_defecto()))
        self.comunidad_seleccionada = tk.StringVar(value="ANDALUCIA")

        self.factoria = None
        self.gestor_proyectos = None
        self.gestor_concedidos = None
        self.gestor_contratos = None

        self._crear_componentes()

    def _ruta_por_defecto(self) -> Path:
        directorio_codigo = Path(__file__).resolve().parent
        directorio_anexos = directorio_codigo.parent / "data" / "anexos_excel"
        if directorio_anexos.exists():
            return directorio_anexos
        return directorio_codigo.parent / "data"

    def _crear_componentes(self) -> None:
        contenedor = ctk.CTkFrame(self, bg="#F4F7FB")
        contenedor.pack(fill="both", expand=True)

        encabezado = ctk.CTkFrame(contenedor, bg="#1F3C88", padx=20, pady=20)
        encabezado.pack(fill="x", padx=16, pady=(16, 8))

        titulo = ctk.CTkLabel(
            encabezado,
            text="Laboratorio 5 · Convocatoria de proyectos de investigacion",
            fg="white",
            bg="#1F3C88",
            font=("Arial", 22, "bold"),
        )
        titulo.pack(anchor="w")

        subtitulo = ctk.CTkLabel(
            encabezado,
            text="Carga, validacion y consulta de anexos Excel con arquitectura orientada a objetos.",
            fg="#DDE7FF",
            bg="#1F3C88",
            font=("Arial", 11),
        )
        subtitulo.pack(anchor="w", pady=(8, 0))

        barra = ctk.CTkFrame(contenedor, bg="#FFFFFF", padx=16, pady=16)
        barra.pack(fill="x", padx=16, pady=(0, 8))

        etiqueta_ruta = ctk.CTkLabel(barra, text="Directorio de anexos", bg="#FFFFFF", font=("Arial", 12, "bold"))
        etiqueta_ruta.grid(row=0, column=0, sticky="w")

        entrada_ruta = ctk.CTkEntry(barra, textvariable=self.ruta_datos, width=700)
        entrada_ruta.grid(row=1, column=0, padx=(0, 12), pady=(6, 0), sticky="ew")

        boton_examinar = ctk.CTkButton(barra, text="Examinar", command=self._seleccionar_directorio)
        boton_examinar.grid(row=1, column=1, pady=(6, 0), padx=(0, 8))

        boton_cargar = ctk.CTkButton(barra, text="Inicializar factoria", command=self._cargar_datos)
        boton_cargar.grid(row=1, column=2, pady=(6, 0))
        barra.grid_columnconfigure(0, weight=1)

        self.panel_estado = ctk.CTkLabel(
            contenedor,
            text="Estado: pendiente de carga.",
            anchor="w",
            bg="#F4F7FB",
            font=("Arial", 12, "bold"),
        )
        self.panel_estado.pack(fill="x", padx=20, pady=(0, 8))

        self.pestanas = ctk.CTkTabview(contenedor)
        self.pestanas.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self.pestanas.add("Resumen")
        self.pestanas.add("Estadisticas")
        self.pestanas.add("Importes")
        self.pestanas.add("Mensajes")

        self._crear_tab_resumen()
        self._crear_tab_estadisticas()
        self._crear_tab_importes()
        self._crear_tab_mensajes()

    def _crear_tab_resumen(self) -> None:
        tab = self.pestanas.tab("Resumen")
        self.tarjetas_resumen = {}
        nombres = [
            ("proyectos", "Total de proyectos"),
            ("concedidos", "Total concedidos"),
            ("contratos", "Total con contrato predoctoral"),
        ]
        indice = 0
        while indice < len(nombres):
            clave, etiqueta = nombres[indice]
            tarjeta = ctk.CTkFrame(tab, bg="#FFFFFF", padx=20, pady=20)
            tarjeta.grid(row=0, column=indice, padx=10, pady=16, sticky="nsew")
            titulo = ctk.CTkLabel(tarjeta, text=etiqueta, bg="#FFFFFF", font=("Arial", 12, "bold"))
            titulo.pack(anchor="w")
            valor = ctk.CTkLabel(tarjeta, text="0", bg="#FFFFFF", font=("Arial", 28, "bold"))
            valor.pack(anchor="w", pady=(10, 0))
            self.tarjetas_resumen[clave] = valor
            tab.grid_columnconfigure(indice, weight=1)
            indice += 1

        self.texto_resumen = ctk.CTkTextbox(tab, height=380, wrap="word")
        self.texto_resumen.grid(row=1, column=0, columnspan=3, padx=10, pady=(0, 16), sticky="nsew")
        tab.grid_rowconfigure(1, weight=1)

    def _crear_tab_estadisticas(self) -> None:
        tab = self.pestanas.tab("Estadisticas")
        marco_superior = ctk.CTkFrame(tab, bg="#FFFFFF", padx=16, pady=16)
        marco_superior.pack(fill="x", padx=10, pady=10)

        etiqueta = ctk.CTkLabel(marco_superior, text="Comunidad autonoma", bg="#FFFFFF", font=("Arial", 12, "bold"))
        etiqueta.grid(row=0, column=0, sticky="w")

        self.menu_comunidades = ctk.CTkOptionMenu(
            marco_superior,
            self.comunidad_seleccionada,
            "ANDALUCIA",
            "MADRID",
            "CATALUÑA",
        )
        self.menu_comunidades.grid(row=1, column=0, padx=(0, 12), pady=(6, 0), sticky="w")

        boton = ctk.CTkButton(marco_superior, text="Calcular tasa", command=self._mostrar_estadistica)
        boton.grid(row=1, column=1, pady=(6, 0), sticky="w")

        self.texto_estadisticas = ctk.CTkTextbox(tab, height=480, wrap="word")
        self.texto_estadisticas.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _crear_tab_importes(self) -> None:
        tab = self.pestanas.tab("Importes")
        self.texto_importes = ctk.CTkTextbox(tab, height=560, wrap="word")
        self.texto_importes.pack(fill="both", expand=True, padx=10, pady=10)

    def _crear_tab_mensajes(self) -> None:
        tab = self.pestanas.tab("Mensajes")
        self.texto_mensajes = ctk.CTkTextbox(tab, height=560, wrap="word")
        self.texto_mensajes.pack(fill="both", expand=True, padx=10, pady=10)

    def _seleccionar_directorio(self) -> None:
        directorio = filedialog.askdirectory(title="Seleccionar directorio con anexos Excel")
        if directorio:
            self.ruta_datos.set(directorio)
            self._registrar_mensaje("Directorio actualizado correctamente: {0}".format(directorio))

    def _cargar_datos(self) -> None:
        ruta = self.ruta_datos.get().strip()
        self.factoria = Factoria(ruta)
        resultado = self.factoria.cargar()
        if not resultado.exito:
            self.panel_estado.configure(text="Estado: error de carga.")
            self._registrar_mensaje(resultado.mensaje)
            messagebox.showerror("Carga de datos", resultado.mensaje)
            return

        self.gestor_proyectos = resultado.datos["gestor_proyectos"]
        self.gestor_concedidos = resultado.datos["gestor_concedidos"]
        self.gestor_contratos = resultado.datos["gestor_contratos"]

        self.panel_estado.configure(text="Estado: carga completada correctamente.")
        self._actualizar_resumen()
        self._actualizar_estadisticas_disponibles()
        self._actualizar_importes()
        self._registrar_mensaje(resultado.mensaje)
        messagebox.showinfo("Carga de datos", resultado.mensaje)

    def _actualizar_resumen(self) -> None:
        self.tarjetas_resumen["proyectos"].configure(text=str(self.gestor_proyectos.cantidad()))
        self.tarjetas_resumen["concedidos"].configure(text=str(self.gestor_concedidos.cantidad()))
        self.tarjetas_resumen["contratos"].configure(text=str(self.gestor_contratos.cantidad()))

        lineas = []
        lineas.append("Resumen de carga")
        lineas.append("=" * 72)
        lineas.append("Total de proyectos: {0}".format(self.gestor_proyectos.cantidad()))
        lineas.append("Total concedidos: {0}".format(self.gestor_concedidos.cantidad()))
        lineas.append("Total contratos predoctorales: {0}".format(self.gestor_contratos.cantidad()))
        lineas.append("")
        lineas.append("Comunidades detectadas:")
        for comunidad in self.gestor_proyectos.comunidades():
            lineas.append("- {0}".format(comunidad))
        self._escribir_texto(self.texto_resumen, "\n".join(lineas))

    def _actualizar_estadisticas_disponibles(self) -> None:
        comunidades = self.gestor_proyectos.comunidades()
        if len(comunidades) == 0:
            return
        menu = self.menu_comunidades["menu"]
        menu.delete(0, "end")
        for comunidad in comunidades:
            menu.add_command(
                label=comunidad,
                command=tk._setit(self.comunidad_seleccionada, comunidad),
            )
        self.comunidad_seleccionada.set(comunidades[0])
        self._mostrar_estadistica()

    def _mostrar_estadistica(self) -> None:
        if self.gestor_proyectos is None or self.gestor_concedidos is None:
            self._registrar_mensaje("No es posible calcular estadisticas sin haber cargado los datos.")
            return
        resultado = self.gestor_proyectos.calcular_tasa_concedidos(
            self.comunidad_seleccionada.get(),
            self.gestor_concedidos,
        )
        if not resultado.exito:
            self._registrar_mensaje(resultado.mensaje)
            return

        datos = resultado.datos
        lineas = []
        lineas.append("Tasa de proyectos concedidos sobre solicitados")
        lineas.append("=" * 72)
        lineas.append("Comunidad autonoma: {0}".format(datos["comunidad_autonoma"]))
        lineas.append("Solicitados: {0}".format(datos["solicitados"]))
        lineas.append("Concedidos: {0}".format(datos["concedidos"]))
        lineas.append("Tasa de exito: {0}%".format(datos["tasa"]))
        self._escribir_texto(self.texto_estadisticas, "\n".join(lineas))
        self._registrar_mensaje("Estadistica calculada correctamente para {0}.".format(datos["comunidad_autonoma"]))

    def _actualizar_importes(self) -> None:
        if self.gestor_concedidos is None:
            return
        total_global = self.gestor_concedidos.total_importe_global()
        totales_por_comunidad = self.gestor_concedidos.total_importe_por_comunidad()
        lineas = []
        lineas.append("Importes concedidos")
        lineas.append("=" * 72)
        lineas.append("Importe global: {0} EUR".format(self._formatear_decimal(total_global)))
        lineas.append("")
        lineas.append("Importe por comunidad autonoma:")
        for comunidad, importe in totales_por_comunidad.items():
            lineas.append("- {0}: {1} EUR".format(comunidad, self._formatear_decimal(importe)))
        self._escribir_texto(self.texto_importes, "\n".join(lineas))

    def _formatear_decimal(self, valor: Decimal) -> str:
        texto = "{0:,.2f}".format(valor)
        texto = texto.replace(",", "X")
        texto = texto.replace(".", ",")
        texto = texto.replace("X", ".")
        return texto

    def _registrar_mensaje(self, mensaje: str) -> None:
        texto_actual = self.texto_mensajes.get("1.0", "end").strip()
        if texto_actual == "":
            nuevo_texto = mensaje
        else:
            nuevo_texto = texto_actual + "\n" + mensaje
        self._escribir_texto(self.texto_mensajes, nuevo_texto)

    def _escribir_texto(self, widget: ctk.CTkTextbox, contenido: str) -> None:
        widget.delete("1.0", "end")
        widget.insert("1.0", contenido)

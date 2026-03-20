from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from zipfile import ZipFile
import xml.etree.ElementTree as ET

from gestor import GestorProyecto, GestorProyectoConcedido, GestorProyectoContrato, ResultadoOperacion
from proyectos import Proyecto, ProyectoConcedido, ProyectoContrato, ValidacionProyectoError


class Factoria:
    NAMESPACE_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    NAMESPACE_REL = "http://schemas.openxmlformats.org/package/2006/relationships"

    def __init__(self, directorio_datos: Optional[str] = None) -> None:
        if directorio_datos is None:
            self.directorio_datos = self._resolver_directorio_por_defecto()
        else:
            self.directorio_datos = Path(directorio_datos)
        self._mapeo_archivos = {
            "anexo_i": "Anexo I.xlsx",
            "anexo_ii": "Anexo II.xlsx",
            "anexo_iii": "Anexo III.xlsx",
            "anexo_iv": "Anexo IV.xlsx",
        }
        self._ns = {"main": self.NAMESPACE_MAIN, "rel": self.NAMESPACE_REL}

    def _resolver_directorio_por_defecto(self) -> Path:
        base_codigo = Path(__file__).resolve().parent
        candidatos = [
            base_codigo.parent / "data" / "anexos_excel",
            base_codigo.parent / "data",
        ]
        indice = 0
        while indice < len(candidatos):
            candidato = candidatos[indice]
            if candidato.exists():
                return candidato
            indice += 1
        return candidatos[0]

    def cargar(self) -> ResultadoOperacion:
        try:
            rutas = self._resolver_rutas_excel()
            filas_i = self._leer_primera_hoja(rutas["anexo_i"])
            filas_ii = self._leer_primera_hoja(rutas["anexo_ii"])
            filas_iii = self._leer_primera_hoja(rutas["anexo_iii"])
            filas_iv = self._leer_primera_hoja(rutas["anexo_iv"])

            gestor_proyectos = GestorProyecto()
            gestor_concedidos = GestorProyectoConcedido()
            gestor_contratos = GestorProyectoContrato()

            detalles_presupuesto = self._crear_indice_presupuestos(filas_ii)
            detalles_contratos = self._crear_indice_contratos(filas_iv)

            self._cargar_concedidos(filas_i, detalles_presupuesto, detalles_contratos, gestor_proyectos, gestor_concedidos, gestor_contratos)
            self._cargar_denegados(filas_iii, gestor_proyectos)
            self._validar_resultados(gestor_proyectos, gestor_concedidos, gestor_contratos)

            return ResultadoOperacion(
                True,
                "Carga completada correctamente.",
                {
                    "gestor_proyectos": gestor_proyectos,
                    "gestor_concedidos": gestor_concedidos,
                    "gestor_contratos": gestor_contratos,
                    "directorio_datos": str(self.directorio_datos),
                },
            )
        except Exception as error:
            return ResultadoOperacion(False, "Error al cargar los anexos: {0}".format(error))

    def _resolver_rutas_excel(self) -> Dict[str, Path]:
        rutas: Dict[str, Path] = {}
        for clave, nombre in self._mapeo_archivos.items():
            ruta = self.directorio_datos / nombre
            if not ruta.exists():
                ruta_alternativa = self.directorio_datos.parent / nombre
                if ruta_alternativa.exists():
                    ruta = ruta_alternativa
            if not ruta.exists():
                raise FileNotFoundError("No se encontro el archivo requerido: {0}".format(nombre))
            rutas[clave] = ruta
        return rutas

    def _leer_primera_hoja(self, ruta_archivo: Path) -> List[Dict[str, str]]:
        with ZipFile(ruta_archivo) as archivo_zip:
            shared_strings = self._leer_shared_strings(archivo_zip)
            workbook = ET.fromstring(archivo_zip.read("xl/workbook.xml"))
            relaciones = ET.fromstring(archivo_zip.read("xl/_rels/workbook.xml.rels"))
            relacion_por_id = {}
            for relacion in relaciones.findall("rel:Relationship", self._ns):
                relacion_por_id[relacion.attrib["Id"]] = relacion.attrib["Target"]
            hoja = workbook.find("main:sheets", self._ns)[0]
            relacion_id = hoja.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
            destino = "xl/" + relacion_por_id[relacion_id]
            xml_hoja = ET.fromstring(archivo_zip.read(destino))
            filas = self._extraer_filas_hoja(xml_hoja, shared_strings)
        return filas

    def _leer_shared_strings(self, archivo_zip: ZipFile) -> List[str]:
        if "xl/sharedStrings.xml" not in archivo_zip.namelist():
            return []
        raiz = ET.fromstring(archivo_zip.read("xl/sharedStrings.xml"))
        textos = []
        for elemento_si in raiz.findall("main:si", self._ns):
            fragmentos = []
            for texto in elemento_si.iterfind(".//main:t", self._ns):
                fragmentos.append(texto.text or "")
            textos.append("".join(fragmentos))
        return textos

    def _extraer_filas_hoja(self, xml_hoja: ET.Element, shared_strings: List[str]) -> List[Dict[str, str]]:
        sheet_data = xml_hoja.find("main:sheetData", self._ns)
        filas_crudas: List[Dict[str, str]] = []
        for fila in sheet_data.findall("main:row", self._ns):
            valores: Dict[str, str] = {}
            for celda in fila.findall("main:c", self._ns):
                referencia_celda = celda.attrib.get("r", "")
                columna = self._extraer_letras_columna(referencia_celda)
                valor = self._leer_valor_celda(celda, shared_strings)
                valores[columna] = valor
            filas_crudas.append(valores)
        if len(filas_crudas) == 0:
            return []
        cabecera = filas_crudas[0]
        columnas_ordenadas = sorted(cabecera.keys(), key=self._indice_columna_excel)
        nombres_columnas = []
        for columna in columnas_ordenadas:
            nombres_columnas.append(cabecera.get(columna, "").strip())
        filas_finales: List[Dict[str, str]] = []
        indice_fila = 1
        while indice_fila < len(filas_crudas):
            fila_cruda = filas_crudas[indice_fila]
            fila_final: Dict[str, str] = {}
            indice_columna = 0
            while indice_columna < len(columnas_ordenadas):
                letra_columna = columnas_ordenadas[indice_columna]
                nombre_columna = nombres_columnas[indice_columna]
                fila_final[nombre_columna] = fila_cruda.get(letra_columna, "").strip()
                indice_columna += 1
            if self._fila_tiene_datos(fila_final):
                filas_finales.append(fila_final)
            indice_fila += 1
        return filas_finales

    def _leer_valor_celda(self, celda: ET.Element, shared_strings: List[str]) -> str:
        tipo = celda.attrib.get("t")
        valor = celda.find("main:v", self._ns)
        if valor is None or valor.text is None:
            inline = celda.find("main:is", self._ns)
            if inline is not None:
                texto = inline.find("main:t", self._ns)
                if texto is not None and texto.text is not None:
                    return texto.text
            return ""
        if tipo == "s":
            return shared_strings[int(valor.text)]
        return valor.text

    def _extraer_letras_columna(self, referencia_celda: str) -> str:
        letras = []
        for caracter in referencia_celda:
            if caracter.isalpha():
                letras.append(caracter)
            else:
                break
        return "".join(letras)

    def _indice_columna_excel(self, letras: str) -> int:
        indice = 0
        for letra in letras:
            indice = (indice * 26) + (ord(letra.upper()) - ord("A") + 1)
        return indice

    def _fila_tiene_datos(self, fila: Dict[str, str]) -> bool:
        for valor in fila.values():
            if str(valor).strip() != "":
                return True
        return False

    def _crear_indice_presupuestos(self, filas_anexo_ii: List[Dict[str, str]]) -> Dict[str, Dict[str, str]]:
        columnas_obligatorias = [
            "REFERENCIA",
            "CD_COSTES_DIRECTOS",
            "CI_COSTES_INDIRECTOS",
            "ANTICIPO_REEMBOLSABLE",
            "SUBVENCION",
            "SUBVENCION_2025_TOTAL",
            "SUBVENCION_2026",
            "SUBVENCION_2027",
            "SUBVENCION_2028",
            "NUM_CONTRATOS_PREDOC",
        ]
        self._validar_columnas(filas_anexo_ii, columnas_obligatorias, "Anexo II")
        indice: Dict[str, Dict[str, str]] = {}
        for fila in filas_anexo_ii:
            referencia = fila.get("REFERENCIA", "").strip()
            if referencia == "":
                continue
            indice[referencia] = fila
        return indice

    def _crear_indice_contratos(self, filas_anexo_iv: List[Dict[str, str]]) -> Dict[str, Dict[str, str]]:
        columnas_obligatorias = ["REFERENCIA", "TITULO DEL PROYECTO"]
        self._validar_columnas(filas_anexo_iv, columnas_obligatorias, "Anexo IV")
        indice: Dict[str, Dict[str, str]] = {}
        for fila in filas_anexo_iv:
            referencia = fila.get("REFERENCIA", "").strip()
            if referencia == "":
                continue
            indice[referencia] = fila
        return indice

    def _cargar_concedidos(
        self,
        filas_anexo_i: List[Dict[str, str]],
        detalles_presupuesto: Dict[str, Dict[str, str]],
        detalles_contratos: Dict[str, Dict[str, str]],
        gestor_proyectos: GestorProyecto,
        gestor_concedidos: GestorProyectoConcedido,
        gestor_contratos: GestorProyectoContrato,
    ) -> None:
        columnas_obligatorias = [
            "REFERENCIA",
            "AREA",
            "ENTIDAD SOLICITANTE",
            "CCAA Entidad Solicitante",
        ]
        self._validar_columnas(filas_anexo_i, columnas_obligatorias, "Anexo I")
        for fila in filas_anexo_i:
            referencia = fila.get("REFERENCIA", "").strip()
            detalle_presupuesto = detalles_presupuesto.get(referencia)
            if detalle_presupuesto is None:
                raise ValidacionProyectoError(
                    "No existe detalle presupuestario para la referencia concedida '{0}'.".format(referencia)
                )
            proyecto = self._crear_proyecto_desde_concedido(fila, detalle_presupuesto, detalles_contratos.get(referencia))
            self._agregar_o_fallar(gestor_proyectos, proyecto)
            self._agregar_o_fallar(gestor_concedidos, proyecto)
            if isinstance(proyecto, ProyectoContrato):
                self._agregar_o_fallar(gestor_contratos, proyecto)

    def _cargar_denegados(self, filas_anexo_iii: List[Dict[str, str]], gestor_proyectos: GestorProyecto) -> None:
        columnas_obligatorias = [
            "REFERENCIA",
            "AREA",
            "ENTIDAD SOLICITANTE",
            "CCAA Entidad Solicitante",
        ]
        self._validar_columnas(filas_anexo_iii, columnas_obligatorias, "Anexo III")
        for fila in filas_anexo_iii:
            proyecto = Proyecto(
                referencia=fila["REFERENCIA"],
                area=fila["AREA"],
                entidad_solicitante=fila["ENTIDAD SOLICITANTE"],
                comunidad_autonoma=fila["CCAA Entidad Solicitante"],
                concedido=False,
            )
            self._agregar_o_fallar(gestor_proyectos, proyecto)

    def _crear_proyecto_desde_concedido(
        self,
        fila_anexo_i: Dict[str, str],
        fila_anexo_ii: Dict[str, str],
        fila_anexo_iv: Optional[Dict[str, str]],
    ) -> ProyectoConcedido:
        referencia = fila_anexo_i["REFERENCIA"]
        area = fila_anexo_i["AREA"]
        entidad = fila_anexo_i["ENTIDAD SOLICITANTE"]
        comunidad = fila_anexo_i["CCAA Entidad Solicitante"]
        costes_directos = self._a_decimal(fila_anexo_ii["CD_COSTES_DIRECTOS"])
        costes_indirectos = self._a_decimal(fila_anexo_ii["CI_COSTES_INDIRECTOS"])
        anticipo = self._a_decimal(fila_anexo_ii["ANTICIPO_REEMBOLSABLE"])
        subvencion = self._a_decimal(fila_anexo_ii["SUBVENCION"])
        anualidades = [
            self._a_decimal(fila_anexo_ii["SUBVENCION_2025_TOTAL"]),
            self._a_decimal(fila_anexo_ii["SUBVENCION_2026"]),
            self._a_decimal(fila_anexo_ii["SUBVENCION_2027"]),
            self._a_decimal(fila_anexo_ii["SUBVENCION_2028"]),
        ]
        numero_contratos = self._a_entero(fila_anexo_ii["NUM_CONTRATOS_PREDOC"])
        tiene_contrato = numero_contratos > 0 or fila_anexo_iv is not None
        if fila_anexo_iv is not None:
            proyecto = ProyectoContrato(
                referencia=referencia,
                area=area,
                entidad_solicitante=entidad,
                comunidad_autonoma=comunidad,
                costes_directos=costes_directos,
                costes_indirectos=costes_indirectos,
                anticipo=anticipo,
                subvencion=subvencion,
                anualidades=anualidades,
                titulo_del_proyecto=fila_anexo_iv["TITULO DEL PROYECTO"],
                numero_contratos_predoc=numero_contratos if numero_contratos > 0 else 1,
            )
            return proyecto
        proyecto_concedido = ProyectoConcedido(
            referencia=referencia,
            area=area,
            entidad_solicitante=entidad,
            comunidad_autonoma=comunidad,
            costes_directos=costes_directos,
            costes_indirectos=costes_indirectos,
            anticipo=anticipo,
            subvencion=subvencion,
            anualidades=anualidades,
            contratado_predoctoral=tiene_contrato,
            numero_contratos_predoc=numero_contratos,
        )
        return proyecto_concedido

    def _a_decimal(self, valor: str) -> Decimal:
        if valor is None:
            raise ValidacionProyectoError("Se esperaba un valor numerico y se encontro nulo.")
        texto = str(valor).strip()
        if texto == "":
            return Decimal("0.00")
        texto = texto.replace("EUR", "")
        texto = texto.replace(" ", "")
        if "," in texto and "." in texto:
            if texto.rfind(",") > texto.rfind("."):
                texto = texto.replace(".", "")
                texto = texto.replace(",", ".")
            else:
                texto = texto.replace(",", "")
        elif "," in texto:
            texto = texto.replace(",", ".")
        try:
            return Decimal(texto).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError):
            raise ValidacionProyectoError("No se pudo convertir a decimal el valor '{0}'.".format(valor))

    def _a_entero(self, valor: str) -> int:
        decimal_valor = self._a_decimal(valor)
        return int(decimal_valor)

    def _agregar_o_fallar(self, gestor, proyecto) -> None:
        resultado = gestor.agregar(proyecto)
        if not resultado.exito:
            raise ValidacionProyectoError(resultado.mensaje)

    def _validar_columnas(self, filas: List[Dict[str, str]], columnas_obligatorias: List[str], nombre_anexo: str) -> None:
        if len(filas) == 0:
            raise ValidacionProyectoError("El archivo {0} no contiene filas de datos.".format(nombre_anexo))
        columnas_disponibles = list(filas[0].keys())
        for columna in columnas_obligatorias:
            if columna not in columnas_disponibles:
                raise ValidacionProyectoError(
                    "La columna '{0}' no existe en {1}.".format(columna, nombre_anexo)
                )

    def _validar_resultados(
        self,
        gestor_proyectos: GestorProyecto,
        gestor_concedidos: GestorProyectoConcedido,
        gestor_contratos: GestorProyectoContrato,
    ) -> None:
        if gestor_proyectos.cantidad() != 7092:
            raise ValidacionProyectoError(
                "El total de proyectos cargados es {0} y deberia ser 7092.".format(
                    gestor_proyectos.cantidad()
                )
            )
        if gestor_concedidos.cantidad() != 3252:
            raise ValidacionProyectoError(
                "El total de concedidos cargados es {0} y deberia ser 3252.".format(
                    gestor_concedidos.cantidad()
                )
            )
        if gestor_contratos.cantidad() != 1149:
            raise ValidacionProyectoError(
                "El total de contratos cargados es {0} y deberia ser 1149.".format(
                    gestor_contratos.cantidad()
                )
            )
        resultado_coherencia = gestor_concedidos.validar_coherencia()
        if not resultado_coherencia.exito:
            raise ValidacionProyectoError(resultado_coherencia.mensaje)
        resultado_subconjunto = gestor_contratos.validar_subconjunto(gestor_concedidos)
        if not resultado_subconjunto.exito:
            raise ValidacionProyectoError(resultado_subconjunto.mensaje)

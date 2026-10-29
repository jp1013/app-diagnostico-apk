import sqlite3
import time
import math
import os
import shutil
from datetime import datetime
import flet as ft
from fpdf import FPDF

# Compatibilidad Flet < 1.0 y >= 1.0
Boton = getattr(ft, "Button", getattr(ft, "ElevatedButton", None))

# RUTA SEGURA EN ANDROID (Evita el crash de Read-Only File System)
RUTA_DATOS = os.environ.get("FLET_APP_STORAGE_DATA", os.path.abspath("."))
os.makedirs(RUTA_DATOS, exist_ok=True)
DB_NAME = os.path.join(RUTA_DATOS, "diagnosticos_moviles.db")

# ==========================================
# 1. BASE DE DATOS LOCAL (SQLite en Android)
# ==========================================
def inicializar_bd():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS diagnosticos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            modelo TEXT,
            imei TEXT,
            cpu_ms REAL,
            disco_pct REAL,
            bateria_pct REAL,
            temp_c REAL,
            touch_estado TEXT,
            estado_general TEXT,
            alertas TEXT
        )
        """
    )
    conn.commit()
    conn.close()

def guardar_diagnostico_bd(d):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO diagnosticos (
            fecha, modelo, imei, cpu_ms, disco_pct,
            bateria_pct, temp_c, touch_estado, estado_general, alertas
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            d["fecha"],
            d["modelo"],
            d["imei"],
            d["cpu_ms"],
            d["disco_pct"],
            d["bateria_pct"],
            d["temp_c"],
            d["touch_estado"],
            d["estado_general"],
            d["alertas"],
        ),
    )
    conn.commit()
    conn.close()

def obtener_historial_bd():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM diagnosticos ORDER BY id DESC")
    filas = cursor.fetchall()
    conn.close()
    return filas

# ==========================================
# 2. GENERADOR DE PDF EN MEMORIA DEL CELULAR
# ==========================================
def generar_reporte_pdf(reg):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(0, 10, "CERTIFICADO TECNICO DE DIAGNOSTICO MOVIL", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 8, f"Reporte #{reg[0]} | Fecha: {reg[1]}", ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, f"Equipo: {reg[2]} (IMEI: {reg[3]})", ln=True)
    pdf.cell(0, 8, f"Dictamen: {reg[9]}", ln=True)
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, f"- Test Estres CPU: {reg[4]} ms", ln=True)
    pdf.cell(0, 7, f"- Almacenamiento Ocupado: {reg[5]}%", ln=True)
    pdf.cell(0, 7, f"- Salud de Bateria: {reg[6]}%", ln=True)
    pdf.cell(0, 7, f"- Temperatura en Carga: {reg[7]} C", ln=True)
    pdf.cell(0, 7, f"- Pantalla Tactil / Sensores: {reg[8]}", ln=True)
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Alertas Detectadas:", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6, f"{reg[10]}")
    nombre_pdf = os.path.join(RUTA_DATOS, f"Reporte_{reg[3]}_{reg[0]}.pdf")
    pdf.output(nombre_pdf)
    return nombre_pdf

# ==========================================
# 3. INTERFAZ MÓVIL (FLET)
# ==========================================
def main(page: ft.Page):
    inicializar_bd()
    page.title = "MobileTech Diagnóstico"
    page.padding = 15
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = ft.ScrollMode.AUTO

    txt_modelo = ft.TextField(label="Marca y Modelo (Ej: Redmi Note 13)")
    txt_imei = ft.TextField(label="IMEI o Serial")
    slider_bateria = ft.Slider(min=10, max=100, divisions=18, value=85, label="{value}%")
    slider_temp = ft.Slider(min=25, max=60, divisions=35, value=36, label="{value}°C")
    sw_touch = ft.Switch(label="Pantalla Táctil OK", value=True)
    barra_progreso = ft.ProgressBar(visible=False)
    txt_alerta = ft.Text("", weight=ft.FontWeight.BOLD, size=13)
    panel_alerta = ft.Container(content=txt_alerta, padding=10, border_radius=8, visible=False)
    lista_historial = ft.Column(spacing=10)

    def mostrar_dialogo(titulo, mensaje, critico=False):
        panel_alerta.visible = True
        panel_alerta.bgcolor = ft.Colors.RED_100 if critico else ft.Colors.GREEN_100
        txt_alerta.color = ft.Colors.RED_900 if critico else ft.Colors.GREEN_900
        txt_alerta.value = f"{titulo}\n{mensaje}"
        dlg = ft.AlertDialog(
            title=ft.Text(titulo, weight=ft.FontWeight.BOLD),
            content=ft.Text(mensaje, selectable=True),
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def ejecutar_test(e):
        if not txt_modelo.value.strip() or not txt_imei.value.strip():
            mostrar_dialogo("⚠️ Datos Incompletos", "Ingresa el Modelo y el IMEI.", True)
            return

        barra_progreso.visible = True
        page.update()

        # 1. Estrés real de CPU en el procesador del celular
        inicio = time.perf_counter()
        acum = 0.0
        for i in range(1, 1500000):
            acum += math.sqrt(i) * math.sin(i)
        cpu_ms = round((time.perf_counter() - inicio) * 1000, 2)

        # 2. Lectura nativa de almacenamiento del teléfono (sin librerías C)
        uso_disco = shutil.disk_usage(RUTA_DATOS)
        disco_pct = round((uso_disco.used / uso_disco.total) * 100, 1)

        bat = round(slider_bateria.value, 1)
        temp = round(slider_temp.value, 1)
        touch = "Funcional" if sw_touch.value else "Fallo Tactil"

        # 3. Evaluación de Alertas Locales
        alertas = []
        if cpu_ms > 550:
            alertas.append(f"CPU lenta ({cpu_ms}ms)")
        if temp >= 42:
            alertas.append(f"Sobrecalentamiento ({temp}°C)")
        if bat < 75:
            alertas.append(f"Bateria degradada ({bat}%)")
        if disco_pct > 90:
            alertas.append(f"Memoria llena ({disco_pct}%)")
        if not sw_touch.value:
            alertas.append("Fallo en pantalla tactil")

        es_critico = len(alertas) > 0
        estado = "RECHAZADO / FALLO" if es_critico else "APROBADO / OPTIMO"
        detalle_alertas = " | ".join(alertas) if es_critico else "Sin anomalias."

        guardar_diagnostico_bd({
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "modelo": txt_modelo.value.strip(),
            "imei": txt_imei.value.strip(),
            "cpu_ms": cpu_ms,
            "disco_pct": disco_pct,
            "bateria_pct": bat,
            "temp_c": temp,
            "touch_estado": touch,
            "estado_general": estado,
            "alertas": detalle_alertas,
        })

        barra_progreso.visible = False
        cargar_historial()
        mostrar_dialogo(estado, f"CPU: {cpu_ms}ms | Disco: {disco_pct}%\n{detalle_alertas}", es_critico)

    def exportar_pdf(reg):
        ruta = generar_reporte_pdf(reg)
        resumen = (
            f"✅ Archivo PDF generado exitosamente.\n\n"
            f"📄 Vista previa del Certificado:\n"
            f"• Equipo: {reg[2]} (IMEI: {reg[3]})\n"
            f"• Estado: {reg[9]}\n"
            f"• CPU: {reg[4]} ms | Disco: {reg[5]}%\n"
            f"• Batería: {reg[6]}% | Temp: {reg[7]}°C\n"
            f"• Hallazgos: {reg[10]}\n\n"
            f"📂 Guardado en almacenamiento interno:\n{ruta}"
        )
        mostrar_dialogo("Certificado PDF Exportado", resumen, False)

    def cargar_historial():
        lista_historial.controls.clear()
        for r in obtener_historial_bd():
            fallo = "RECHAZADO" in r[9]
            color = ft.Colors.RED_600 if fallo else ft.Colors.GREEN_700
            lista_historial.controls.append(
                ft.Card(
                    content=ft.Container(
                        padding=12,
                        content=ft.Column([
                            ft.Text(f"📱 {r[2]} ({r[3]})", weight=ft.FontWeight.BOLD),
                            ft.Text(r[9], color=color, weight=ft.FontWeight.BOLD, size=12),
                            ft.Text(f"CPU: {r[4]}ms | Disco: {r[5]}% | Bat: {r[6]}% | {r[7]}°C", size=12),
                            ft.Text(f"Alerta: {r[10]}", size=11),
                            Boton(
                                "Exportar PDF",
                                icon=ft.Icons.PICTURE_AS_PDF,
                                on_click=lambda e, item=r: exportar_pdf(item),
                            ),
                        ]),
                    )
                )
            )
        page.update()

    page.add(
        ft.Text("🔬 Diagnóstico y Estrés Móvil", size=20, weight=ft.FontWeight.BOLD),
        txt_modelo,
        txt_imei,
        ft.Text("Salud de Batería (%):", size=12),
        slider_bateria,
        ft.Text("Temperatura (°C):", size=12),
        slider_temp,
        sw_touch,
        Boton("Ejecutar Test de Estrés", icon=ft.Icons.SPEED, on_click=ejecutar_test),
        barra_progreso,
        panel_alerta,
        ft.Divider(),
        ft.Text("📂 Historial SQLite:", weight=ft.FontWeight.BOLD),
        lista_historial,
    )
    cargar_historial()

if hasattr(ft, "run"):
    ft.run(main)
else:
    ft.app(target=main)
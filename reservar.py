"""
Automatización de reserva en Gonnet Box (TurnosWeb)
Versión multi-usuario — lee la lista de alumnos desde una Google Sheet
(alimentada por un Google Form).
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
import pytz
import gspread
from google.oauth2.service_account import Credentials

# ── Configuración general ──────────────────────────────────────────────────────
BASE_URL  = "https://gonnetbox.turnosweb.com"
AGENDA    = "0_227_0"
TIMEZONE  = pytz.timezone("America/Argentina/Buenos_Aires")

# ID de la Google Sheet (lo que aparece en la URL entre /d/ y /edit)
# Ej: https://docs.google.com/spreadsheets/d/ESTE_ES_EL_ID/edit
SHEET_ID = os.environ.get("SHEET_ID", "")

# Nombres exactos de las columnas tal como las generó el Google Form
COL_NOMBRE = "Nombre completo"
COL_EMAIL  = "Email de TurnosWeb"
COL_PASS   = "Contraseña de TurnosWeb"
COL_HORA   = "Hora de clase preferida"   # formato esperado en la Sheet: "08:00"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "es-AR,es;q=0.9",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": BASE_URL + "/",
    "Origin": BASE_URL,
}


# ── Helpers generales ──────────────────────────────────────────────────────────
def log(msg, usuario=""):
    ts = datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
    prefix = f"[{usuario}] " if usuario else ""
    print(f"[{ts}] {prefix}{msg}")

def manana_str():
    return (datetime.now(TIMEZONE) + timedelta(days=1)).strftime("%Y%m%d")

def hora_a_codigo(hora_texto: str) -> str:
    """Convierte '08:00' -> '080000'. Si ya viene como '080000', la deja igual."""
    hora_texto = hora_texto.strip()
    if ":" in hora_texto:
        partes = hora_texto.split(":")
        hh = partes[0].zfill(2)
        mm = partes[1].zfill(2) if len(partes) > 1 else "00"
        return f"{hh}{mm}00"
    return hora_texto.zfill(6)


# ── Carga de usuarios desde Google Sheets ──────────────────────────────────────
def cargar_usuarios_desde_sheet() -> list:
    raw = os.environ.get("GOOGLE_CREDENTIALS")
    if not raw:
        log("❌ Secret GOOGLE_CREDENTIALS no encontrado")
        sys.exit(1)

    creds_dict = json.loads(raw)
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )
    gc = gspread.authorize(creds)

    if not SHEET_ID:
        log("❌ Secret SHEET_ID no encontrado")
        sys.exit(1)

    try:
        sheet = gc.open_by_key(SHEET_ID).sheet1
    except gspread.exceptions.APIError as e:
        log(f"❌ Error abriendo la Sheet (ID='{SHEET_ID}'): {e}")
        sys.exit(1)

    filas = sheet.get_all_records()
    usuarios = []
    for fila in filas:
        nombre = str(fila.get(COL_NOMBRE, "")).strip()
        email = str(fila.get(COL_EMAIL, "")).strip()
        password = str(fila.get(COL_PASS, "")).strip()
        hora_raw = str(fila.get(COL_HORA, "")).strip()

        if not (nombre and email and password and hora_raw):
            log(f"⚠️  Fila incompleta, se omite: {fila}")
            continue

        usuarios.append({
            "nombre": nombre,
            "email": email,
            "password": password,
            "hora": hora_a_codigo(hora_raw),
        })

    log(f"👥 {len(usuarios)} usuarios cargados desde la Sheet")
    return usuarios


# ── Lógica de reserva (idéntica a la versión TW_USUARIOS) ─────────────────────
def init_session(session: requests.Session):
    session.get(BASE_URL, timeout=30)

def login(session: requests.Session, email: str, password: str, nombre: str) -> bool:
    r = session.post(
        f"{BASE_URL}/web/loginajax",
        data={"user": email, "pass": password},
        headers=HEADERS,
        timeout=30,
    )
    try:
        data = r.json()
    except Exception:
        log(f"❌ Login falló (respuesta no es JSON): {r.text[:300]}", nombre)
        return False

    if data.get("ok") == 1 and data.get("fullname"):
        log(f"✅ Login OK — {data.get('fullname2', email)}", nombre)
        return True

    log(f"❌ Login rechazado: {data}", nombre)
    return False

def obtener_clases(session: requests.Session, fecha: str, nombre: str) -> list:
    r = session.post(
        f"{BASE_URL}/web/calendar",
        data={"ft": 1, "dateform": fecha, "agenda": AGENDA},
        headers=HEADERS,
        timeout=30,
    )
    try:
        data = r.json()
    except Exception as e:
        log(f"❌ Error obteniendo clases: {e} — {r.text[:300]}", nombre)
        return []

    clases = []
    for line in data.get("lines", []):
        clases.extend(line.get("data", []))
    log(f"📋 {len(clases)} clases encontradas para {fecha}", nombre)
    return clases

def encontrar_clase(clases: list, fecha: str, hora: str, nombre: str):
    target_prefix = f"227_{fecha}_{hora}"
    for c in clases:
        if c.get("id", "").startswith(target_prefix):
            log(f"🎯 Clase encontrada: {c['dia']} — {c['name']} "
                f"(lugares: {c['disp']})", nombre)
            if int(c.get("disp", 0)) == 0:
                log("⚠️  Sin lugares disponibles", nombre)
                return None
            return c
    log(f"ℹ️  No hay clase a las {hora[:2]}:{hora[2:4]} para {fecha}. "
        f"Se omite sin error.", nombre)
    return None

def reservar(session: requests.Session, clase: dict, nombre: str) -> bool:
    reserva_id = f"{clase['id']}_{clase['idt']}"
    r = session.post(
        f"{BASE_URL}/web/reservar",
        data={"id": reserva_id},
        headers=HEADERS,
        timeout=30,
    )
    try:
        data = r.json()
    except Exception as e:
        log(f"❌ Error al reservar: {e} — {r.text[:300]}", nombre)
        return False

    if data.get("ok") == 1:
        log(f"✅ Reserva confirmada: {data['t_smldate']} — {data['name']}", nombre)
        return True

    log(f"❌ Reserva rechazada: err={data.get('err')}", nombre)
    return False

def procesar_usuario(usuario: dict, fecha: str) -> bool:
    nombre, email, password, hora = (
        usuario["nombre"], usuario["email"], usuario["password"], usuario["hora"]
    )
    log("--- Procesando usuario ---", nombre)

    with requests.Session() as session:
        init_session(session)
        if not login(session, email, password, nombre):
            return False
        clases = obtener_clases(session, fecha, nombre)
        if not clases:
            return False
        clase = encontrar_clase(clases, fecha, hora, nombre)
        if not clase:
            return True   # no había clase ese día, no es un error
        return reservar(session, clase, nombre)


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    log("=== Iniciando proceso de reserva (Google Sheets) ===")
    fecha = manana_str()
    log(f"Fecha objetivo: {fecha}")

    usuarios = cargar_usuarios_desde_sheet()
    if not usuarios:
        log("⚠️  No hay usuarios para procesar")
        sys.exit(0)

    resultados = []
    for usuario in usuarios:
        ok = procesar_usuario(usuario, fecha)
        resultados.append((usuario["nombre"], ok))

    print()
    log("=== Resumen ===")
    for nombre, ok in resultados:
        log(f"{'✅' if ok else '❌'} {nombre}")

    fallos = [n for n, ok in resultados if not ok]
    if fallos:
        log(f"❌ {len(fallos)} usuario(s) fallaron: {', '.join(fallos)}")
        sys.exit(1)

    log("=== Todos los usuarios procesados correctamente ===")


if __name__ == "__main__":
    main()

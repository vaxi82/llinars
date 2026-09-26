import requests
import json
import sys
import os
import re
from datetime import datetime, date

# ============================================================
# CONFIGURACIÓN — API real de la FCF (confirmada por inspección directa)
# GET https://www.fcf.cat/api/competition/partidos?grupId=XXXX
# Devuelve un DICCIONARIO agrupado por jornada:
#   { "1": [ {partido...}, {partido...} ], "2": [ ... ], ... }
# Cada partido usa estos campos (confirmados):
#   NOMBRE_CASA, NOMBRE_FUERA, ESCUDO_CASA, ESCUDO_FUERA,
#   CAMPO, COMIENZO1 ("YYYY-MM-DD HH:MM:SS"), CODEQUIPO_CASA, CODEQUIPO_FUERA
# ============================================================
JUGADORES = [
    {
        "jugador": "Erik",
        "categoria": "Infantil A",
        "api": "https://www.fcf.cat/api/competition/partidos?grupId=58162479",
        "url_web": "https://www.fcf.cat/ca/competicio?temporadaId=22&disciplinaId=19308233&competicioId=58162474&grupId=58162479"
    },
    {
        "jugador": "Biel",
        "categoria": "Benjamí B",
        "api": "https://www.fcf.cat/api/competition/partidos?grupId=60364101",
        "url_web": "https://www.fcf.cat/ca/competicio?temporadaId=22&disciplinaId=19308235&competicioId=58162174&grupId=60364101"
    }
]

CLUB = "LLINARS"
ESCUDO_CLUB_URL = "https://www.fcf.cat/img/escudos/club_08027.png"
ESCUDO_CLUB_LOCAL = "escudos/club_08027.png"
CAMPO_CASA = "Camp Municipal de Llinars del Vallès"

# Prefijo para reconstruir la URL completa de los escudos.
# ESCUDO_CASA / ESCUDO_FUERA solo traen el nombre del fichero
# (p.ej. "00100_0001223430_LLINARS.png"), así que lo anteponemos.
BASE_ESCUDOS = "https://www.fcf.cat/img/escudos/"

ESCUDOS_DIR = "escudos"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36",
    "Accept": "application/json, */*",
    "Accept-Language": "es-ES,es;q=0.9",
    "Referer": "https://www.fcf.cat/ca/competicio",
}

# Caché en memoria de esta ejecución: url remota -> ruta local (o la propia
# url remota si la descarga falla, para no romper el build).
_cache_escudos = {}


def _nombre_seguro(nombre):
    """Convierte el nombre de fichero de la FCF en algo seguro para el filesystem."""
    nombre = nombre.split("?")[0]
    nombre = os.path.basename(nombre)
    nombre = re.sub(r"[^A-Za-z0-9._-]", "_", nombre)
    return nombre or "escudo.png"


def descargar_escudo(url_remota):
    """Descarga un escudo a escudos/ y devuelve la ruta relativa.
    Si falla la descarga, devuelve la URL remota como último recurso."""
    if url_remota in _cache_escudos:
        return _cache_escudos[url_remota]

    nombre = _nombre_seguro(url_remota)
    ruta_local = f"{ESCUDOS_DIR}/{nombre}"

    if os.path.exists(ruta_local):
        _cache_escudos[url_remota] = ruta_local
        return ruta_local

    try:
        res = requests.get(url_remota, headers=headers, timeout=15)
        if res.status_code == 200 and res.content:
            os.makedirs(ESCUDOS_DIR, exist_ok=True)
            with open(ruta_local, "wb") as f:
                f.write(res.content)
            _cache_escudos[url_remota] = ruta_local
            return ruta_local
    except Exception:
        pass

    # Descarga fallida: mejor un enlace remoto roto (con fallback en el HTML)
    # que un build que se detiene por completo.
    _cache_escudos[url_remota] = url_remota
    return url_remota


def escudo_url(nombre_fichero):
    if not nombre_fichero:
        remota = ESCUDO_CLUB_URL
    else:
        nombre_fichero = str(nombre_fichero)
        remota = nombre_fichero if nombre_fichero.startswith("http") else BASE_ESCUDOS + nombre_fichero
    return descargar_escudo(remota)


def parse_comienzo(txt):
    """COMIENZO1 viene como 'YYYY-MM-DD HH:MM:SS'. Devuelve (date, 'HH:MM')."""
    if not txt:
        return None, ""
    txt = str(txt).strip()
    try:
        dt = datetime.strptime(txt, "%Y-%m-%d %H:%M:%S")
        return dt.date(), dt.strftime("%H:%M")
    except ValueError:
        try:
            dt = datetime.fromisoformat(txt)
            return dt.date(), dt.strftime("%H:%M")
        except ValueError:
            return None, ""


def es_partido_llinars(partido):
    # Descarta jornadas de descanso (equipo "-1" / "Descans"): no son partidos reales.
    if partido.get("CODEQUIPO_CASA") == "-1" or partido.get("CODEQUIPO_FUERA") == "-1":
        return False
    loc = partido.get("NOMBRE_CASA", "") or ""
    vis = partido.get("NOMBRE_FUERA", "") or ""
    return CLUB in (loc + " " + vis).upper()


def extrae_partidos(data, jugador, categoria, url_web):
    """data es un dict {jornada: [partidos]}."""
    acumulados = []
    for jornada, partidos in data.items():
        if not isinstance(partidos, list):
            continue
        for p in partidos:
            if not isinstance(p, dict):
                continue
            if not es_partido_llinars(p):
                continue

            loc = p.get("NOMBRE_CASA", "")
            vis = p.get("NOMBRE_FUERA", "")
            es_local = CLUB in loc.upper()
            f_date, hora = parse_comienzo(p.get("COMIENZO1"))

            acumulados.append({
                "jugador": jugador,
                "categoria": categoria,
                "jornada": jornada,
                "equipo_local": loc,
                "equipo_visitante": vis,
                "escudo_local": escudo_url(p.get("ESCUDO_CASA")),
                "escudo_visitante": escudo_url(p.get("ESCUDO_FUERA")),
                "es_local": es_local,
                "fecha": f_date.isoformat() if f_date else "Fecha por determinar",
                "hora": hora,
                "campo": p.get("CAMPO") or (CAMPO_CASA if es_local else f"Campo de {vis if es_local else loc}"),
                "url": url_web,
                "_fecha_date": f_date,
            })
    return acumulados


def main():
    hoy = date.today()
    partidos = []
    errores = []

    # Se descarga siempre, aunque ningún partido lo necesite: lo usa
    # el <link rel="apple-touch-icon"> del index.html para el acceso directo.
    descargar_escudo(ESCUDO_CLUB_URL)

    for eq in JUGADORES:
        try:
            res = requests.get(eq["api"], headers=headers, timeout=25)
            if res.status_code != 200:
                errores.append(f"{eq['jugador']}: HTTP {res.status_code}")
                continue
            data = res.json()

            if not isinstance(data, dict):
                errores.append(f"{eq['jugador']}: formato de respuesta inesperado ({type(data)})")
                continue

            encontrados = extrae_partidos(data, eq["jugador"], eq["categoria"], eq["url_web"])

            # Solo partidos futuros; si no hay, el último jugado
            futuros = [p for p in encontrados if p["_fecha_date"] and p["_fecha_date"] >= hoy]
            futuros.sort(key=lambda p: p["_fecha_date"])
            if not futuros and encontrados:
                con_fecha = [p for p in encontrados if p["_fecha_date"]]
                con_fecha.sort(key=lambda p: p["_fecha_date"])
                futuros = con_fecha[-1:]
            if not futuros:
                muestra = json.dumps(data, ensure_ascii=False)[:1500]
                print(f"DIAGNÓSTICO {eq['jugador']} — estructura recibida:")
                print(muestra)
                errores.append(f"{eq['jugador']}: la API respondió pero sin partidos de {CLUB}")

            partidos.extend(futuros)
        except Exception as e:
            errores.append(f"{eq['jugador']}: {e}")

    for p in partidos:
        del p["_fecha_date"]

    if not partidos:
        print("ERROR — no se pudo extraer ningún partido real:")
        for e in errores:
            print("  -", e)
        sys.exit(1)

    with open("partidos.json", "w", encoding="utf-8") as f:
        json.dump(partidos, f, ensure_ascii=False, indent=2)

    print(f"OK: {len(partidos)} partidos guardados")
    for p in partidos:
        print(f"  - {p['jugador']}: {p['equipo_local']} vs {p['equipo_visitante']} | {p['fecha']} {p['hora']} (J{p['jornada']})")


if __name__ == "__main__":
    main()

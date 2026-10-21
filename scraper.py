import requests
try:
    from curl_cffi import requests as cffi_requests
except ImportError:
    cffi_requests = None
import json
import sys
import os
import re
from datetime import datetime, date

# ============================================================
# CONFIGURACIÓN
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
BASE_ESCUDOS = "https://www.fcf.cat/img/escudos/"
ESCUDOS_DIR = "escudos"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, image/*,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,ca;q=0.8",
    "Referer": "https://www.fcf.cat/ca/competicio",
}

_cache_escudos = {}

def _nombre_seguro(nombre):
    nombre = str(nombre or "").split("?")[0]
    nombre = os.path.basename(nombre)
    nombre = re.sub(r"[^A-Za-z0-9._-]", "_", nombre)
    if not nombre:
        return "escudo.png"
    return nombre

def construir_url_escudo(valor):
    if not valor:
        return None
    valor = str(valor).strip()
    if not valor:
        return None
    if valor.startswith("http://") or valor.startswith("https://"):
        return valor
    return BASE_ESCUDOS + valor.lstrip("/")

def descargar_escudo(url_remota):
    if not url_remota:
        return ESCUDO_CLUB_LOCAL
    if url_remota in _cache_escudos:
        return _cache_escudos[url_remota]
    nombre = _nombre_seguro(url_remota)
    ruta_local = os.path.join(ESCUDOS_DIR, nombre)
    if os.path.isfile(ruta_local) and os.path.getsize(ruta_local) > 0:
        ruta_relativa = ruta_local.replace("\\", "/")
        _cache_escudos[url_remota] = ruta_relativa
        print(f"ESCUDO OK (local): {ruta_relativa}")
        return ruta_relativa
    try:
        print(f"Descargando escudo: {url_remota}")
        res = requests.get(url_remota, headers=headers, timeout=20)
        content_type = res.headers.get("Content-Type", "").lower()
        if (res.status_code == 200 and res.content and
            ("image" in content_type or url_remota.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".svg")))):
            os.makedirs(ESCUDOS_DIR, exist_ok=True)
            with open(ruta_local, "wb") as f:
                f.write(res.content)
            ruta_relativa = ruta_local.replace("\\", "/")
            _cache_escudos[url_remota] = ruta_relativa
            print(f"ESCUDO GUARDADO: {ruta_relativa} ({len(res.content)} bytes)")
            return ruta_relativa
    except Exception as e:
        print(f"AVISO: error descargando {url_remota}: {e}")
    print(f"FALLBACK URL REMOTA: {url_remota}")
    _cache_escudos[url_remota] = url_remota
    return url_remota

def escudo_url(valor):
    url_remota = construir_url_escudo(valor)
    if not url_remota:
        return ESCUDO_CLUB_LOCAL
    return descargar_escudo(url_remota)

def parse_comienzo(txt):
    if not txt:
        return None, ""
    txt = str(txt).strip()
    try:
        dt = datetime.strptime(txt, "%Y-%m-%d %H:%M:%S")
        return dt.date(), dt.strftime("%H:%M")
    except ValueError:
        pass
    try:
        dt = datetime.fromisoformat(txt)
        return dt.date(), dt.strftime("%H:%M")
    except ValueError:
        return None, ""

def es_partido_llinars(partido):
    if partido.get("CODEQUIPO_CASA") == "-1":
        return False
    if partido.get("CODEQUIPO_FUERA") == "-1":
        return False
    loc = partido.get("NOMBRE_CASA", "") or ""
    vis = partido.get("NOMBRE_FUERA", "") or ""
    return CLUB in (loc + " " + vis).upper()

def extrae_partidos(data, jugador, categoria, url_web):
    acumulados = []
    for jornada, partidos in data.items():
        if not isinstance(partidos, list):
            continue
        for p in partidos:
            if not isinstance(p, dict):
                continue
            if not es_partido_llinars(p):
                continue
            loc = p.get("NOMBRE_CASA", "") or ""
            vis = p.get("NOMBRE_FUERA", "") or ""
            es_local = CLUB in loc.upper()
            f_date, hora = parse_comienzo(p.get("COMIENZO1"))
            escudo_local = escudo_url(p.get("ESCUDO_CASA"))
            escudo_visitante = escudo_url(p.get("ESCUDO_FUERA"))
            acumulados.append({
                "jugador": jugador,
                "categoria": categoria,
                "jornada": jornada,
                "equipo_local": loc,
                "equipo_visitante": vis,
                "escudo_local": escudo_local,
                "escudo_visitante": escudo_visitante,
                "es_local": es_local,
                "fecha": f_date.isoformat() if f_date else "Fecha por determinar",
                "hora": hora,
                "campo": p.get("CAMPO") or (CAMPO_CASA if es_local else f"Campo de {vis}"),
                "url": url_web,
                "_fecha_date": f_date,
            })
    return acumulados

def get_con_reintentos(url, timeout=25):
    """Intenta primero como Chrome real (curl_cffi) y luego con requests.
    Si el WAF responde 403 no insiste mucho: es un bloqueo, no un fallo puntual."""
    import time
    intentos = []
    if cffi_requests is not None:
        intentos.append(("curl_cffi/chrome", lambda: cffi_requests.get(
            url, impersonate="chrome", timeout=timeout,
            headers={"Accept": "application/json, text/plain, */*",
                     "Accept-Language": "ca-ES,ca;q=0.9,es;q=0.8",
                     "Referer": "https://www.fcf.cat/ca/competicio"})))
    intentos.append(("requests", lambda: requests.get(url, headers=headers, timeout=timeout)))
    intentos.append(("requests (reintento)", lambda: requests.get(url, headers=headers, timeout=timeout)))
    ultimo = None
    for n, (nombre, fn) in enumerate(intentos, 1):
        try:
            res = fn()
            print(f"[{n}/{len(intentos)}] {nombre}: GET {url} -> HTTP {res.status_code} ({len(res.content)} bytes)")
            if res.status_code == 200:
                return res
            print("   Body:", res.text[:150].replace("\n", " "))
            ultimo = res
        except Exception as e:
            print(f"[{n}/{len(intentos)}] {nombre}: ERROR {e}")
        time.sleep(3)
    return ultimo

ENTRADA_DIR = "entrada"

def leer_entrada(jugador):
    """Lee el JSON más reciente que el iPhone subió a entrada/<jugador>-<fecha>.json.
    Devuelve (data, [ficheros usados]) o (None, [])."""
    import glob
    ficheros = sorted(glob.glob(os.path.join(ENTRADA_DIR, f"{jugador.lower()}-*.json")))
    if not ficheros:
        return None, []
    try:
        with open(ficheros[-1], encoding="utf-8") as f:
            data = json.load(f)
        print(f"Usando datos subidos desde el iPhone: {ficheros[-1]}")
        return data, ficheros
    except Exception as e:
        print(f"AVISO: no se pudo leer {ficheros[-1]}: {e}")
        return None, ficheros

def main():
    hoy = date.today()
    partidos = []
    errores = []
    usados = []
    sin_datos_nuevos = []
    os.makedirs(ESCUDOS_DIR, exist_ok=True)

    antiguos = []
    if os.path.isfile("partidos.json"):
        try:
            with open("partidos.json", encoding="utf-8") as f:
                antiguos = json.load(f)
        except Exception:
            antiguos = []

    for eq in JUGADORES:
        print(f"\n{'='*70}\nProcesando {eq['jugador']} ({eq['categoria']})\n{'='*70}")
        try:
            data, ficheros = leer_entrada(eq["jugador"])
            usados.extend(ficheros)
            if data is None:
                res = get_con_reintentos(eq["api"])
                if res is None or res.status_code != 200:
                    errores.append(f"{eq['jugador']}: HTTP {getattr(res, 'status_code', 'sin respuesta')}")
                    sin_datos_nuevos.append(eq["jugador"])
                    continue
                try:
                    data = res.json()
                except ValueError:
                    errores.append(f"{eq['jugador']}: la respuesta no es JSON: {res.text[:200]!r}")
                    sin_datos_nuevos.append(eq["jugador"])
                    continue
            if not isinstance(data, dict):
                errores.append(f"{eq['jugador']}: formato inesperado ({type(data)})")
                sin_datos_nuevos.append(eq["jugador"])
                continue
            encontrados = extrae_partidos(data, eq["jugador"], eq["categoria"], eq["url_web"])
            futuros = [p for p in encontrados if p["_fecha_date"] and p["_fecha_date"] >= hoy]
            futuros.sort(key=lambda p: p["_fecha_date"])
            if not futuros and encontrados:
                con_fecha = [p for p in encontrados if p["_fecha_date"]]
                con_fecha.sort(key=lambda p: p["_fecha_date"])
                futuros = con_fecha[-1:]
            if not futuros:
                errores.append(f"{eq['jugador']}: no hay partidos de {CLUB}")
                sin_datos_nuevos.append(eq["jugador"])
            partidos.extend(futuros)
        except Exception as e:
            errores.append(f"{eq['jugador']}: {e}")
            sin_datos_nuevos.append(eq["jugador"])

    for p in partidos:
        p.pop("_fecha_date", None)

    # Jugadores sin datos nuevos: conservar lo que ya había en partidos.json
    for nombre in sin_datos_nuevos:
        previos = [p for p in antiguos if p.get("jugador") == nombre]
        if previos:
            print(f"Conservando {len(previos)} partidos anteriores de {nombre}")
            partidos.extend(previos)

    hay_nuevos = len(sin_datos_nuevos) < len(JUGADORES)
    if not partidos or not hay_nuevos:
        print("\nNo se obtuvieron datos nuevos:")
        for e in errores:
            print("  -", e)
        if antiguos:
            print("::warning title=Scraper bloqueado::No se pudo actualizar; se mantiene el partidos.json anterior. " + " | ".join(errores))
            sys.exit(0)
        sys.exit(1)

    with open("partidos.json", "w", encoding="utf-8") as f:
        json.dump(partidos, f, ensure_ascii=False, indent=2)
    for fich in usados:           # los ficheros de entrada ya están procesados
        try:
            os.remove(fich)
        except OSError:
            pass
    print(f"\n{'='*70}\nOK: {len(partidos)} partidos guardados\n{'='*70}")
    for p in partidos:
        print(f"- {p['jugador']}: {p['equipo_local']} vs {p['equipo_visitante']} | {p['fecha']} {p['hora']} | J{p['jornada']}")
    if errores:
        print("\nAVISOS:")
        for e in errores:
            print(f"  - {e}")

if __name__ == "__main__":
    main()

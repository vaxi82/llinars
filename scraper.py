import requests
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
    "Accept": "image/*,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,ca;q=0.8",
    "Referer": "https://www.fcf.cat/ca/competicio",
}

_cache_escudos = {}

# ============================================================
# UTILIDADES DE ESCUDOS
# ============================================================
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

    # 1. Si ya existe localmente, usarlo
    if os.path.isfile(ruta_local) and os.path.getsize(ruta_local) > 0:
        ruta_relativa = ruta_local.replace("\\", "/")
        _cache_escudos[url_remota] = ruta_relativa
        print(f"ESCUDO OK (local): {ruta_relativa}")
        return ruta_relativa

    # 2. Intentar descargarlo
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
            print(f"ESCUDO GUARDADO: {ruta_relativa}")
            return ruta_relativa
    except Exception as e:
        print(f"AVISO: error descargando {url_remota}: {e}")

    # 3. FALLBACK: URL remota (el HTML manejará el error si no carga)
    print(f"FALLBACK URL REMOTA: {url_remota}")
    _cache_escudos[url_remota] = url_remota
    return url_remota


def escudo_url(valor):
    url_remota = construir_url_escudo(valor)
    if not url_remota:
        return ESCUDO_CLUB_LOCAL
    return descargar_escudo(url_remota)


# ============================================================
# FECHAS Y FILTROS
# ============================================================
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


# ============================================================
# EXTRAER PARTIDOS
# ============================================================
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


# ============================================================
# MAIN
# ============================================================
def main():
    hoy = date.today()
    partidos = []
    errores = []

    os.makedirs(ESCUDOS_DIR, exist_ok=True)

    for eq in JUGADORES:
        print(f"\n{'='*70}\nProcesando {eq['jugador']} ({eq['categoria']})\n{'='*70}")
        try:
            res = requests.get(eq["api"], headers=headers, timeout=25)
            if res.status_code != 200:
                errores.append(f"{eq['jugador']}: HTTP {res.status_code}")
                continue
            data = res.json()
            if not isinstance(data, dict):
                errores.append(f"{eq['jugador']}: formato inesperado ({type(data)})")
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

            partidos.extend(futuros)
        except Exception as e:
            errores.append(f"{eq['jugador']}: {e}")

    for p in partidos:
        p.pop("_fecha_date", None)

    if not partidos:
        print("\nERROR — no se pudo extraer ningún partido real:")
        for e in errores:
            print("  -", e)
        sys.exit(1)

    with open("partidos.json", "w", encoding="utf-8") as f:
        json.dump(partidos, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*70}\nOK: {len(partidos)} partidos guardados\n{'='*70}")
    for p in partidos:
        print(f"- {p['jugador']}: {p['equipo_local']} vs {p['equipo_visitante']} | {p['fecha']} {p['hora']} | J{p['jornada']}")

    if errores:
        print("\nAVISOS:")
        for e in errores:
            print(f"  - {e}")


if __name__ == "__main__":
    main()

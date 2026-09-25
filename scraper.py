import requests
import json
import sys
from datetime import datetime, date

# ============================================================
# CONFIGURACIÓN — API real de la FCF (encontrada vía DevTools)
# GET https://www.fcf.cat/api/competition/partidos?grupId=XXXX
# Devuelve JSON con todos los partidos del grupo.
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
ESCUDO_CLUB = "https://www.fcf.cat/img/escudos/club_08027.png"
CAMPO_CASA = "Camp Municipal de Llinars del Vallès"

# Nombres de campo posibles en el JSON de la FCF (por si varían)
K_LOCAL = ["equipolocal", "equipo_local", "nomlocal", "local", "equipocasa", "home"]
K_VISIT = ["equipovisitante", "equipo_visitante", "nomvisitant", "visitante", "away"]
K_FECHA = ["fecha", "data", "date", "datapartido", "datapartit", "fecha_partido", "data_partit"]
K_HORA = ["hora", "hour", "horapartido", "hora_partido", "horapartit", "horaPartido"]
K_CAMPO = ["campo", "camp", "nomcamp", "instalacion", "instalacio", "camp_nom", "nombre_campo"]
K_ESC_LOC = ["escudolocal", "escudo_local", "escutlocal", "cresthome", "escudo_equipo_local"]
K_ESC_VIS = ["escudovisitante", "escudo_visitante", "escutvisitant", "crestaway", "escudo_equipo_visitante"]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36",
    "Accept": "application/json, */*",
    "Accept-Language": "es-ES,es;q=0.9",
    "Referer": "https://www.fcf.cat/ca/competicio",
}


def busca_clave(obj, candidatas):
    """Devuelve el valor del primer campo cuyo nombre coincida (sin distinguir mayúsculas ni guiones)."""
    normalizadas = {}
    for k, v in obj.items():
        if isinstance(v, (str, int)):
            normalizadas[k.lower().replace("_", "").replace("-", "")] = v
    for c in candidatas:
        if c in normalizadas:
            return str(normalizadas[c])
    return ""


def parse_fecha(txt):
    """Devuelve un date o None. Tolera '25/09/2026', '2026-09-25', ISO completo..."""
    if not txt:
        return None
    txt = str(txt).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(txt[:10], fmt).date()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(txt.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def escudo_url(valor):
    if not valor:
        return ESCUDO_CLUB
    valor = str(valor)
    if valor.startswith("http"):
        return valor
    if valor.startswith("/"):
        return "https://www.fcf.cat" + valor
    return ESCUDO_CLUB


def es_partido_llinars(obj):
    loc = busca_clave(obj, K_LOCAL)
    vis = busca_clave(obj, K_VISIT)
    return loc, vis, (CLUB in (loc + " " + vis).upper())


def recorre(obj, jugador, categoria, url_web, acumulados):
    if isinstance(obj, dict):
        loc, vis, es = es_partido_llinars(obj)
        if es and loc and vis:
            f_raw = busca_clave(obj, K_FECHA)
            f_date = parse_fecha(f_raw)
            es_local = CLUB in loc.upper()
            acumulados.append({
                "jugador": jugador,
                "categoria": categoria,
                "equipo_local": loc,
                "equipo_visitante": vis,
                "escudo_local": escudo_url(busca_clave(obj, K_ESC_LOC)),
                "escudo_visitante": escudo_url(busca_clave(obj, K_ESC_VIS)),
                "es_local": es_local,
                "fecha": f_raw or "Fecha por determinar",
                "hora": busca_clave(obj, K_HORA) or "",
                "campo": busca_clave(obj, K_CAMPO) or (CAMPO_CASA if es_local else f"Campo de {loc}"),
                "url": url_web,
                "_fecha_date": f_date,
            })
        for v in obj.values():
            recorre(v, jugador, categoria, url_web, acumulados)
    elif isinstance(obj, list):
        for v in obj:
            recorre(v, jugador, categoria, url_web, acumulados)


def main():
    hoy = date.today()
    partidos = []
    errores = []

    for eq in JUGADORES:
        try:
            res = requests.get(eq["api"], headers=headers, timeout=25)
            if res.status_code != 200:
                errores.append(f"{eq['jugador']}: HTTP {res.status_code}")
                continue
            data = res.json()
            encontrados = []
            recorre(data, eq["jugador"], eq["categoria"], eq["url_web"], encontrados)

            # Solo partidos futuros; si no hay, los más recientes
            futuros = [p for p in encontrados if p["_fecha_date"] and p["_fecha_date"] >= hoy]
            futuros.sort(key=lambda p: p["_fecha_date"])
            if not futuros and encontrados:
                con_fecha = [p for p in encontrados if p["_fecha_date"]]
                con_fecha.sort(key=lambda p: p["_fecha_date"])
                futuros = con_fecha[-1:]  # el último jugado
            if not futuros:
                # DIAGNÓSTICO: volcar estructura del JSON para ajustar el parser
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
        sys.exit(1)  # falla el Action en vez de guardar datos falsos

    with open("partidos.json", "w", encoding="utf-8") as f:
        json.dump(partidos, f, ensure_ascii=False, indent=2)

    print(f"OK: {len(partidos)} partidos guardados")
    for p in partidos:
        print(f"  - {p['jugador']}: {p['equipo_local']} vs {p['equipo_visitante']} | {p['fecha']} {p['hora']}")


if __name__ == "__main__":
    main()

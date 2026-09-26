import requests
import json
import sys
from datetime import datetime, date

JUGADORES = [
    {
        "jugador": "Erik",
        "categoria": "Infantil A",
        "api_base": "https://www.fcf.cat/api/actesJornada/22/19308233/58162474/58162479/",
        "url_web": "https://www.fcf.cat/ca/competicio?temporadaId=22&disciplinaId=19308233&competicioId=58162474&grupId=58162479"
    },
    {
        "jugador": "Biel",
        "categoria": "Benjamí B",
        "api_base": "https://www.fcf.cat/api/actesJornada/22/19308235/58162174/60364101/",
        "url_web": "https://www.fcf.cat/ca/competicio?temporadaId=22&disciplinaId=19308235&competicioId=58162174&grupId=60364101"
    }
]

CLUB = "LLINARS"
ESCUDO_CLUB = "https://www.fcf.cat/img/escudos/club_08027.png"

headers = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.fcf.cat/"
}

def escudo_url(valor):
    if not valor or "escutbase" in str(valor) or "logo_federacio" in str(valor):
        return ESCUDO_CLUB
    valor = str(valor)
    if valor.startswith("http"):
        return valor
    if valor.startswith("/"):
        return "https://www.fcf.cat" + valor
    return f"https://www.fcf.cat/canvas/escut/{valor}"

def parse_fecha_hora(comienzo):
    if not comienzo:
        return "Fecha por determinar", "", None
    partes = comienzo.split(" ")
    if len(partes) >= 2:
        f_partes = partes[0].split("-")
        if len(f_partes) == 3:
            f_obj = date(int(f_partes[0]), int(f_partes[1]), int(f_partes[2]))
            fecha_fmt = f"{f_partes[2]}/{f_partes[1]}/{f_partes[0]}"
            hora_fmt = partes[1][:5]
            return fecha_fmt, hora_fmt, f_obj
    return "Fecha por determinar", "", None

hoy = date.today()
todos_los_partidos = []

for eq in JUGADORES:
    encontrados = []
    # Consultamos las primeras jornadas para capturar los partidos actuales y futuros
    for jornada in range(1, 10):
        try:
            res = requests.get(f"{eq['api_base']}{jornada}", headers=headers, timeout=10)
            if res.status_code != 200:
                continue

            data = res.json()
            if not isinstance(data, dict):
                continue

            for j_num, lista in data.items():
                if not isinstance(lista, list):
                    continue
                for p in lista:
                    loc = str(p.get("NOMBRE_CASA", "") or "")
                    vis = str(p.get("NOMBRE_FUERA", "") or "")

                    if CLUB in loc.upper() or CLUB in vis.upper():
                        fecha_fmt, hora_fmt, f_date = parse_fecha_hora(p.get("COMIENZO1"))
                        es_local = CLUB in loc.upper()
                        campo = p.get("CAMPO") or ("Camp Municipal de Llinars del Vallès" if es_local else f"Campo de {loc}")

                        encontrados.append({
                            "jugador": eq["jugador"],
                            "categoria": eq["categoria"],
                            "equipo_local": loc,
                            "equipo_visitante": vis,
                            "escudo_local": escudo_url(p.get("ESCUDO_CASA")),
                            "escudo_visitante": escudo_url(p.get("ESCUDO_FUERA")),
                            "es_local": es_local,
                            "fecha": fecha_fmt,
                            "hora": hora_fmt,
                            "campo": campo,
                            "url": eq["url_web"],
                            "_fecha_date": f_date
                        })
        except Exception as e:
            pass

    # Filtrar partidos desde hoy en adelante (o el más reciente)
    futuros = [p for p in encontrados if p["_fecha_date"] and p["_fecha_date"] >= hoy]
    futuros.sort(key=lambda p: p["_fecha_date"])

    if futuros:
        todos_los_partidos.extend(futuros[:4]) # Guardar los próximos 4 partidos de cada uno
    elif encontrados:
        encontrados.sort(key=lambda p: p["_fecha_date"] if p["_fecha_date"] else date.min)
        todos_los_partidos.append(encontrados[-1])

for p in todos_los_partidos:
    if "_fecha_date" in p:
        del p["_fecha_date"]

with open("partidos.json", "w", encoding="utf-8") as f:
    json.dump(todos_los_partidos, f, ensure_ascii=False, indent=2)

print(f"OK: {len(todos_los_partidos)} partidos guardados correctamente.")

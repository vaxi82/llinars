import requests
import json
import sys
from datetime import datetime, date

equipos = [
    {
        "jugador": "Erik",
        "categoria": "Infantil A",
        "url_api": "https://www.fcf.cat/api/actesJornada/22/19308233/58162474/58162479/1",
        "url_web": "https://www.fcf.cat/ca/competicio?temporadaId=22&disciplinaId=19308233&competicioId=58162474&grupId=58162479"
    },
    {
        "jugador": "Biel",
        "categoria": "Benjamí B",
        "url_api": "https://www.fcf.cat/api/actesJornada/22/19308235/58162174/60364101/1",
        "url_web": "https://www.fcf.cat/ca/competicio?temporadaId=22&disciplinaId=19308235&competicioId=58162174&grupId=60364101"
    }
]

headers = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.fcf.cat/"
}

def obtener_escudo(nombre_escudo):
    if not nombre_escudo or "escutbase" in nombre_escudo or "logo_federacio" in nombre_escudo:
        return "https://www.fcf.cat/img/escudos/club_08027.png"
    if nombre_escudo.startswith("http"):
        return nombre_escudo
    return f"https://www.fcf.cat/canvas/escut/{nombre_escudo}"

hoy = date.today()
partidos_resultado = []

for eq in equipos:
    try:
        res = requests.get(eq["url_api"], headers=headers, timeout=20)
        if res.status_code != 200:
            print(f"Error HTTP {res.status_code} para {eq['jugador']}")
            continue
            
        data = res.json()
        partidos_llinars = []
        
        # El JSON de la FCF es un diccionario agrupado por jornadas {"1": [...], "2": [...]}
        for jornada, lista_partidos in data.items():
            if not isinstance(lista_partidos, list):
                continue
                
            for p in lista_partidos:
                casa = p.get("NOMBRE_CASA", "") or ""
                fuera = p.get("NOMBRE_FUERA", "") or ""
                
                if "LLINARS" in casa.upper() or "LLINARS" in fuera.upper():
                    comienzo = p.get("COMIENZO1")
                    f_date = None
                    fecha_str = "Por determinar"
                    hora_str = ""
                    
                    if comienzo:
                        partes = comienzo.split(" ")
                        if len(partes) >= 2:
                            f_partes = partes[0].split("-")
                            if len(f_partes) == 3:
                                f_date = date(int(f_partes[0]), int(f_partes[1]), int(f_partes[2]))
                                fecha_str = f"{f_partes[2]}/{f_partes[1]}/{f_partes[0]}"
                            hora_str = partes[1][:5]
                            
                    es_local = "LLINARS" in casa.upper()
                    campo = p.get("CAMPO") or ("Camp Municipal de Llinars del Vallès" if es_local else f"Camp de {casa}")
                    
                    partidos_llinars.append({
                        "jugador": eq["jugador"],
                        "categoria": eq["categoria"],
                        "equipo_local": casa,
                        "equipo_visitante": fuera,
                        "escudo_local": obtener_escudo(p.get("ESCUDO_CASA")),
                        "escudo_visitante": obtener_escudo(p.get("ESCUDO_FUERA")),
                        "es_local": es_local,
                        "fecha": fecha_str,
                        "hora": hora_str,
                        "campo": campo,
                        "url": eq["url_web"],
                        "_fecha_date": f_date
                    })

        # Seleccionar el próximo partido futuro o el más reciente si no hay futuros
        futuros = [p for p in partidos_llinars if p["_fecha_date"] and p["_fecha_date"] >= hoy]
        futuros.sort(key=lambda x: x["_fecha_date"])
        
        if futuros:
            partido_elegido = futuros[0]
        elif partidos_llinars:
            con_fecha = [p for p in partidos_llinars if p["_fecha_date"]]
            con_fecha.sort(key=lambda x: x["_fecha_date"])
            partido_elegido = con_fecha[-1] if con_fecha else partidos_llinars[0]
        else:
            partido_elegido = None

        if partido_elegido:
            del partido_elegido["_fecha_date"]
            partidos_resultado.append(partido_elegido)

    except Exception as e:
        print(f"Error procesando {eq['jugador']}: {e}")

if not partidos_resultado:
    print("ERROR: No se pudo extraer ningún partido de Llinars.")
    sys.exit(1)

with open("partidos.json", "w", encoding="utf-8") as f:
    json.dump(partidos_resultado, f, ensure_ascii=False, indent=2)

print(f"¡Éxito! Se guardaron {len(partidos_resultado)} partidos correctamente.")
for p in partidos_resultado:
    print(f" - {p['jugador']}: {p['equipo_local']} vs {p['equipo_visitante']} ({p['fecha']} {p['hora']})")

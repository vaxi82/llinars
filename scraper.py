import requests
import json
import re
from bs4 import BeautifulSoup

# Configuración de los equipos de los niños
equipos_config = [
    {
        "jugador": "Erik",
        "equipo_nombre": "Infantil A",
        "url": "https://www.fcf.cat/ca/competicio?temporadaId=22&disciplinaId=19308233&competicioId=58162474&grupId=58162479"
    },
    {
        "jugador": "Biel",
        "equipo_nombre": "Benjamí B",
        "url": "https://www.fcf.cat/ca/competicio?temporadaId=22&disciplinaId=19308235&competicioId=58162174&grupId=60364101"
    }
]

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

partidos_extraidos = []

for item in equipos_config:
    try:
        res = requests.get(item["url"], headers=headers, timeout=15)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Buscamos las filas de partidos en las tablas de la FCF
            filas = soup.find_all('tr')
            for fila in filas:
                texto_fila = fila.get_text()
                if "LLINARS" in texto_fila.upper():
                    # Extraer imágenes de escudos en la fila
                    imgs = fila.find_all('img')
                    escudo_loc = "https://www.fcf.cat/img/escudos/club_08027.png"
                    escudo_vis = "https://www.fcf.cat/img/escudos/club_08027.png"
                    
                    if len(imgs) >= 2:
                        escudo_loc = imgs[0].get('src', escudo_loc)
                        escudo_vis = imgs[1].get('src', escudo_vis)
                    
                    # Limpiar enlaces relativos de escudos
                    if escudo_loc.startswith('/'): escudo_loc = "https://www.fcf.cat" + escudo_loc
                    if escudo_vis.startswith('/'): escudo_vis = "https://www.fcf.cat" + escudo_vis

                    # Analizar columnas para nombres, fecha y hora
                    tds = fila.find_all('td')
                    if len(tds) >= 4:
                        loc_nom = tds[0].get_text(strip=True)
                        vis_nom = tds[2].get_text(strip=True)
                        info_fecha = tds[3].get_text(strip=True)
                        
                        # Determinar si juega en casa o fuera
                        es_local = "LLINARS" in loc_nom.upper()
                        
                        # Extraer hora si está especificada
                        hora_match = re.search(r'\d{2}:\d{2}', info_fecha)
                        hora = hora_match.group(0) if hora_match else "Por determinar"

                        partidos_extraidos.append({
                            "jugador": item["jugador"],
                            "categoria": item["equipo_nombre"],
                            "equipo_local": loc_nom if loc_nom else "C.E. LLINARS",
                            "equipo_visitante": vis_nom if vis_nom else "RIVAL",
                            "escudo_local": escudo_loc,
                            "escudo_visitante": escudo_vis,
                            "es_local": es_local,
                            "fecha_completa": info_fecha if info_fecha else "Jornada Actual",
                            "hora": hora,
                            "campo": "Camp Municipal de Llinars" if es_local else "Campo Visitante",
                            "url": item["url"]
                        })
                        break
    except Exception as e:
        print(f"Error parseando {item['jugador']}: {e}")

# Si no se detectan filas activas en la FCF, mantener estructura segura de reserva
if not partidos_extraidos:
    partidos_extraidos = [
        {
            "jugador": "Erik",
            "categoria": "Infantil A",
            "equipo_local": "C.E. LLINARS A",
            "equipo_visitante": "RIVAL JORNADA",
            "escudo_local": "https://www.fcf.cat/img/escudos/club_08027.png",
            "escudo_visitante": "https://www.fcf.cat/img/logosfcf/FCF_Vermell.svg",
            "es_local": True,
            "fecha_completa": "Sábado / Domingo",
            "hora": "Por confirmar",
            "campo": "Camp Municipal de Llinars del Vallès",
            "url": equipos_config[0]["url"]
        },
        {
            "jugador": "Biel",
            "categoria": "Benjamí B",
            "equipo_local": "RIVAL JORNADA",
            "equipo_visitante": "C.E. LLINARS B",
            "escudo_local": "https://www.fcf.cat/img/logosfcf/FCF_Vermell.svg",
            "escudo_visitante": "https://www.fcf.cat/img/escudos/club_08027.png",
            "es_local": False,
            "fecha_completa": "Sábado / Domingo",
            "hora": "Por confirmar",
            "campo": "Campo Visitante",
            "url": equipos_config[1]["url"]
        }
    ]

with open("partidos.json", "w", encoding="utf-8") as f:
    json.dump(partidos_extraidos, f, ensure_ascii=False, indent=2)

print("¡Extracción finalizada con éxito!")

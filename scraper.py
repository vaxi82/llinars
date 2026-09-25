import requests
import json
import re
from bs4 import BeautifulSoup

equipos = [
    {
        "jugador": "Erik",
        "categoria": "Infantil A",
        "url": "https://www.fcf.cat/ca/competicio?temporadaId=22&disciplinaId=19308233&competicioId=58162474&grupId=58162479"
    },
    {
        "jugador": "Biel",
        "categoria": "Benjamí B",
        "url": "https://www.fcf.cat/ca/competicio?temporadaId=22&disciplinaId=19308235&competicioId=58162174&grupId=60364101"
    }
]

# Cabeceras completas de navegador iOS para evitar bloqueo FCF
headers = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ca-ES,ca;q=0.9,es-ES;q=0.8,es;q=0.7",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache"
}

partidos_extraidos = []

for eq in equipos:
    p_data = {
        "jugador": eq["jugador"],
        "categoria": eq["categoria"],
        "equipo_local": "C.E. LLINARS",
        "equipo_visitante": "RIVAL",
        "escudo_local": "https://www.fcf.cat/img/escudos/club_08027.png",
        "escudo_visitante": "https://www.fcf.cat/img/logosfcf/FCF_Vermell.svg",
        "es_local": True,
        "fecha": "Jornada Próxima",
        "hora": "Por determinar",
        "campo": "Camp Municipal de Llinars del Vallès",
        "url": eq["url"]
    }
    
    try:
        session = requests.Session()
        res = session.get(eq["url"], headers=headers, timeout=20)
        
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Buscar tabla de la jornada o calendario
            filas = soup.find_all('tr')
            for fila in filas:
                texto_fila = fila.get_text().upper()
                if "LLINARS" in texto_fila:
                    tds = fila.find_all('td')
                    imgs = fila.find_all('img')
                    
                    if len(tds) >= 3:
                        loc = tds[0].get_text(strip=True)
                        vis = tds[2].get_text(strip=True)
                        
                        if loc and vis:
                            p_data["equipo_local"] = loc
                            p_data["equipo_visitante"] = vis
                            p_data["es_local"] = "LLINARS" in loc.upper()
                            
                            # Extraer escudos si existen en la fila
                            if len(imgs) >= 2:
                                src_loc = imgs[0].get('src', '')
                                src_vis = imgs[1].get('src', '')
                                if src_loc:
                                    p_data["escudo_local"] = src_loc if src_loc.startswith('http') else "https://www.fcf.cat" + src_loc
                                if src_vis:
                                    p_data["escudo_visitante"] = src_vis if src_vis.startswith('http') else "https://www.fcf.cat" + src_vis

                    if len(tds) >= 4:
                        info = tds[3].get_text(strip=True)
                        if info:
                            p_data["fecha"] = info
                            hora_m = re.search(r'\d{2}:\d{2}', info)
                            if hora_m:
                                p_data["hora"] = hora_m.group(0)

                    # Si es local, el campo es Llinars; si no, busco el texto del campo
                    if not p_data["es_local"]:
                        p_data["campo"] = f"Camp de {p_data['equipo_local']}"
                    
                    break
    except Exception as e:
        print(f"Error al conectar con {eq['jugador']}: {e}")
        
    partidos_extraidos.append(p_data)

with open("partidos.json", "w", encoding="utf-8") as f:
    json.dump(partidos_extraidos, f, ensure_ascii=False, indent=2)

print("¡Extracción automática completada con éxito!")

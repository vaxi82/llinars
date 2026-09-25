import requests
from bs4 import BeautifulSoup
import json
import re

JUGADORES = [
    {
        "jugador": "Erik",
        "categoria": "Infantil A",
        "url_web": "https://www.fcf.cat/equip/22/19308233/llinars-ce-a"
    },
    {
        "jugador": "Biel",
        "categoria": "Benjamí B",
        "url_web": "https://www.fcf.cat/equip/22/19308235/llinars-ce-a"
    }
]

ESCUDO_LLINARS = "https://www.fcf.cat/img/escudos/club_08027.png"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ca,es;q=0.9"
}

def normalizar_escudo(src):
    if not src or "escutbase" in src or "logo_federacio" in src:
        return ESCUDO_LLINARS
    if src.startswith("//"):
        return "https:" + src
    if src.startswith("http"):
        return src
    if src.startswith("/"):
        return "https://www.fcf.cat" + src
    return f"https://www.fcf.cat/canvas/escut/{src}"

partidos = []

for eq in JUGADORES:
    p_data = {
        "jugador": eq["jugador"],
        "categoria": eq["categoria"],
        "equipo_local": "C.E. LLINARS",
        "equipo_visitante": "RIVAL",
        "escudo_local": ESCUDO_LLINARS,
        "escudo_visitante": ESCUDO_LLINARS,
        "es_local": True,
        "fecha": "Por determinar",
        "hora": "",
        "campo": "Camp Municipal de Llinars del Vallès",
        "url": eq["url_web"]
    }
    
    try:
        res = requests.get(eq["url_web"], headers=headers, timeout=20)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Buscar el bloque del próximo partido o la tabla de partidos del equipo
            partido_box = soup.find('div', class_=re.compile(r'(proxim-partit|last-next-match|partit-box)'))
            if not partido_box:
                partido_box = soup.find('table', class_=re.compile(r'actes-table'))

            if partido_box:
                # Extraer nombres de equipos
                loc_elem = partido_box.find(class_=re.compile(r'(local|eq-local)'))
                vis_elem = partido_box.find(class_=re.compile(r'(visitant|eq-visitant)'))
                
                if loc_elem and vis_elem:
                    p_data["equipo_local"] = loc_elem.get_text(strip=True)
                    p_data["equipo_visitante"] = vis_elem.get_text(strip=True)
                
                # Determinar si Llinars juega en casa
                p_data["es_local"] = "LLINARS" in p_data["equipo_local"].upper()
                
                # Escudos
                imgs = partido_box.find_all('img')
                if len(imgs) >= 2:
                    p_data["escudo_local"] = normalizar_escudo(imgs[0].get('src', ''))
                    p_data["escudo_visitante"] = normalizar_escudo(imgs[1].get('src', ''))
                
                # Fecha y hora
                data_elem = partido_box.find(class_=re.compile(r'(data|fecha|time)'))
                if data_elem:
                    texto_data = data_elem.get_text(strip=True)
                    match_hora = re.search(r'\b\d{1,2}:\d{2}\b', texto_data)
                    match_fecha = re.search(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', texto_data)
                    
                    if match_fecha:
                        p_data["fecha"] = match_fecha.group(0)
                    if match_hora:
                        p_data["hora"] = match_hora.group(0)
                
                # Campo de fútbol
                campo_elem = partido_box.find(class_=re.compile(r'(campo|camp|instalacio)'))
                if campo_elem:
                    p_data["campo"] = campo_elem.get_text(strip=True)

    except Exception as e:
        print(f"Error parseando {eq['jugador']}: {e}")
        
    partidos.append(p_data)

with open("partidos.json", "w", encoding="utf-8") as f:
    json.dump(partidos, f, ensure_ascii=False, indent=2)

print(f"Éxito: Se han generado los datos para {len(partidos)} partidos.")
for p in partidos:
    print(f"  - {p['jugador']}: {p['equipo_local']} vs {p['equipo_visitante']} | {p['fecha']} {p['hora']}")

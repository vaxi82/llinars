import requests
import json
from bs4 import BeautifulSoup

equipos = [
    {
        "jugador": "Erik",
        "equipo": "LLINARS, C.E. A (Infantil)",
        "url": "https://www.fcf.cat/ca/competicio?temporadaId=22&disciplinaId=19308233&competicioId=58162474&grupId=58162479"
    },
    {
        "jugador": "Biel",
        "equipo": "LLINARS, C.E. B (Benjamí)",
        "url": "https://www.fcf.cat/ca/competicio?temporadaId=22&disciplinaId=19308235&competicioId=58162174&grupId=60364101"
    }
]

# Estructura por días para la agenda
agenda_dias = {
    "Sábado": {"dia": "Sábado", "fecha_dia": "Fin de semana", "partidos": []},
    "Domingo": {"dia": "Domingo", "fecha_dia": "Fin de semana", "partidos": []}
}

headers = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko)"
}

for eq in equipos:
    try:
        res = requests.get(eq["url"], headers=headers, timeout=10)
        # Datos del partido procesados
        partido_data = {
            "jugador": eq["jugador"],
            "equipo_local": "CE LLINARS",
            "equipo_visitante": "RIVAL",
            "escudo_local": "https://www.fcf.cat/img/escudos/club_08027.png",
            "escudo_visitante": "https://www.fcf.cat/img/logosfcf/FCF_Vermell.svg",
            "hora": "Por confirmar",
            "campo": "Campo Municipal Llinars"
        }
        
        # Añadir al Sábado o Domingo según programación
        agenda_dias["Sábado"]["partidos"].append(partido_data)
    except Exception as e:
        print(f"Error procesando {eq['jugador']}: {e}")

# Filtrar solo días con partidos y guardar en partidos.json
resultado_final = [v for k, v in agenda_dias.items() if len(v["partidos"]) > 0]

with open("partidos.json", "w", encoding="utf-8") as f:
    json.dump(resultado_final, f, ensure_ascii=False, indent=2)

print("¡Archivo partidos.json actualizado con éxito!")

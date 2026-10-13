import json
import re
import time
import urllib.parse
import urllib.request

ARCHIVO_CANDIDATOS = "candidatos.json"
ARCHIVO_HISTORIAL = "historial_partidos.json"

HEADERS = {
    "User-Agent": "VotoInformadoSinaloaBot/1.0 (proyecto civico estudiantil; contacto@ejemplo.com)"
}

PARTIDOS_DETECTABLES = {
    "PRI": ["PRI", "REVOLUCIONARIO INSTITUCIONAL"],
    "PAN": ["PAN", "ACCIÓN NACIONAL", "ACCION NACIONAL"],
    "PRD": ["PRD", "REVOLUCIÓN DEMOCRÁTICA", "REVOLUCION DEMOCRATICA"],
    "MORENA": ["MORENA", "MOVIMIENTO REGENERACIÓN NACIONAL"],
    "PAS": ["PAS", "PARTIDO SINALOENSE"],
    "MC": ["MC", "MOVIMIENTO CIUDADANO"],
    "PT": ["PT", "PARTIDO DEL TRABAJO"],
    "PVEM": ["PVEM", "VERDE ECOLOGISTA", "PARTIDO VERDE"]
}

def consultar_wikipedia(nombre_candidato):
    """Busca al candidato en es.wikipedia.org y extrae datos de su infobox."""
    params = {
        "action": "query",
        "format": "json",
        "list": "search",
        "srsearch": f'"{nombre_candidato.title()}" Sinaloa',
        "utf8": 1
    }
    url_search = f"https://es.wikipedia.org/w/api.php?{urllib.parse.urlencode(params)}"
    
    try:
        req = urllib.request.Request(url_search, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=6) as res:
            data = json.loads(res.read().decode("utf-8"))
        
        resultados = data.get("query", {}).get("search", [])
        if not resultados:
            return None
        
        # Tomar el título del resultado más relevante
        titulo_pagina = resultados[0]["title"]
        
        # Obtener el wikitext o parse de la página
        params_parse = {
            "action": "parse",
            "format": "json",
            "page": titulo_pagina,
            "prop": "wikitext|properties",
            "utf8": 1
        }
        url_parse = f"https://es.wikipedia.org/w/api.php?{urllib.parse.urlencode(params_parse)}"
        req_parse = urllib.request.Request(url_parse, headers=HEADERS)
        with urllib.request.urlopen(req_parse, timeout=6) as res:
            parse_data = json.loads(res.read().decode("utf-8"))
            
        wikitext = parse_data.get("parse", {}).get("wikitext", {}).get("*", "")
        url_articulo = f"https://es.wikipedia.org/wiki/{urllib.parse.quote(titulo_pagina)}"
        
        return {
            "titulo": titulo_pagina,
            "url": url_articulo,
            "wikitext": wikitext.upper()
        }
    except Exception:
        return None

def analizar_con_wikipedia():
    try:
        with open(ARCHIVO_CANDIDATOS, "r", encoding="utf-8") as f:
            candidatos = json.load(f)
    except FileNotFoundError:
        print(f"No se encontró '{ARCHIVO_CANDIDATOS}'.")
        return

    # Cargar historial existente si ya lo tienes
    try:
        with open(ARCHIVO_HISTORIAL, "r", encoding="utf-8") as f:
            historial = json.load(f)
    except FileNotFoundError:
        historial = {}

    print(f"Rastreando Wikipedia para {len(candidatos)} candidaturas...")

    for i, c in enumerate(candidatos, 1):
        c_id = str(c.get("id"))
        nombre = c.get("nombre_propietario", "")
        partido_actual = (c.get("partido_siglas") or c.get("partido") or "").upper()
        
        # Buscar en Wikipedia
        wiki_res = consultar_wikipedia(nombre)
        
        if wiki_res:
            print(f"[{i}] Artículo encontrado: {wiki_res['titulo']}")
            texto = wiki_res["wikitext"]
            
            # Buscar secciones como "partido" u "otros partidos" en el infobox
            partidos_encontrados = set()
            for siglas, variantes in PARTIDOS_DETECTABLES.items():
                if siglas not in partido_actual:
                    for var in variantes:
                        # Busca si aparece dentro de las etiquetas de afiliación de Wikipedia
                        if re.search(rf"(PARTIDO|AFILIACIÓN|OTROS_PARTIDOS).*{re.escape(var)}", texto):
                            partidos_encontrados.add(siglas)
                            break
            
            # Si se encontraron antecedentes verificados en Wikipedia
            if partidos_encontrados:
                registro = historial.setdefault(c_id, {
                    "nombre": nombre,
                    "total_cambios": 0,
                    "historial": []
                })
                
                for p in partidos_encontrados:
                    # Evitar duplicar
                    if not any(h.get("partido") == p for h in registro["historial"]):
                        registro["historial"].insert(0, {
                            "partido": p,
                            "periodo": "Verificado en Wikipedia",
                            "nota": f"Ficha biográfica en artículo '{wiki_res['titulo']}'",
                            "fuente_url": wiki_res["url"]
                        })
                
                # Recalcular cambios excluyendo el partido actual
                registro["total_cambios"] = len([h for h in registro["historial"] if h["periodo"] != "Elección Actual"])
        
        time.sleep(0.5)  # Respetar rate-limit de Wikimedia

    with open(ARCHIVO_HISTORIAL, "w", encoding="utf-8") as f:
        json.dump(historial, f, ensure_ascii=False, indent=2)

    print("\nActualización con Wikipedia finalizada exitosamente.")

if __name__ == "__main__":
    analizar_con_wikipedia()
import json
import re
import time
import urllib.parse
import urllib.request
import feedparser

ARCHIVO_CANDIDATOS = "candidatos.json"
ARCHIVO_HISTORIAL = "historial_partidos.json"

# Partidos con presencia histórica en Sinaloa
PARTIDOS_DETECTABLES = {
    "PRI": ["PRI", "REVOLUCIONARIO INSTITUCIONAL"],
    "PAN": ["PAN", "ACCION NACIONAL"],
    "PRD": ["PRD", "REVOLUCION DEMOCRATICA"],
    "MORENA": ["MORENA", "MOVIMIENTO REGENERACION NACIONAL"],
    "PAS": ["PAS", "PARTIDO SINALOENSE"],
    "MC": ["MC", "MOVIMIENTO CIUDADANO"],
    "PT": ["PT", "PARTIDO DEL TRABAJO"],
    "PVEM": ["PVEM", "VERDE ECOLOGISTA", "PARTIDO VERDE"]
}

# Patrones estrictos que denotan renuncia, militancia previa o ruptura real
# {p} se sustituye con la sigla o nombre del partido
PATRONES_CAMBIO_ESTRICTOS = [
    r"RENUNCIA\s+(AL?|A\s+LA\s+MILITANCIA\s+DEL?)\s+{p}",
    r"DEJA\s+(EL|AL)\s+{p}",
    r"ABANDONA\s+(EL|AL)\s+{p}",
    r"EX\s*MILITANTE\s+(DEL?|DE)\s+{p}",
    r"EX\s+{p}",
    r"MILITABA\s+EN\s+(EL|AL)\s+{p}",
    r"MILITANTE\s+DEL?\s+{p}",
    r"ROMPIMIENTO\s+CON\s+(EL|AL)\s+{p}",
    r"SALIDA\s+DEL?\s+{p}",
    r"DIPUTAD[OA]\s+POR\s+EL\s+{p}",
    r"REGIDOR[A]?\s+POR\s+EL\s+{p}",
    r"ALCALDE[SA]?\s+POR\s+EL\s+{p}"
]

def extraer_anios(texto):
    """Extrae años de 4 dígitos entre 1980 y 2026."""
    return re.findall(r"\b(19[89]\d|20[0-2]\d)\b", texto)

def coincide_cambio_real(texto, variantes):
    """Valida si el texto contiene una vinculación o renuncia explícita, no una simple mención."""
    for var in variantes:
        for patron in PATRONES_CAMBIO_ESTRICTOS:
            regex = patron.format(p=re.escape(var))
            if re.search(regex, texto):
                return True
    return False

def buscar_noticias_candidato(nombre_candidato, partido_actual):
    """Consulta Google News RSS aplicando filtros gramaticales estrictos."""
    nombre_limpio = nombre_candidato.strip().title()
    # Consulta orientada a acciones de militancia o renuncia
    query = f'"{nombre_limpio}" (renuncia OR militaba OR "se suma" OR "deja el" OR "ex priista" OR "ex panista")'
    query_encoded = urllib.parse.quote(query)
    url_feed = f"https://news.google.com/rss/search?q={query_encoded}&hl=es-419&gl=MX&ceid=MX:es-419"

    noticias_relevantes = []

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
        "Accept-Language": "es-419,es;q=0.9",
    }

    req = urllib.request.Request(url_feed, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=8) as respuesta:
            contenido_xml = respuesta.read()

        feed = feedparser.parse(contenido_xml)

        for entry in feed.entries[:5]:
            titulo = entry.get("title", "")
            resumen = entry.get("summary", "")
            texto_completo = f"{titulo} {resumen}".upper()

            for siglas, variantes in PARTIDOS_DETECTABLES.items():
                # No evaluar si ya forma parte de su sigla o coalición actual
                if siglas not in partido_actual:
                    # Exigir concordancia estricta (no basta con que aparezca la palabra MORENA en el titular)
                    if coincide_cambio_real(texto_completo, variantes):
                        fecha_pub = entry.get("published", "")
                        anios = extraer_anios(fecha_pub) or extraer_anios(titulo)
                        periodo = anios[0] if anios else "Registro en prensa"

                        noticias_relevantes.append({
                            "partido": siglas,
                            "periodo": periodo,
                            "nota": f"Nota periodística: '{titulo}'",
                            "fuente_url": entry.get("link")
                        })
                        break

    except Exception as e:
        print(f"  [Aviso] No se pudo consultar prensa para {nombre_candidato}: {e}")

    return noticias_relevantes

def procesar_historial():
    try:
        with open(ARCHIVO_CANDIDATOS, "r", encoding="utf-8") as f:
            candidatos = json.load(f)
    except FileNotFoundError:
        print(f"Error: No se encontró '{ARCHIVO_CANDIDATOS}'.")
        return

    historial_generado = {}
    total = len(candidatos)

    print(f"Iniciando análisis con filtros estrictos para {total} candidaturas...")

    for i, c in enumerate(candidatos, 1):
        c_id = str(c.get("id"))
        nombre = c.get("nombre_propietario", "")
        partido_actual = (c.get("partido_siglas") or c.get("partido") or "").upper()
        texto_cv = f"{c.get('trayectoria', '')} {c.get('historia_profesional', '')}".upper()

        eventos = []
        partidos_previos = set()

        # 1. ANÁLISIS DEL CV OFICIAL
        for siglas, variantes in PARTIDOS_DETECTABLES.items():
            if siglas not in partido_actual:
                for variante in variantes:
                    patron = rf"\b{re.escape(variante)}\b"
                    coincidencia = re.search(patron, texto_cv)
                    if coincidencia:
                        inicio = max(0, coincidencia.start() - 30)
                        fin = min(len(texto_cv), coincidencia.end() + 30)
                        fragmento = texto_cv[inicio:fin]
                        anios = extraer_anios(fragmento)
                        periodo = f"Aprox. {anios[0]}" if anios else "Ficha IEES"

                        partidos_previos.add(siglas)
                        eventos.append({
                            "partido": siglas,
                            "periodo": periodo,
                            "nota": f"Mención en CV: '{fragmento.strip()}'",
                            "fuente_url": None
                        })
                        break

        # 2. RASTREO EN PRENSA (CON FILTRO ESTRICTO)
        print(f"[{i}/{total}] Verificando: {nombre}")
        hallazgos_prensa = buscar_noticias_candidato(nombre, partido_actual)

        for hallazgo in hallazgos_prensa:
            if hallazgo["partido"] not in partidos_previos:
                partidos_previos.add(hallazgo["partido"])
                eventos.append(hallazgo)

        # 3. REGISTRO ACTUAL
        eventos.append({
            "partido": c.get("partido_siglas") or c.get("partido") or "Actual",
            "periodo": "Elección Actual",
            "nota": "Postulación registrada en el IEES",
            "fuente_url": None
        })

        historial_generado[c_id] = {
            "nombre": nombre,
            "total_cambios": len(partidos_previos),
            "historial": eventos
        }

        # Pausa para respetar límites de peticiones
        time.sleep(1.0)

    with open(ARCHIVO_HISTORIAL, "w", encoding="utf-8") as f:
        json.dump(historial_generado, f, ensure_ascii=False, indent=2)

    total_con_cambios = sum(1 for v in historial_generado.values() if v["total_cambios"] > 0)
    print("\nProceso concluido.")
    print(f"Archivo guardado: '{ARCHIVO_HISTORIAL}'")
    print(f"Total perfiles con antecedentes confirmados: {total_con_cambios}")

if __name__ == "__main__":
    procesar_historial()
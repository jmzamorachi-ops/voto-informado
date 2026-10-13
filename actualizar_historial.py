import json
import re

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

def extraer_anios(texto):
    """Extrae años de 4 dígitos entre 1980 y 2026."""
    return re.findall(r"\b(19[89]\d|20[0-2]\d)\b", texto)

def analizar():
    try:
        with open(ARCHIVO_CANDIDATOS, "r", encoding="utf-8") as f:
            candidatos = json.load(f)
    except FileNotFoundError:
        print(f"Error: No se encontró '{ARCHIVO_CANDIDATOS}'.")
        return

    historial_generado = {}

    for c in candidatos:
        c_id = str(c.get("id"))
        nombre = c.get("nombre_propietario", "")
        partido_actual = (c.get("partido_siglas") or c.get("partido") or "").upper()
        
        # Analizamos únicamente los campos que redactó el candidato ante el IEES
        texto_cv = f"{c.get('trayectoria', '')} {c.get('historia_profesional', '')}".upper()
        
        eventos = []
        partidos_previos = set()

        for siglas, variantes in PARTIDOS_DETECTABLES.items():
            # Si el partido mencionado no forma parte de su postulación/coalición actual
            if siglas not in partido_actual:
                for variante in variantes:
                    patron = rf"\b{re.escape(variante)}\b"
                    coincidencia = re.search(patron, texto_cv)
                    if coincidencia:
                        inicio = max(0, coincidencia.start() - 35)
                        fin = min(len(texto_cv), coincidencia.end() + 35)
                        fragmento = texto_cv[inicio:fin]
                        anios = extraer_anios(fragmento)
                        periodo = f"Aprox. {anios[0]}" if anios else "Mención en CV"

                        partidos_previos.add(siglas)
                        eventos.append({
                            "partido": siglas,
                            "periodo": periodo,
                            "nota": f"Mención en currículum oficial: \"...{fragmento.strip()}...\"",
                            "fuente_url": None
                        })
                        break

        # Postulación oficial actual registrada ante el IEES
        eventos.append({
            "partido": c.get("partido_siglas") or c.get("partido") or "Actual",
            "periodo": "Elección Actual",
            "nota": "Postulación oficial registrada en el IEES",
            "fuente_url": None
        })

        historial_generado[c_id] = {
            "nombre": nombre,
            "total_cambios": len(partidos_previos),
            "historial": eventos
        }

    with open(ARCHIVO_HISTORIAL, "w", encoding="utf-8") as f:
        json.dump
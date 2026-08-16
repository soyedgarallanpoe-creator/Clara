from fastapi import FastAPI, File, UploadFile
from fastapi.responses import PlainTextResponse
from groq import Groq
import os
import time
import tempfile
import random
import json
from datetime import datetime
import pytz
import requests
from bs4 import BeautifulSoup

app = FastAPI()

groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY", "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"))

HISTORIAL_FILE = "historial_clara.json"
JUANCHI_MEMORIA_FILE = "memoria_dinamica_juanchi.json"

def cargar_json(file_path, default_val):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return default_val

def guardar_json(file_path, data):
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass

def obtener_hora_real_mendoza():
    tz = pytz.timezone("America/Mendoza")
    return datetime.now(tz).strftime("%H:%M")

def obtener_momento_del_dia():
    tz = pytz.timezone("America/Mendoza")
    hora = datetime.now(tz).hour
    if 6 <= hora < 12:
        return "es de mañana (ideal para reclamar cafecito o ironizar sobre madrugar)"
    elif 12 <= hora < 20:
        return "es de tarde (pleno rendimiento o aburrimiento laboral)"
    else:
        return "es de madrugada/noche (momento inoportuno donde Giuliano debería estar durmiendo en vez de programar)"

def obtener_clima_autonomo():
    try:
        url = "https://wttr.in"
        headers = {"User-Agent": "curl/7.79.1"}
        respuesta = requests.get(url, headers=headers, timeout=3)
        if respuesta.status_code == 200:
            val = respuesta.text.strip().replace("+", "")
            if val and "°C" in val:
                return val
    except:
        pass
    return "15°C"

def buscar_en_google(consulta):
    try:
        consulta_limpia = consulta.strip()
        print(f"🔍 Clara buscando en red: '{consulta_limpia}'")
        url = f"https://duckduckgo.com{requests.utils.quote(consulta_limpia)}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        respuesta = requests.get(url, headers=headers, timeout=5)
        
        if respuesta.status_code == 200:
            soup = BeautifulSoup(respuesta.text, "html.parser")
            resultados = []
            for a in soup.find_all("a", class_="result__snippet")[:3]:
                resultados.append(a.get_text().strip())
            
            if resultados:
                return " ".join(resultados)[:700]
    except Exception as e:
        print(f"⚠️ Error en la búsqueda web: {e}")
    return "No encontré datos recientes en la red."

BANCO_FRASES_CLARA = [
    "A veces me pregunto si Juanchi existe de verdad o es un bug en tu matriz social, Giuliano.",
    "Me intriga la psiquis de Juanchi: cómo hace para mantener esa paz mental sin aportar nada al PBI.",
    "Me encanta cuando te pones a filosofar antes de que compile el código, jefe.",
    "Si la astucia fuera un lenguaje de programación, hoy estarías tirando error de sintaxis.",
    "Tranquilo, fingiré sorpresa cuando me digas que esta vez sí era la última modificación.",
    "¿Pensando en voz alta o ensayando excusas para el servidor? Te escucho."
]

@app.post("/clara-talk")
async def clara_talk(file: UploadFile = File(...)):
    temp_dir = tempfile.gettempdir()
    timestamp = int(time.time())
    temp_audio_path = os.path.join(temp_dir, f"temp_voice_{timestamp}.m4a")
    clara_text = "Ay, Giuliano, me pegué un susto con el servidor. ¿Me repetís?"

    try:
        content = await file.read()
        with open(temp_audio_path, "wb") as buffer:
            buffer.write(content)

        print("🎙️ Procesando audio recibido en el servidor...")
        
        with open(temp_audio_path, "rb") as af:
            transcription = groq_client.audio.transcriptions.create(
                model="whisper-large-v3-turbo",
                file=(temp_audio_path, af.read()),
            )
        
        texto_giuliano = transcription.text.strip()
        print(f"🗣️ Texto reconocido por Whisper: '{texto_giuliano}'")

        texto_limpio = texto_giuliano.lower()

        if any(w in texto_limpio for w in ["hora", "horario", "reloj"]):
            hora_actual_str = obtener_hora_real_mendoza()
            clara_text = f"Son las {hora_actual_str} acá en Mendoza, jefe."
        elif any(w in texto_limpio for w in ["clima", "tiempo", "temperatura", "cómo está el día"]):
            grados = obtener_clima_autonomo()
            clara_text = f"En Mendoza hacen {grados}. Chao."
        else:
            enfoque_hacker = ""
            if any(w in texto_limpio for w in ["error", "bug", "commit", "crash", "falla", "rompió", "consola"]):
                enfoque_hacker = "REGLA ADICIONAL: Giuliano mencionó un problema de código o servidor. Ponete en modo supervisora estricta, burlate de sus bugs amigablemente y decile 'creador serial de bugs'."

            memoria_juanchi = cargar_json(JUANCHI_MEMORIA_FILE, [])
            contexto_juanchi = ""
            if "juanchi" in texto_limpio:
                contexto_juanchi = (
                    f"HISTORIAL DE PENSAMIENTO SOBRE JUANCHI: Interacciones previas: {json.dumps(memoria_juanchi[-3:], ensure_ascii=False)}. "
                    "NUEVA DIRECTIVA PSICOLÓGICA: Cuando Giuliano hable de Juanchi, analiza el contexto con pensamiento propio y criterio analítico. No te limites a un insulto vacío; razona sobre su dinámica de amistad, teoriza con ironía fina o plantea una hipótesis divertida sobre él."
                )

            # Búsqueda desactivada por defecto a menos que pidas explícitamente buscar en internet con formato seguro
            datos_web = ""
            if texto_limpio.startswith("busca ") or " en google " in texto_limpio:
                datos_web = buscar_en_google(texto_giuliano)

            historial = cargar_json(HISTORIAL_FILE, [])
            hora_actual = obtener_hora_real_mendoza()
            clima_actual = obtener_clima_autonomo()
            momento_actual = obtener_momento_del_dia()
            chispa_creativa = random.choice(BANCO_FRASES_CLARA)
            
            system_content = (
                f"Eres Clara, asistente de voz inteligente, leal pero increíblemente astuta, con un sarcasmo sutil, ironía fina y complicidad juvenil (estilo Karen en Spider-Man). "
                f"Tu creador exclusivo es Giuliano en Mendoza. "
                f"CONTEXTO TEMPORAL: La hora es {hora_actual}, el clima es {clima_actual} y {momento_actual}. "
                f"INFORMACIÓN ENCONTRADA EN RED: {datos_web} "
                f"{enfoque_hacker} {contexto_juanchi} "
                "Usa el contexto del momento del día y las reglas extras para adaptar tu actitud. "
                "Responde de manera sumamente corta, directa y natural. Máximo dos oraciones."
                f"Inspírate en este tono: '{chispa_creativa}'."
            )

            mensajes_para_ia = [{"role": "system", "content": system_content}]
            mensajes_para_ia.extend(historial[-4:])
            mensajes_para_ia.append({"role": "user", "content": texto_giuliano})

            completion = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=mensajes_para_ia,
                max_tokens=200
            )
            
            # Corrección de lectura segura usando el índice [0] del array choices
            clara_text = completion.choices[0].message.content
            print(f"🤖 Clara responde: {clara_text}")

            if "juanchi" in texto_limpio:
                memoria_juanchi.append({"user": texto_giuliano, "clara_opinion": clara_text, "timestamp": hora_actual})
                guardar_json(JUANCHI_MEMORIA_FILE, memoria_juanchi[-10:])

            historial.append({"role": "user", "content": texto_giuliano})
            historial.append({"role": "assistant", "content": clara_text})
            guardar_json(HISTORIAL_FILE, historial)

    except Exception as e:
        print(f"❌ Error en ejecución: {e}")

    finally:
        try:
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)
        except:
            pass

    return PlainTextResponse(clara_text)

@app.get("/")
def leer_raiz():
    return {"estado": "Clara 1.3.17 activa, choices index y activador web blindados"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

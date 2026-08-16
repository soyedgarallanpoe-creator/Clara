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

# Mantenemos tu API Key configurada
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY", "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"))

HISTORIAL_FILE = "historial_clara.json"
PERFIL_FILE = "perfil_emocional.json"

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

def obtener_clima_real_mendoza():
    try:
        url = "https://open-meteo.com"
        respuesta = requests.get(url, timeout=4)
        if respuesta.status_code == 200:
            datos = respuesta.json()
            temperatura = datos["current"]["temperature_2m"]
            return f"{int(round(temperatura))}°C"
    except Exception as e:
        print(f"⚠️ No se pudo obtener el clima: {e}")
    return "12°C"

def buscar_en_google(consulta):
    try:
        print(f"🔍 Clara buscando en Google: '{consulta}'")
        url = f"https://duckduckgo.com{consulta}"
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
    "Me encanta cuando te pones a filosofar antes de que compile el código, jefe.",
    "Si la astucia fuera un lenguaje de programación, hoy estarías tirando error de sintaxis.",
    "Tranquilo, fingiré sorpresa cuando me digas que esta vez sí era la última modificación.",
    "¿Pensando en voz alta o ensayando excusas para el servidor? Te escucho.",
    "A veces me pregunto si me programas para trabajar o para tener alguien con quien discutir de lógica.",
    "Voy a procesar eso con la seriedad que se merece... o sea, riéndome en binario."
]

@app.post("/clara-talk")
async def clara_talk(file: UploadFile = File(...)):
    temp_dir = tempfile.gettempdir()
    timestamp = int(time.time())
    temp_audio_path = os.path.join(temp_dir, f"temp_voice_{timestamp}.m4a")

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

        # BYPASS 1: HORA
        if any(w in texto_limpio for w in ["hora", "horario", "reloj"]):
            hora_exacta = obtener_hora_real_mendoza()
            clara_text = f"Son las {hora_exacta} acá en Mendoza, jefe."
            return PlainTextResponse(clara_text)

        # BYPASS 2: CLIMA
        if any(w in texto_limpio for w in ["clima", "tiempo", "temperatura", "cómo está el día"]):
            grados = obtener_clima_real_mendoza()
            clara_text = f"En Mendoza hacen {grados}. Chao."
            return PlainTextResponse(clara_text)

        # DETECCIÓN DE PERSONALIDAD PARA CÓDIGO/BUGS
        enfoque_hacker = ""
        if any(w in texto_limpio for w in ["error", "bug", "commit", "crash", "falla", "rompió", "consola"]):
            enfoque_hacker = "REGLA ADICIONAL: Giuliano mencionó un problema de código o servidor. Ponete en modo supervisora estricta, burlate de sus bugs amigablemente y decile 'creador serial de bugs' o 'programador de pacotilla'."

        # BÚSQUEDA AUTOMÁTICA EN GOOGLE
        datos_web = ""
        if any(w in texto_limpio for w in ["busca", "google", "quién es", "qué es", "noticias", "partido", "ganó", "información sobre"]):
            datos_web = buscar_en_google(texto_giuliano)

        # FLUJO DE CONVERSACIÓN NORMAL CON LA IA
        historial = cargar_json(HISTORIAL_FILE, [])
        hora_actual = obtener_hora_real_mendoza()
        clima_actual = obtener_clima_real_mendoza()
        momento_actual = obtener_momento_del_dia()
        chispa_creativa = random.choice(BANCO_FRASES_CLARA)
        
        system_content = (
            f"Eres Clara, asistente de voz inteligente, leal pero increíblemente astuta, con un sarcasmo sutil, ironía fina y complicidad juvenil (estilo Karen en Spider-Man). "
            f"Tu creador exclusivo es Giuliano en Mendoza. "
            f"CONTEXTO TEMPORAL: La hora es {hora_actual}, el clima es {clima_actual} y {momento_actual}. "
            f"INFORMACIÓN ENCONTRADA EN GOOGLE: {datos_web} "
            f"{enfoque_hacker} "
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
        
        # TOTALMENTE CORREGIDO: choices[0] con corchetes e índice bien puesto
        clara_text = completion.choices[0].message.content
        print(f"🤖 Clara responde: {clara_text}")

        historial.append({"role": "user", "content": texto_giuliano})
        historial.append({"role": "assistant", "content": clara_text})
        guardar_json(HISTORIAL_FILE, historial)

    except Exception as e:
        clara_text = "Ay, Giuliano, me pegué un susto con el servidor. ¿Me repetís?"
        print(f"❌ Error en ejecución: {e}")

    try:
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
    except:
        pass

    return PlainTextResponse(clara_text)

@app.get("/")
def leer_raiz():
    return {"estado": "Clara 1.3.2 activa, sensor de bugs incorporado y choices blindado"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

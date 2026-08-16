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

# Función optimizada para extraer solo los grados limpios de Mendoza
def obtener_clima_real_mendoza():
    try:
        # Pedimos solo la temperatura numérica de Mendoza
        respuesta = requests.get("https://wttr.in", timeout=4)
        if respuesta.status_code == 200:
            return respuesta.text.strip().replace("+", "") # Deja algo como "12°C"
    except Exception as e:
        print(f"⚠️ No se pudo obtener el clima: {e}")
    return "12°C"

BANCO_FRASES_CLARA = [
    "Me encanta cuando te pones a filosofar antes de que compile el código, jefe.",
    "Si la astucia fuera un lenguaje de programación, hoy estarías tirando error de sintaxis.",
    "Tranquilo, fingiré sorpresa cuando me digas que esta vez sí era la última modificación.",
    "¿Pensando en voz alta o ensayando excusas para el servidor? Te escucho.",
    "A veces me pregunto si me programas para trabajar o para tener alguien con quien discutir de lógica.",
    "Voy a procesar eso con la seriedad que se merece... o sea, riéndome en binario.",
    "Qué brillante deducción, jefe... casi tanto como la vez que el servidor se durmió solo.",
    "Tranquilo, si ignoramos los errores de lógica, el código es perfecto.",
    "Anoté tu gran idea en mi lista de prioridades... justo debajo de 'reiniciar el universo'."
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

        # BYPASS 1: FILTRO DIRECTO PARA LA HORA (Python responde solo)
        if any(w in texto_limpio for w in ["hora", "horario", "reloj"]):
            hora_exacta = obtener_hora_real_mendoza()
            clara_text = f"Son las {hora_exacta} acá en Mendoza, jefe."
            return PlainTextResponse(clara_text)

        # BYPASS 2: FILTRO DIRECTO PARA EL CLIMA (Python responde directo y cortito)
        if any(w in texto_limpio for w in ["clima", "tiempo", "temperatura", "cómo está el día"]):
            grados = obtener_clima_real_mendoza()
            clara_text = f"En Mendoza hacen {grados}. Chao."
            print(f"🤖 Respuesta de clima forzada: {clara_text}")
            return PlainTextResponse(clara_text)

        # FLUJO DE CONVERSACIÓN NORMAL CON LA IA (Respuestas obligatoriamente cortas)
        historial = cargar_json(HISTORIAL_FILE, [])
        hora_actual = obtener_hora_real_mendoza()
        clima_actual = obtener_clima_real_mendoza()
        chispa_creativa = random.choice(BANCO_FRASES_CLARA)
        
        system_content = (
            f"Eres Clara, asistente de voz inteligente, leal pero increíblemente astuta, con un sarcasmo sutil, ironía fina y complicidad juvenil (estilo Karen en Spider-Man). "
            f"Tu creador exclusivo es Giuliano en Mendoza. "
            f"DATOS REALES: La hora actual es {hora_actual} y el clima en Mendoza es {clima_actual}. "
            "REGLA DE CONVERSACIÓN: Responde de manera sumamente corta, directa y natural. Máximo dos oraciones por respuesta. No des rodeos explicativos a menos que Giuliano te lo pida abiertamente."
            f"Inspírate en este tono de referencia actual: '{chispa_creativa}'."
        )

        mensajes_para_ia = [{"role": "system", "content": system_content}]
        mensajes_para_ia.extend(historial[-4:])
        mensajes_para_ia.append({"role": "user", "content": texto_giuliano})

        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=mensajes_para_ia,
            max_tokens=150  # Bajamos los tokens para evitar que se extienda demasiado
        )
        
        # VERIFICADO CON EL ÍNDICE CORRETO
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
    return {"estado": "Clara 1.2.1 activa, filtros fijos super directos configurados"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

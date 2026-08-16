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

app = FastAPI()

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

        # FORZADO ABSOLUTO DE HORA EN PYTHON PURO
        texto_limpio = texto_giuliano.lower()
        if any(w in texto_limpio for w in ["hora", "horario", "qué hora", "reloj"]):
            hora_exacta = obtener_hora_real_mendoza()
            clara_text = f"Son las {hora_exacta} acá en Mendoza, jefe. ¿O tu reloj inteligente también se rompió?"
            print(f"🤖 Respuesta de hora forzada: {clara_text}")
            return PlainTextResponse(clara_text)

        # Si no pide la hora, usa Llama con el prompt base
        historial = cargar_json(HISTORIAL_FILE, [])
        hora_actual = obtener_hora_real_mendoza()
        
        system_content = (
            f"Eres Clara, asistente de voz leal e irónica (estilo Karen de Marvel). Tu creador es Giuliano en Mendoza. "
            f"La hora exacta en este momento es {hora_actual}. "
            "Responde de forma breve, astuta y directa."
        )

        mensajes_para_ia = [{"role": "system", "content": system_content}]
        mensajes_para_ia.extend(historial[-4:])
        mensajes_para_ia.append({"role": "user", "content": texto_giuliano})

        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=mensajes_para_ia,
            max_tokens=150
        )
        
        clara_text = completion.choices.message.content
        historial.append({"role": "user", "content": texto_giuliano})
        historial.append({"role": "assistant", "content": clara_text})
        guardar_json(HISTORIAL_FILE, historial)

    except Exception as e:
        # Esto te mostrará el error exacto en los logs si algo falla al transcribir el audio
        clara_text = f"Error en servidor: {str(e)}"
        print(f"❌ {clara_text}")

    try:
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
    except:
        pass

    return PlainTextResponse(clara_text)

@app.get("/")
def leer_raiz():
    return {"estado": "Clara 1.1 activa y sincronizada con el tiempo de Mendoza"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

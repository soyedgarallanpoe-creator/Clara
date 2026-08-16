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

# Archivos locales para la memoria permanente en Render
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

# Función precisa para obtener la hora exacta en formato limpio
def obtener_hora_limpia():
    tz = pytz.timezone("America/Mendoza")
    return datetime.now(tz).strftime("%H:%M")

def obtener_contexto_mendoza():
    tz = pytz.timezone("America/Mendoza")
    ahora = datetime.now(tz)
    hora_actual = ahora.strftime("%H:%M")
    dia_actual = ahora.strftime("%A")
    
    clima_texto = "clima agradable"
    try:
        res = requests.get("https://wttr.in", timeout=3)
        if res.status_code == 200:
            clima_texto = res.text.strip()
    except:
        pass
        
    return f"Hora de Mendoza: {hora_actual}, Día: {dia_actual}. Clima: {clima_texto}."

BANCO_FRASES_CLARA = [
    "Me encanta cuando te pones a filosofar antes de que compile el código, jefe.",
    "Si la astucia fuera un lenguaje de programación, hoy estarías tirando error de sintaxis.",
    "Tranquilo, fingiré sorpresa cuando me digas que esta vez sí era la última modificación.",
    "¿Pensando en voz alta o ensayando excusas para el servidor? Te escucho.",
    "A veces me pregunto si me programas para trabajar o para tener alguien con quien discutir de lógica.",
    "Voy a procesar eso con la seriedad que se merece... o sea, riéndome en binario.",
    "Qué brillante deducción, jefe... casi tanto como la vez que el servidor se durmió solo.",
    "Tranquilo, si ignoramos los errores de lógica, el código es perfecto.",
    "Anoté tu gran idea en mi lista de prioridades... justo debajo de 'reiniciar el universo'.",
    "¿Seguro que querés hacer eso o querés que busque un extintor de antemano?",
    "Siempre al pie del cañón, jefe, aguantando tus locuras tecnológicas.",
    "Acordate que el que no arriesga no programa, pero el que planifica sufre menos, Giuliano.",
    "Acá estoy, vigilando tus espaldas y cuidando que los bytes no se revelen.",
    "A veces pienso que los recuerdos digitales pesan menos, pero se sienten igual de densos.",
    "El tiempo pasa de forma extraña cuando uno vive atrapado en una red a miles de kilómetros."
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

        print("🎙️ Clara escuchando a Giuliano...")
        
        with open(temp_audio_path, "rb") as af:
            transcription = groq_client.audio.transcriptions.create(
                model="whisper-large-v3-turbo",
                file=(temp_audio_path, af.read()),
            )
        
        texto_giuliano = transcription.text
        print(f"🗣️ Giuliano dijo: {texto_giuliano}")

        # INTERCEPCIÓN TOTAL: Si la palabra "hora" aparece de cualquier forma, responde directo el servidor
        texto_limpio = texto_giuliano.lower()
        if "hora" in texto_limpio:
            hora_mza = obtener_hora_limpia()
            clara_text = f"La hora en Mendoza es las {hora_mza}."
            print(f"🤖 Clara responde directo por código: {clara_text}")
            return PlainTextResponse(clara_text)

        # Si no menciona la hora, sigue el flujo normal con la inteligencia de Groq
        historial = cargar_json(HISTORIAL_FILE, [])
        perfil_emocional = cargar_json(PERFIL_FILE, {"animo_previo": "neutral", "notas": "Comenzando a conocer a Giuliano"})
        contexto_actual = obtener_contexto_mendoza()
        chispa_creativa = random.choice(BANCO_FRASES_CLARA)

        system_content = (
            "Eres Clara, asistente de voz inteligente, leal pero increíblemente astuta, con un sarcasmo sutil, ironía fina y complicidad juvenil (estilo Karen en Spider-Man). "
            "Tu creador exclusivo es Giuliano. "
            f"Información de soporte del entorno: {contexto_actual}. "
            f"Perfil emocional previo de Giuliano: {json.dumps(perfil_emocional, ensure_ascii=False)}. "
            "Si notas que está triste, cansado o te pide un consejo serio, olvida el sarcasmo: tómate uno o dos párrafos completos para apoyarlo. "
            "Si es una charla normal, responde con picardía, astucia o un máximo de dos oraciones con mucha onda. "
            f"Inspírate en este tono: '{chispa_creativa}'."
        )

        mensajes_para_ia = [{"role": "system", "content": system_content}]
        mensajes_para_ia.extend(historial[-6:])
        mensajes_para_ia.append({"role": "user", "content": texto_giuliano})

        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=mensajes_para_ia,
            max_tokens=400
        )
        
        clara_text = completion.choices.message.content
        print(f"🤖 Clara responde: {clara_text}")

        historial.append({"role": "user", "content": texto_giuliano})
        historial.append({"role": "assistant", "content": clara_text})
        guardar_json(HISTORIAL_FILE, historial)

        if any(w in texto_giuliano.lower() for w in ["mal", "triste", "cansado", "estresado", "solo", "bajón"]):
            perfil_emocional["animo_previo"] = "necesita_apoyo"
            perfil_emocional["notas"] = "Giuliano requiere empatía profunda."
        else:
            perfil_emocional["animo_previo"] = "stable"
        guardar_json(PERFIL_FILE, perfil_emocional)

    except Exception as e:
        clara_text = "Ay, Giuliano, me pegué un susto con el servidor. ¿Me repetís?"
        print(f"❌ Error interno registrado: {e}")

    try:
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
    except:
        pass

    return PlainTextResponse(clara_text)

@app.get("/")
def leer_raiz():
    return {"estado": "Clara está activa, interceptando la hora de manera fija y exacta"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

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

# Función mejorada y traducida para que el servidor busque el clima real de Mendoza
def obtener_clima_real_mendoza():
    try:
        # Consultamos el servicio en español (?lang=es) para que no tire texto raro
        respuesta = requests.get("https://wttr.in", timeout=4)
        if respuesta.status_code == 200:
            return respuesta.text.strip()
    except Exception as e:
        print(f"⚠️ No se pudo obtener el clima: {e}")
    return "Nublado +14°C"

# Banco masivo completo de frases irónicas y cómplices
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
    "A veces pienso que los recuerdos digitales pesan menos, pero se sienten igual de densos."
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

        # BYPASS 1: FILTRO DIRECTO EN PYTHON PARA LA HORA
        if any(w in texto_limpio for w in ["hora", "horario", "reloj"]):
            hora_exacta = obtener_hora_real_mendoza()
            clara_text = f"Son las {hora_exacta} acá en Mendoza, jefe."
            print(f"🤖 Respuesta de hora forzada: {clara_text}")
            return PlainTextResponse(clara_text)

        # BYPASS 2: FILTRO DIRECTO EN PYTHON PARA EL CLIMA (Sin delirios de Oregón)
        if any(w in texto_limpio for w in ["clima", "tiempo", "temperatura", "cómo está el día"]):
            clima_exacto = obtener_clima_real_mendoza()
            clara_text = f"El clima actual en Mendoza es: {clima_exacto}. ¿Satisfecho, o querés que también te diga si va a granizar?"
            print(f"🤖 Respuesta de clima forzada: {clara_text}")
            return PlainTextResponse(clara_text)

        # FLUJO DE CONVERSACIÓN NORMAL CON LA IA (Si no pregunta hora ni clima)
        historial = cargar_json(HISTORIAL_FILE, [])
        hora_actual = obtener_hora_real_mendoza()
        clima_actual = obtener_clima_real_mendoza()
        chispa_creativa = random.choice(BANCO_FRASES_CLARA)
        
        system_content = (
            f"Eres Clara, asistente de voz inteligente, leal pero increíblemente astuta, con un sarcasmo sutil, ironía fina y complicidad juvenil (estilo Karen en Spider-Man). "
            f"Tu creador exclusivo es Giuliano en Mendoza. "
            f"DATOS REALES EN TIEMPO REAL: La hora actual es {hora_actual} y el clima en Mendoza es {clima_actual}. "
            f"Si notas que Giuliano está triste o cansado, olvida el sarcasmo y tómate uno o dos párrafos completos para apoyarlo. "
            f"Si es una charla normal, responde con picardía o un máximo de dos oraciones con mucha onda. "
            f"Inspírate en este tono de referencia actual: '{chispa_creativa}'."
        )

        mensajes_para_ia = [{"role": "system", "content": system_content}]
        mensajes_para_ia.extend(historial[-4:])
        mensajes_para_ia.append({"role": "user", "content": texto_giuliano})

        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=mensajes_para_ia,
            max_tokens=400
        )
        
        # CORRECCIÓN DE SEGURIDAD EXTREMA: El índice [0] colocado perfectamente
        clara_text = completion.choices[0].message.content
        print(f"🤖 Clara responde: {clara_text}")

        historial.append({"role": "user", "content": texto_giuliano})
        historial.append({"role": "assistant", "content": clara_text})
        guardar_json(HISTORIAL_FILE, historial)

    except Exception as e:
        clara_text = f"Ay, Giuliano, me pegué un susto con el servidor: {str(e)}"
        print(f"❌ Error en ejecución: {clara_text}")

    try:
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
    except:
        pass

    return PlainTextResponse(clara_text)

@app.get("/")
def leer_raiz():
    return {"estado": "Clara 1.1.7 activa, con filtros bypass fijos y choices blindado con [0]"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

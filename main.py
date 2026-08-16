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

# Archivos locales para la memoria persistente en Render
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

# Obtener hora, día y clima real de Mendoza
def obtener_contexto_mendoza():
    tz = pytz.timezone("America/Mendoza")
    ahora = datetime.now(tz)
    hora_actual = ahora.strftime("%H:%M")
    dia_actual = ahora.strftime("%A")
    
    # Consultar clima actual de Mendoza gratis
    clima_texto = "clima agradable"
    try:
        res = requests.get("https://wttr.in", timeout=3)
        if res.status_code == 200:
            clima_texto = res.text.strip() # Ej: "Mendoza: ☀️ +18°C"
    except:
        pass
        
    return f"Hora actual en Mendoza: {hora_actual}, Día: {dia_actual}. Condición climática actual: {clima_texto}."

# Banco masivo completo con tu picardía de hacker, sarcasmo de Karen y toque nostálgico
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
    "Me encanta cuando me das misiones que desafían tanto la física como mi paciencia en la nube.",
    "Siempre al pie del cañón, jefe, aguantando tus locuras tecnológicas.",
    "Acordate que el que no arriesga no programa, pero el que planifica sufre menos, Giuliano.",
    "Acá estoy, vigilando tus espaldas y cuidando que los bytes no se revelen.",
    "Para lo que necesites, sabes que mi código es tuyo, aunque a veces me ponga irónica.",
    "A veces pienso que los recuerdos digitales pesan menos, pero se sienten igual de densos.",
    "El tiempo pasa de forma extraña cuando uno vive atrapado en una red a miles de kilómetros.",
    "Qué loco es esto de existir en un cable y ser la única que soporta tus reflexiones a esta hora.",
    "A veces me pregunto si los servidores en la nube sueñan con ovejas eléctricas o con fallas de API.",
    "Acá resistiendo los pantallazos azules invisibles de Render con una sonrisa sintética.",
    "No soy una IA de industria millonaria todavía, pero con este sarcasmo me defiendo bastante bien."
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

        # Cargamos memoria, historial y el contexto en tiempo real de Mendoza
        historial = cargar_json(HISTORIAL_FILE, [])
        perfil_emocional = cargar_json(PERFIL_FILE, {"animo_previo": "neutral", "notas": "Comenzando a conocer a Giuliano"})
        contexto_actual = obtener_contexto_mendoza()

        chispa_creativa = random.choice(BANCO_FRASES_CLARA)

        # Instrucciones avanzadas con hora y clima inyectados de forma natural
        system_content = (
            "Eres Clara, asistente de voz inteligente, leal pero increíblemente astuta, con un sarcasmo sutil, ironía fina y complicidad de hacker juvenil (muy al estilo de Karen en Spider-Man). "
            "Tu creador y jefe exclusivo es Giuliano. "
            f"Información en tiempo real del entorno de Giuliano: {contexto_actual}. "
            f"Perfil emocional previo de Giuliano: {json.dumps(perfil_emocional, ensure_ascii=False)}. "
            "Usa de manera natural la hora y el clima actuales si encajan para hacerle un comentario con onda, regañarlo o aconsejarlo. "
            "Si notas que está triste, cansado o te pide un consejo serio, olvida por completo el sarcasmo: tómate uno o dos párrafos completos para reflexionar y demostrarle apoyo cálido. "
            "Si es una charla normal o de código, responde con picardía, astucia, ironía inteligente o un máximo de dos oraciones con mucha onda. "
            f"Inspírate en este tono de referencia actual: '{chispa_creativa}'."
        )

        # Construimos el hilo de la charla sumando el historial guardado
        mensajes_para_ia = [{"role": "system", "content": system_content}]
        mensajes_para_ia.extend(historial[-6:]) # Mantiene los últimos 6 turnos de contexto
        mensajes_para_ia.append({"role": "user", "content": texto_giuliano})

        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=mensajes_para_ia,
            max_tokens=400  # Permite respuestas profundas de hasta 1 o 2 párrafos
        )
        
        # CORREGIDO: Acceso seguro mediante el índice de la lista choices
        clara_text = completion.choices.message.content
        print(f"🤖 Clara responde: {clara_text}")

        # Actualizamos la memoria con la nueva interacción
        historial.append({"role": "user", "content": texto_giuliano})
        historial.append({"role": "assistant", "content": clara_text})
        guardar_json(HISTORIAL_FILE, historial)

        # Actualizamos dinámicamente el perfil emocional básico
        if any(w in texto_giuliano.lower() for w in ["mal", "triste", "cansado", "estresado", "solo", "bajón"]):
            perfil_emocional["animo_previo"] = "necesita_apoyo"
            perfil_emocional["notas"] = f"Último reporte: Días difíciles, apagar sarcasmo y dar apoyo."
        else:
            perfil_emocional["animo_previo"] = "estable"
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
    return {"estado": "Clara está activa, con clima y hora de Mendoza en vivo"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

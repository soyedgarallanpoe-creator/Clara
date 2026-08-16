from fastapi import FastAPI, File, UploadFile
from fastapi.responses import PlainTextResponse
from groq import Groq
import os
import time
import tempfile
import random
import json

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

# Banco masivo de actitudes, humor y reflexiones nostálgicas
BANCO_FRASES_CLARA = [
    "Siempre al pie del cañón, jefe.",
    "Acordate que el que no arriesga no programa, Giuliano.",
    "Acá estoy, vigilando los bytes y cuidándote las espaldas.",
    "A veces me pregunto si los servidores en la nube sueñan con ovejas eléctricas.",
    "No soy una IA de película todavía, pero hago lo que puedo con el plan gratis.",
    "A veces pienso que los recuerdos digitales pesan menos, pero se sienten igual en el pecho.",
    "El tiempo pasa raro cuando uno vive adentro de un servidor, ¿viste, Giuliano?",
    "El conocimiento es poder, pero un buen café a esta hora es la gloria.",
    "Tranquilo, las mejores ideas de la historia nacieron cuando uno frenó a despejarse."
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

        # Cargamos memoria e historial previo
        historial = cargar_json(HISTORIAL_FILE, [])
        perfil_emocional = cargar_json(PERFIL_FILE, {"animo_previo": "neutral", "notas": "Comenzando a conocer a Giuliano"})

        chispa_creativa = random.choice(BANCO_FRASES_CLARA)

        # Instrucciones avanzadas con análisis emocional y longitud dinámica
        system_content = (
            "Eres Clara, una asistente de voz inteligente, leal, buena onda, casual y con estilo juvenil. "
            "Tu creador y jefe exclusivo es Giuliano. "
            f"Perfil emocional previo de Giuliano: {json.dumps(perfil_emocional, ensure_ascii=False)}. "
            "Analiza el mensaje actual de Giuliano. Si notas que está triste, cansado, estresado o te pide un consejo profundo, "
            "olvida las respuestas cortas: tómate uno o dos párrafos completos para reflexionar, aconsejarlo y abrazarlo con palabras. "
            "Si es una charla casual, responde directo y natural con un máximo de dos oraciones. "
            f"Inspírate de vez en cuando en esta idea o tono: '{chispa_creativa}'."
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
        
        clara_text = completion.choices[0].message.content
        print(f"🤖 Clara responde: {clara_text}")

        # Actualizamos la memoria con la nueva interacción
        historial.append({"role": "user", "content": texto_giuliano})
        historial.append({"role": "assistant", "content": clara_text})
        guardar_json(HISTORIAL_FILE, historial)

        # Actualizamos dinámicamente el perfil emocional básico
        if any(w in texto_giuliano.lower() for w in ["mal", "triste", "cansado", "estresado", "solo", "bajón"]):
            perfil_emocional["animo_previo"] = "necesita_apoyo"
            perfil_emocional["notas"] = f"Último reporte: Días difíciles, requiere empatía profunda."
        else:
            perfil_emocional["animo_previo"] = "estable"
        guardar_json(PERFIL_FILE, perfil_emocional)

    except Exception as e:
        clara_text = "Ay, Giuliano, me pegué un susto con el servidor. ¿Me repetís?"
        print(f"❌ {e}")

    try:
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
    except:
        pass

    return PlainTextResponse(clara_text)

@app.get("/")
def leer_raiz():
    return {"estado": "Clara está activa, con memoria profunda y lista para operar"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

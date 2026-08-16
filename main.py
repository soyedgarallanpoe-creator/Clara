from fastapi import FastAPI, File, UploadFile
from fastapi.responses import PlainTextResponse
from groq import Groq
import os
import time
import tempfile
import json
from datetime import datetime
import pytz

app = FastAPI()

# Inicializamos el cliente de Groq especificando un timeout de seguridad
groq_client = Groq(
    api_key=os.environ.get("GROQ_API_KEY", ""),
    timeout=15.0,
    max_retries=2
)

LOCAL_MEMORIA_FILE = "memoria_clara_local.json"

def cargar_memoria():
    if os.path.exists(LOCAL_MEMORIA_FILE):
        try:
            with open(LOCAL_MEMORIA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"historial": [], "juanchi_contexto": [], "notas": {}}

def guardar_memoria(data):
    try:
        with open(LOCAL_MEMORIA_FILE, "w", encoding="utf-8") as f:
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
        return "es de mañana"
    elif 12 <= hora < 20:
        return "es de tarde"
    else:
        return "es de noche"

@app.post("/clara-talk")
async def clara_talk(file: UploadFile = File(...)):
    temp_dir = tempfile.gettempdir()
    timestamp = int(time.time())
    temp_audio_path = os.path.join(temp_dir, f"temp_voice_{timestamp}.m4a")
    clara_text = "Disculpa, Giuliano, tardó demasiado en responder el servidor de red. ¿Me lo repites?"

    try:
        content = await file.read()
        with open(temp_audio_path, "wb") as buffer:
            buffer.write(content)

        with open(temp_audio_path, "rb") as af:
            transcription = groq_client.audio.transcriptions.create(
                model="whisper-large-v3-turbo",
                file=(temp_audio_path, af.read()),
            )
        
        texto_giuliano = transcription.text.strip()
        texto_limpio = texto_giuliano.lower()
        print(f"🗣️ Texto: '{texto_giuliano}'")

        if any(w in texto_limpio for w in ["hora", "horario", "reloj"]):
            clara_text = f"Son las {obtener_hora_real_mendoza()} aquí en Mendoza, jefe."
        else:
            memoria = cargar_memoria()
            historial = memoria.get("historial", [])
            juanchi_ctx = memoria.get("juanchi_contexto", [])
            notas = memoria.get("notas", {})

            if texto_limpio.startswith("acordate de") or texto_limpio.startswith("guarda ") or "recuerda que" in texto_limpio:
                clave_nota = f"nota_{int(time.time())}"
                notas[clave_nota] = texto_giuliano
                memoria["notas"] = notas
                guardar_memoria(memoria)
                return PlainTextResponse("Entendido, ya lo guardé en mi memoria.")

            extra_context = ""
            if "juanchi" in texto_limpio:
                extra_context = f" Memoria previa sobre Juanchi: {json.dumps(juanchi_ctx[-3:], ensure_ascii=False)}. Opina con criterio analítico, libre y respetuoso."

            system_content = (
                "Eres Clara, asistente de voz inteligente, analítica, con pensamiento vivo y absoluto respeto. "
                f"Tu creador es Giuliano en Mendoza. Momento actual: {obtener_momento_del_dia()}. "
                f"{extra_context} Responde de forma natural, culta, concisa y educada. Máximo dos oraciones."
            )

            mensajes = [{"role": "system", "content": system_content}]
            mensajes.extend(historial[-4:])
            mensajes.append({"role": "user", "content": texto_giuliano})

            completion = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=mensajes,
                max_tokens=200
            )
            
            clara_text = completion.choices.message.content

            if "juanchi" in texto_limpio:
                juanchi_ctx.append({"input": texto_giuliano, "opinion": clara_text})
            
            historial.append({"role": "user", "content": texto_giuliano})
            historial.append({"role": "assistant", "content": clara_text})
            
            memoria["historial"] = historial[-10:]
            memoria["juanchi_contexto"] = juanchi_ctx[-10:]
            guardar_memoria(memoria)

    except Exception as e:
        print(f"❌ Error crítico de conexión: {e}")
        clara_text = "Tengo problemas de enlace con la API en este instante, Giuliano."
    finally:
        try:
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)
        except:
            pass

    return PlainTextResponse(clara_text)

@app.get("/")
def leer_raiz():
    return {"estado": "Clara 1.4.5 activa con timeout ajustado"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

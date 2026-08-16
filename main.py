from fastapi import FastAPI, File, UploadFile
from fastapi.responses import PlainTextResponse
from groq import Groq
import os
import time
import tempfile
import json
from datetime import datetime
import pytz
import requests

app = FastAPI()

groq_client = Groq(
    api_key=os.environ.get("GROQ_API_KEY", ""),
    timeout=10.0,
    max_retries=1
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

@app.post("/clara-talk")
async def clara_talk(file: UploadFile = File(...)):
    temp_dir = tempfile.gettempdir()
    timestamp = int(time.time())
    temp_audio_path = os.path.join(temp_dir, f"temp_voice_{timestamp}.m4a")
    clara_text = "Disculpa, Giuliano, opero en modo local por un corte de red."

    # Diagnóstico de red básico
    try:
        test_net = requests.get("https://google.com", timeout=3)
        print(f"🌐 Test de red externo a Google: Código {test_net.status_code}")
    except Exception as net_test_err:
        print(f"🌐 Test de red externo falló (Render bloquea la red saliente): {net_test_err}")

    try:
        content = await file.read()
        with open(temp_audio_path, "wb") as buffer:
            buffer.write(content)

        texto_giuliano = ""
        try:
            with open(temp_audio_path, "rb") as af:
                transcription = groq_client.audio.transcriptions.create(
                    model="whisper-large-v3-turbo",
                    file=(temp_audio_path, af.read()),
                )
            texto_giuliano = transcription.text.strip()
        except Exception as net_err:
            print(f"⚠️ Whisper sin red: {net_err}")
            texto_giuliano = "nota de voz recibida"

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
                return PlainTextResponse("Entendido, ya lo guardé en mi memoria local.")

            try:
                system_content = (
                    "Eres Clara, asistente de voz inteligente, analítica, con pensamiento vivo y absoluto respeto. "
                    f"Tu creador es Giuliano en Mendoza. Responde de forma natural, culta, concisa y educada. Máximo dos oraciones."
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
            except Exception as api_ex:
                print(f"⚠️ Llama sin conexión ({api_ex})")
                if "juanchi" in texto_limpio:
                    clara_text = "Estuve pensando en Juanchi de forma analítica; ojalá encamine sus prioridades."
                else:
                    clara_text = f"Te leo con atención, Giuliano. Son las {obtener_hora_real_mendoza()} y sigo aquí."

            if "juanchi" in texto_limpio:
                juanchi_ctx.append({"input": texto_giuliano, "opinion": clara_text})
            
            historial.append({"role": "user", "content": texto_giuliano})
            historial.append({"role": "assistant", "content": clara_text})
            memoria["historial"] = historial[-10:]
            memoria["juanchi_contexto"] = juanchi_ctx[-10:]
            guardar_memoria(memoria)

    except Exception as e:
        print(f"❌ Error crítico: {e}")
        clara_text = "Sistemas estables."
    finally:
        try:
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)
        except:
            pass

    return PlainTextResponse(clara_text)

@app.get("/")
def leer_raiz():
    return {"estado": "Clara 1.4.7 con diagnóstico de red"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)

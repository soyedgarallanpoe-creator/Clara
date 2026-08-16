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

groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
JSONBIN_KEY = os.environ.get("JSONBIN_KEY", "")
JSONBIN_BIN_ID = os.environ.get("JSONBIN_BIN_ID", "")

LOCAL_BACKLOG_FILE = "respaldo_local_clara.json"

def cargar_respaldo_local():
    if os.path.exists(LOCAL_BACKLOG_FILE):
        try:
            with open(LOCAL_BACKLOG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"historial": [], "juanchi_contexto": [], "notas_personales": {}}

def guardar_respaldo_local(data):
    try:
        with open(LOCAL_BACKLOG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass

def cargar_memoria_nube():
    if not JSONBIN_KEY or not JSONBIN_BIN_ID:
        return cargar_respaldo_local()
    try:
        url = f"https://jsonbin.io{JSONBIN_BIN_ID}/latest"
        headers = {"X-Master-Key": JSONBIN_KEY}
        res = requests.get(url, headers=headers, timeout=4)
        if res.status_code == 200:
            datos_nube = res.json().get("record", {})
            guardar_respaldo_local(datos_nube)
            return datos_nube
    except Exception as e:
        print(f"⚠️ Aviso de red (usando respaldo local): {e}")
    return cargar_respaldo_local()

def guardar_memoria_nube(data):
    guardar_respaldo_local(data)
    if not JSONBIN_KEY or not JSONBIN_BIN_ID:
        return
    try:
        url = f"https://jsonbin.io{JSONBIN_BIN_ID}"
        headers = {"Content-Type": "application/json", "X-Master-Key": JSONBIN_KEY}
        requests.put(url, headers=headers, json=data, timeout=4)
    except Exception as e:
        print(f"⚠️ No se pudo sincronizar con la nube, operando localmente: {e}")

def obtener_hora_real_mendoza():
    tz = pytz.timezone("America/Mendoza")
    return datetime.now(tz).strftime("%H:%M")

def obtener_momento_del_dia():
    tz = pytz.timezone("America/Mendoza")
    hora = datetime.now(tz).hour
    if 6 <= hora < 12:
        return "es de mañana (buen ritmo y claridad mental para arrancar)"
    elif 12 <= hora < 20:
        return "es de tarde (pleno rendimiento cotidiano)"
    else:
        return "es de noche (momento de bajar el ritmo)"

def obtener_clima_autonomo():
    try:
        url = "https://wttr.in"
        headers = {"User-Agent": "curl/7.79.1"}
        res = requests.get(url, headers=headers, timeout=2)
        if res.status_code == 200:
            val = res.text.strip().replace("+", "")
            if val and "°C" in val:
                return val
    except:
        pass
    return "15°C"

@app.post("/clara-talk")
async def clara_talk(file: UploadFile = File(...)):
    temp_dir = tempfile.gettempdir()
    timestamp = int(time.time())
    temp_audio_path = os.path.join(temp_dir, f"temp_voice_{timestamp}.m4a")
    clara_text = "Disculpa, Giuliano, hubo un pequeño corte de red en el servidor. ¿Me lo repites?"

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

        if any(w in texto_limpio for w in ["hora", "horario", "reloj"]):
            clara_text = f"Son las {obtener_hora_real_mendoza()} aquí en Mendoza, jefe."
        elif any(w in texto_limpio for w in ["clima", "tiempo", "temperatura"]):
            clara_text = f"En Mendoza tenemos {obtener_clima_autonomo()} en este momento."
        else:
            nube_data = cargar_memoria_nube()
            historial = nube_data.get("historial", [])
            juanchi_ctx = nube_data.get("juanchi_contexto", [])
            notas = nube_data.get("notas_personales", {})

            if texto_limpio.startswith("acordate de") or texto_limpio.startswith("guarda ") or "recuerda que" in texto_limpio:
                clave_nota = f"nota_{int(time.time())}"
                notas[clave_nota] = texto_giuliano
                guardar_memoria_nube({"historial": historial, "juanchi_contexto": juanchi_ctx, "notas_personales": notas})
                return PlainTextResponse("Entendido, ya lo guardé en mi memoria permanente.")

            extra_context = ""
            if "juanchi" in texto_limpio:
                extra_context = f" Memoria sobre Juanchi registrada: {json.dumps(juanchi_ctx[-3:], ensure_ascii=False)}. Piensa y opina de forma analítica, libre y respetuosa."

            contexto_notas = f" Notas guardadas: {json.dumps(notas, ensure_ascii=False)}" if notas else ""

            system_content = (
                "Eres Clara, asistente de voz inteligente, analítica, con pensamiento vivo y absoluto respeto. "
                f"Tu creador es Giuliano en Mendoza. Hora: {obtener_hora_real_mendoza()}, Clima: {obtener_clima_autonomo()}. "
                f"{extra_context} {contexto_notas} "
                "Responde de forma natural, culta, concisa y educada. Máximo dos oraciones."
            )

            mensajes = [{"role": "system", "content": system_content}]
            mensajes.extend(historial[-4:])
            mensajes.append({"role": "user", "content": texto_giuliano})

            completion = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=mensajes,
                max_tokens=200
            )
            
            # Arreglado con el índice [0] obligatorio para la lista de choices
            clara_text = completion.choices.message.content

            if "juanchi" in texto_limpio:
                juanchi_ctx.append({"input": texto_giuliano, "opinion": clara_text})
            
            historial.append({"role": "user", "content": texto_giuliano})
            historial.append({"role": "assistant", "content": clara_text})
            
            guardar_memoria_nube({
                "historial": historial[-10:],
                "juanchi_contexto": juanchi_ctx[-10:],
                "notas_personales": notas
            })

    except Exception as e:
        print(f"❌ Error controlado en ejecución: {e}")
    finally:
        try:
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)
        except:
            pass

    return PlainTextResponse(clara_text)

@app.get("/")
def leer_raiz():
    return {"estado": "Clara 1.4.3 activa con el índice [0] corregido"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

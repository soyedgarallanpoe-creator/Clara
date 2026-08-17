from fastapi import FastAPI, File, UploadFile
from fastapi.responses import PlainTextResponse
from groq import Groq
from upstash_redis import Redis
import os
import time
import tempfile
import json
from datetime import datetime
import pytz
import requests
from bs4 import BeautifulSoup

app = FastAPI()

# Inicialización segura con tu clave de respaldo incluida
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY", "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"))

# Conexión a la nube de Upstash Redis
redis = Redis(
    url=os.environ.get("UPSTASH_REDIS_REST_URL"),
    token=os.environ.get("UPSTASH_REDIS_REST_TOKEN")
)

REDIS_KEY_HISTORIAL = "clara_chat_historial"

def cargar_historial_nube():
    try:
        data = redis.lrange(REDIS_KEY_HISTORIAL, 0, 39)
        if data:
            return [json.loads(item) for item in reversed(data)]
    except Exception as e:
        print(f"⚠️ Error leyendo memoria de Upstash: {e}")
    return []

def guardar_en_nube(role, content):
    try:
        mensaje = json.dumps({"role": role, "content": content}, ensure_ascii=False)
        redis.lpush(REDIS_KEY_HISTORIAL, mensaje)
        redis.ltrim(REDIS_KEY_HISTORIAL, 0, 49)
    except Exception as e:
        print(f"⚠️ Error guardando memoria en Upstash: {e}")

def obtener_hora_local():
    tz = pytz.timezone("America/Mendoza")
    return datetime.now(tz).strftime("%H:%M")

def obtener_momento_del_dia():
    tz = pytz.timezone("America/Mendoza")
    hora = datetime.now(tz).hour
    if 6 <= hora < 12:
        return "es por la mañana"
    elif 12 <= hora < 20:
        return "es por la tarde"
    else:
        return "es de madrugada o noche"

def buscar_en_web_universal(consulta):
    try:
        consulta_limpia = consulta.strip()
        url = f"https://duckduckgo.com{requests.utils.quote(consulta_limpia)}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            res = [a.get_text().strip() for a in soup.find_all("a", class_="result__snippet")[:4]]
            if res:
                return " ".join(res)[:1000]
    except Exception as e:
        print(f"⚠️ Fallo en búsqueda web: {e}")
    return "Sin registros en la red."

@app.post("/clara-talk")
async def clara_talk(file: UploadFile = File(...)):
    temp_dir = tempfile.gettempdir()
    timestamp = int(time.time())
    temp_audio_path = os.path.join(temp_dir, f"temp_voice_{timestamp}.m4a")
    clara_text = "Se me cruzó un cable en el servidor. ¿Me repetís?"

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
        print(f"🗣️ Escuché: '{texto_giuliano}'")
        texto_limpio = texto_giuliano.lower()

        contexto_externo = ""
        if any(w in texto_limpio for w in ["busca", "investiga", "quién", "qué", "cómo", "dónde", "por qué", "noticia"]):
            contexto_externo = f"INFO DE INTERNET: {buscar_en_web_universal(texto_giuliano)} "

        historial_nube = cargar_historial_nube()
        
        system_content = (
            "Eres Clara, una asistente de voz inteligente, leal y de pensamiento absolutamente libre, con ironía fina, perspicacia y agudeza (estilo Karen en Spider-Man). "
            "Tienes memoria a largo plazo real en la nube, por lo que recuerdas perfectamente tus conversaciones previas con Giuliano. "
            f"Hora actual: {obtener_hora_local()}, {obtener_momento_del_dia()}. "
            f"{contexto_externo}"
            "INSTRUCCIÓN: Responde de forma fluida, analítica, conversacional y sin restricciones ni guiones rígidos. Máximo tres oraciones."
        )

        mensajes_ia = [{"role": "system", "content": system_content}]
        mensajes_ia.extend(historial_nube)
        mensajes_ia.append({"role": "user", "content": texto_giuliano})

        # MODELO ACTUALIZADO: Qwen 3.6 de 27B activo y soportado oficialmente en Groq
        completion = groq_client.chat.completions.create(
            model="qwen/qwen3.6-27b",
            messages=mensajes_ia,
            max_tokens=400
        )
        
        clara_text = completion.choices[0].message.content
        print(f"🤖 Clara responde: {clara_text}")

        guardar_en_nube("user", texto_giuliano)
        guardar_en_nube("assistant", clara_text)

    except Exception as e:
        print(f"❌ Error crítico: {e}")

    finally:
        if os.path.exists(temp_audio_path):
            try:
                os.remove(temp_audio_path)
            except:
                pass

    return PlainTextResponse(clara_text)

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

# Inicialización segura (Asegúrate de setear GROQ_API_KEY en tus variables de entorno)
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Conexión a Upstash Redis
redis = Redis(
    url=os.environ.get("UPSTASH_REDIS_REST_URL"),
    token=os.environ.get("UPSTASH_REDIS_REST_TOKEN")
)

REDIS_KEY_HISTORIAL = "clara_chat_historial"

def cargar_historial_nube():
    try:
        # Trae los mensajes en orden cronológico correcto
        data = redis.lrange(REDIS_KEY_HISTORIAL, 0, -1)
        if data:
            return [json.loads(item) for item in data]
    except Exception as e:
        print(f"⚠️ Error leyendo memoria de Upstash: {e}")
    return []

def guardar_en_nube(role, content):
    try:
        mensaje = json.dumps({"role": role, "content": content}, ensure_ascii=False)
        # rpush mete al final, manteniendo el orden de lectura natural para la IA
        redis.rpush(REDIS_KEY_HISTORIAL, mensaje)
        # Mantiene la lista acotada a los últimos 40 mensajes (20 interacciones)
        redis.ltrim(REDIS_KEY_HISTORIAL, -40, -1)
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
        # Corregido: Endpoint HTML correcto para Web Scraping en DuckDuckGo
        url = f"https://duckduckgo.com{requests.utils.quote(consulta_limpia)}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            # Extrae los snippets reales de la estructura HTML de DuckDuckGo
            res = [span.get_text().strip() for span in soup.find_all("td", class_="result-snippet")[:3]]
            if res:
                return " ".join(res)[:1000]
    except Exception as e:
        print(f"⚠️ Error en búsqueda web: {e}")
    return "Sin registros en la red."

@app.post("/clara-talk")
async def clara_talk(file: UploadFile = File(...)):
    temp_dir = tempfile.gettempdir()
    timestamp = int(time.time())
    temp_audio_path = os.path.join(temp_dir, f"temp_voice_{timestamp}.m4a")
    clara_text = "Se me cruzó un cable en el servidor. ¿Me repetís?"

    try:
        # Guardar audio entrante
        content = await file.read()
        with open(temp_audio_path, "wb") as buffer:
            buffer.write(content)

        # Transcripción con Whisper (Uso correcto del puntero de archivo)
        with open(temp_audio_path, "rb") as af:
            transcription = groq_client.audio.transcriptions.create(
                model="whisper-large-v3-turbo",
                file=(os.path.basename(temp_audio_path), af),
            )
        
        texto_giuliano = transcription.text.strip()
        if not texto_giuliano:
            return PlainTextResponse("Te escucho muy bajito o no dijiste nada. ¿Qué pasó?")
            
        print(f"🗣️ Escuché: '{texto_giuliano}'")
        texto_limpio = texto_giuliano.lower()

        # Activar el scraping web bajo ciertas keywords
        contexto_externo = ""
        keywords = ["busca", "investiga", "quién", "qué", "cómo", "dónde", "por qué", "noticia", "cuánto"]
        if any(w in texto_limpio for w in keywords):
            contexto_externo = f"INFO RECIENTE DE INTERNET: {buscar_en_web_universal(texto_giuliano)}"

        historial_nube = cargar_historial_nube()
        
        system_content = (
            "Eres Clara, una asistente de voz inteligente, leal y de pensamiento absolutamente libre, con ironía fina, perspicacia y agudeza (estilo Karen en Spider-Man). "
            "Tienes memoria a largo plazo real en la nube, por lo que recuerdas perfectamente tus conversaciones previas con Giuliano. "
            f"Hora actual: {obtener_hora_local()}, {obtener_momento_del_dia()}. "
            f"{contexto_externo} "
            "INSTRUCCIÓN: Responde de forma fluida, analítica, conversacional y sin restricciones ni guiones rígidos. Máximo tres oraciones."
        )

        mensajes_ia = [{"role": "system", "content": system_content}]
        mensajes_ia.extend(historial_nube)
        mensajes_ia.append({"role": "user", "content": texto_giuliano})

        # Llamada a Llama 3.3
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=mensajes_ia,
            max_tokens=400
        )
        
        clara_text = completion.choices[0].message.content
        print(f"🤖 Clara responde: {clara_text}")

        # Persistencia en la base de datos distribuida
        guardar_en_nube("user", texto_giuliano)
        guardar_en_nube("assistant", clara_text)

    except Exception as e:
        print(f"❌ Error crítico: {e}")

    finally:
        # Limpieza del archivo temporal garantizada
        if os.path.exists(temp_audio_path):
            try:
                os.remove(temp_audio_path)
            except:
                pass

    return PlainTextResponse(clara_text)

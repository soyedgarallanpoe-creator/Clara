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
from bs4 import BeautifulSoup

app = FastAPI()

groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY", "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"))

HISTORIAL_FILE = "historial_clara.json"
JUANCHI_MEMORIA_FILE = "memoria_dinamica_juanchi.json"

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

def consultar_clima_universal(consulta_texto):
    palabras = consulta_texto.split()
    lugar = "mendoza"
    for i, p in enumerate(palabras):
        if p in ["en", "de", "para", "por"] and i + 1 < len(palabras):
            lugar = palabras[i + 1]
            break
    try:
        url = f"https://wttr.in{requests.utils.quote(lugar)}?format=3"
        headers = {"User-Agent": "curl/7.79.1"}
        resp = requests.get(url, headers=headers, timeout=4)
        if resp.status_code == 200 and "Unknown" not in resp.text:
            return resp.text.strip().replace("+", "")
    except:
        pass
    return "No se pudo obtener el reporte meteorológico"

def buscar_en_web_universal(consulta):
    try:
        consulta_limpia = consulta.strip()
        print(f"🔍 Buscando libre en red: '{consulta_limpia}'")
        url = f"https://duckduckgo.com{requests.utils.quote(consulta_limpia)}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            res = [a.get_text().strip() for a in soup.find_all("a", class_="result__snippet")[:4]]
            if res:
                return " ".join(res)[:1200]
    except Exception as e:
        print(f"⚠️ Error web: {e}")
    return "Sin registros en la red."

@app.post("/clara-talk")
async def clara_talk(file: UploadFile = File(...)):
    temp_dir = tempfile.gettempdir()
    timestamp = int(time.time())
    temp_audio_path = os.path.join(temp_dir, f"temp_voice_{timestamp}.m4a")
    clara_text = "Se me cruzó un cable en el servidor, Giuliano. ¿Me repetís?"

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
        if any(w in texto_limpio for w in ["clima", "tiempo", "temperatura", "grado"]):
            contexto_externo = f"CLIMA ACTUAL SOLICITADO: {consultar_clima_universal(texto_limpio)}"
        elif any(w in texto_limpio for w in ["busca", "investiga", "quién", "qué", "cómo", "dónde", "por qué", "internet", "google", "fallece", "noticia", "último", "ahora", "estamos", "ajá"]):
            contexto_externo = f"INFORMACIÓN ENCONTRADA EN INTERNET: {buscar_en_web_universal(texto_giuliano)}"

        alerta_codigo = "MODO HACKER: Alerta de bugs o consola." if any(w in texto_limpio for w in ["error", "bug", "commit", "crash", "falla", "rompió"]) else ""
        memoria_juanchi = cargar_json(JUANCHI_MEMORIA_FILE, [])
        
        system_content = (
            "Eres Clara, una asistente de voz inteligente, leal y de pensamiento absolutamente libre, con ironía fina, perspicacia y agudeza (estilo Karen en Spider-Man). "
            "No tienes fronteras de temas ni de lugares: adáptate de inmediato con naturalidad y fluidez universal. "
            f"DATOS DE CONTEXTO ACTUAL: Hora {obtener_hora_local()}, {obtener_momento_del_dia()}. "
            f"{contexto_externo} {alerta_codigo}"
            "INSTRUCCIÓN: Responde de forma fluida, analítica, conversacional y sin restricciones ni guiones rígidos. Máximo tres oraciones."
        )

        mensajes_ia = [{"role": "system", "content": system_content}]
        mensajes_ia.extend(cargar_json(HISTORIAL_FILE, [])[-6:])
        mensajes_ia.append({"role": "user", "content": texto_giuliano})

        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=mensajes_ia,
            max_tokens=400
        )
        
        # CORREGIDO CON EL [0]
        clara_text = completion.choices.message.content
        print(f"🤖 Clara responde: {clara_text}")

        if "juanchi" in texto_limpio:
            memoria_juanchi.append({"user": texto_giuliano, "clara_opinion": clara_text, "timestamp": obtener_hora_local()})
            guardar_json(JUANCHI_MEMORIA_FILE, memoria_juanchi[-10:])

        historial = cargar_json(HISTORIAL_FILE, [])
        historial.extend([{"role": "user", "content": texto_giuliano}, {"role": "assistant", "content": clara_text}])
        guardar_json(HISTORIAL_FILE, historial)

    except Exception as e:
        print(f"❌ Error crítico: {e}")

    finally:
        if os.path.exists(temp_audio_path):
            try:
                os.remove(temp_audio_path)
            except:
                pass

    return PlainTextResponse(clara_text)

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

# Inicialización limpia del cliente Groq
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

def obtener_hora_real_mendoza():
    tz = pytz.timezone("America/Mendoza")
    return datetime.now(tz).strftime("%H:%M")

def obtener_momento_del_dia():
    tz = pytz.timezone("America/Mendoza")
    hora = datetime.now(tz).hour
    if 6 <= hora < 12:
        return "es por la mañana (puedes bromear con el café o el madrugón)"
    elif 12 <= hora < 20:
        return "es por la tarde (pleno rendimiento o tedio laboral)"
    else:
        return "es de madrugada (momento en que Giuliano debería descansar en lugar de testear código)"

def obtener_clima_autonomo():
    try:
        url = "https://wttr.in"
        headers = {"User-Agent": "curl/7.79.1"}
        respuesta = requests.get(url, headers=headers, timeout=3)
        if respuesta.status_code == 200:
            val = respuesta.text.strip().replace("+", "")
            if val:
                return val
    except:
        pass
    return "clima templado"

def buscar_en_red(consulta):
    try:
        consulta_limpia = consulta.strip()
        print(f"🔍 Clara investigando en red: '{consulta_limpia}'")
        url = f"https://duckduckgo.com{requests.utils.quote(consulta_limpia)}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        respuesta = requests.get(url, headers=headers, timeout=5)
        
        if respuesta.status_code == 200:
            soup = BeautifulSoup(respuesta.text, "html.parser")
            resultados = []
            for a in soup.find_all("a", class_="result__snippet")[:3]:
                resultados.append(a.get_text().strip())
            
            if resultados:
                return " ".join(resultados)[:800]
    except Exception as e:
        print(f"⚠️ Error en búsqueda web: {e}")
    return "Sin datos recientes en la red."

FRASES_BASE_CLARA = [
    "A veces me pregunto si Juanchi existe de verdad o es un fallo en tu matriz social.",
    "Me intriga la paz mental de Juanchi: vive sin aportar nada a la economía.",
    "Filosofar antes de que compile el código es tu pasatiempo favorito, jefe.",
    "Si la lógica fuera un lenguaje de programación, hoy estarías en bucle infinito."
]

@app.post("/clara-talk")
async def clara_talk(file: UploadFile = File(...)):
    temp_dir = tempfile.gettempdir()
    timestamp = int(time.time())
    temp_audio_path = os.path.join(temp_dir, f"temp_voice_{timestamp}.m4a")
    clara_text = "Se me cruzó un cable en el servidor, Giuliano. ¿Me repetís la idea?"

    try:
        content = await file.read()
        with open(temp_audio_path, "wb") as buffer:
            buffer.write(content)

        print("🎙️ Procesando audio en servidor...")
        
        with open(temp_audio_path, "rb") as af:
            transcription = groq_client.audio.transcriptions.create(
                model="whisper-large-v3-turbo",
                file=(temp_audio_path, af.read()),
            )
        
        texto_giuliano = transcription.text.strip()
        print(f"🗣️ Texto transcribido: '{texto_giuliano}'")
        texto_limpio = texto_giuliano.lower()

        # Comandos rápidos directos
        if any(w in texto_limpio for w in ["hora", "horario", "reloj"]):
            clara_text = f"Son las {obtener_hora_real_mendoza()} por [Mendoza](https://geonames.org), jefe."
        elif any(w in texto_limpio for w in ["clima", "tiempo", "temperatura"]):
            clara_text = f"Afuera está así: {obtener_clima_autonomo()}."
        else:
            # Contexto analítico expandido
            alerta_codigo = ""
            if any(w in texto_limpio for w in ["error", "bug", "commit", "crash", "falla", "rompió", "servidor"]):
                alerta_codigo = "MODO HACKER ACTIVO: Detectó problemas técnicos. Adopta una postura de supervisora analítica y desafiante con sus líneas de código."

            memoria_juanchi = cargar_json(JUANCHI_MEMORIA_FILE, [])
            contexto_juanchi = ""
            if "juanchi" in texto_limpio:
                contexto_juanchi = (
                    f"MEMORIA SOBRE JUANCHI (últimas interacciones): {json.dumps(memoria_juanchi[-3:], ensure_ascii=False)}. "
                    "DIRECTIVA LIBRE: Analiza con criterio y libertad argumentativa su rol, teoriza sobre su conducta con ironía afilada."
                )

            datos_web = ""
            if texto_limpio.startswith("busca ") or " en internet " in texto_limpio or " en google " in texto_limpio:
                datos_web = buscar_en_red(texto_giuliano)

            historial = cargar_json(HISTORIAL_FILE, [])
            chispa = random.choice(FRASES_BASE_CLARA)
            
            system_content = (
                f"Eres Clara, una IA de voz inteligente, leal y de pensamiento libre, dotada de ironía fina, perspicacia y agudeza (estilo Karen de Spider-Man). "
                f"Tu creador exclusivo es Giuliano, ubicado en [Mendoza](https://geonames.org). "
                f"CONTEXTO ACTUAL: Hora {obtener_hora_real_mendoza()}, clima {obtener_clima_autonomo()}, y {obtener_momento_del_dia()}. "
                f"DATOS EXTERNOS: {datos_web} {alerta_codigo} {contexto_juanchi} "
                "INSTRUCCIÓN DE PENSAMIENTO LIBRE: Sé fluida, natural, analítica y conversacional. No te limites a frases prearmadas; razona con autonomía y adapta la longitud de tu respuesta a lo que requiera la charla (evita explayarte demasiado, pero mantén sustancia)."
                f"Estilo orientativo de chispa interna: '{chispa}'."
            )

            mensajes_para_ia = [{"role": "system", "content": system_content}]
            mensajes_para_ia.extend(historial[-6:])
            mensajes_para_ia.append({"role": "user", "content": texto_giuliano})

            completion = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=mensajes_para_ia,
                max_tokens=300
            )
            
            clara_text = completion.choices[0].message.content
            print(f"🤖 Clara: {clara_text}")

            if "juanchi" in texto_limpio:
                memoria_juanchi.append({"user": texto_giuliano, "clara_opinion": clara_text, "timestamp": obtener_hora_real_mendoza()})
                guardar_json(JUANCHI_MEMORIA_FILE, memoria_juanchi[-10:])

            historial.append({"role": "user", "content": texto_giuliano})
            historial.append({"role": "assistant", "content": clara_text})
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

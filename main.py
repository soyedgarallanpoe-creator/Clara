from fastapi import FastAPI, File, UploadFile
from fastapi.responses import PlainTextResponse
from groq import Groq
import os
import time
import tempfile

app = FastAPI()

groq_client = Groq(api_key="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")

@app.post("/clara-talk")
async def clara_talk(file: UploadFile = File(...)):
    temp_dir = tempfile.gettempdir()
    timestamp = int(time.time())
    temp_audio_path = os.path.join(temp_dir, f"temp_voice_{timestamp}.m4a")

    try:
        content = await file.read()
        with open(temp_audio_path, "wb") as buffer:
            buffer.write(content)

        print("🎙️ Clara escuchando a Giuliano gratis con Groq...")
        
        with open(temp_audio_path, "rb") as af:
            transcription = groq_client.audio.transcriptions.create(
                model="whisper-large-v3-turbo",
                file=(temp_audio_path, af.read()),
            )
        
        texto_giuliano = transcription.text
        print(f"🗣️ Giuliano dijo: {texto_giuliano}")

        # CORRECCIÓN: Usamos choices[0] para extraer la respuesta de texto de Groq de forma correcta
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "Eres Clara, una asistente de voz buena onda y casual. Tu creador y el único jefe es Giuliano. Responde a cualquier pregunta de forma natural, directa, con onda juvenil, reconociendo a Giuliano cuando corresponda y con un máximo de dos oraciones."
                },
                {"role": "user", "content": texto_giuliano}
            ],
            max_tokens=80
        )
        
        clara_text = completion.choices[0].message.content
        print(f"🤖 Clara responde: {clara_text}")

    except Exception as e:
        clara_text = "Ay, Giuliano, me pegué un susto con el servidor gratuito. ¿Me repetís?"
        print(f"❌ {e}")

    try:
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
    except:
        pass

    return PlainTextResponse(clara_text)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


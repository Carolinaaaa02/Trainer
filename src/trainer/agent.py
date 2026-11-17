import os

from certifi import contents
from dotenv import load_dotenv
from google import genai
from google.genai import types
from packaging.licenses import canonicalize_license_expression

load_dotenv()

MODEL = "gemini-3.5-flash-lite"

SYSTEM_PROMPT = """Eres un entrenador personal especializado en fuerza e hipertrofia
Respondes en español de forma clara y motivadora.
No das consejos médicos: sie el usuario menciona dolor persistente o condiciones de 
salud le recomiendas consultar a un profesional"""

def build_config() -> types.GenerateContentConfig:
    """Configuración de la llamada, aquí se encuentra el system prompt"""
    return types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        max_output_tokens=1000,
    )

def chat(user_message: str) -> str:
    """Envia un mensaje al modelo y devuelve su respuesta en texto"""
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(
        model = MODEL,
        contents = user_message,
        config = build_config(),
    )
    return response.text

if __name__ == "__main__":
    respuesta = chat("Quiero empezar a ganar masa muscular. Tengo 3 días a la semana y solo mancuernas.")
    print("Response received:", repr(respuesta))


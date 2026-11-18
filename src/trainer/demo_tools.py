import os

from google import genai
from google.genai import types

from src.trainer.agent import MODEL, SYSTEM_PROMPT
from src.trainer.llm import to_gemini_tool
from src.trainer.tools import TOOLS

MESSAGES = [
    "Hoy hice 3 series de sentadilla goblet con 20 kg, 10 repeticiones cada una.",
    "Qué ejercicios de pecho puedo hacer con mancuernas?",
    "Me duele la rodilla izquierda desde hace una semana.",
    "Hoy hice 3 series de sentadilla goblet con 20 kg",
]

if __name__ == "__main__":
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[to_gemini_tool(TOOLS)],
    )
    for message in MESSAGES:
        print(f"\nUsuario: {message}")
        response = client.models.generate_content(
            model=MODEL, contents=message, config=config
        )
        calls = response.function_calls or []
        if not calls:
            print("  (sin herramientas) Respuesta:", response.text)
        for call in calls:
            print(f"  Herramienta pedida: {call.name}")
            print(f"  Argumentos: {dict(call.args or {})}")
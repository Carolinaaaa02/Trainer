import os
from dotenv import load_dotenv
from google import genai
from google.genai import errors

from src.trainer.agent import MODEL, build_system_prompt
from src.trainer.agent_loop import Agent
from src.trainer.db import connect, init_db
from src.trainer.llm import GeminiModel
from src.trainer.repository import add_user, get_first_user_id
from src.trainer.tools import TOOLS
from datetime import date

EXIT_WORDS = {"salir", "exit", "quit"}

def main() -> None:
    load_dotenv(override=True)
    conn = connect()
    init_db(conn)

    user_id = get_first_user_id(conn)
    if user_id is None:
        name = input("Aún no hay usuarios. ¿Como te llamas?").strip() or "Usuario"
        user_id = add_user(conn, name, "mejorar condición física", 3, "mancuernas")

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    agent = Agent(GeminiModel(client, MODEL, build_system_prompt(date.today()), TOOLS), conn, user_id)

    print("Entrenador listo. Escribe 'salir' para terminar")
    while True:
        try:
            text = input("\nTú: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if text.lower() in EXIT_WORDS:
            break
        if not text:
            continue

        try:
            reply = agent.send(text)
        except errors.APIError as exc:
            print(f"\n(No pude contactar al modelo: error {exc.code}. Intenta de nuevo en un momento.)")
            continue
        for trace in reply.tool_calls:
            status = "error" if "error" in trace.result else "ok"
            print(f" [herramienta] {trace.name} {trace.args} -> {status}")
            if reply.guardrail:
                print(f' [guardrail] {reply.guardrail}')
        print(f"\nEntrenador: {reply.text}")

if __name__ == "__main__":
    main()
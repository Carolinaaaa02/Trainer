import time
from typing import Any

from google import genai
from google.genai import errors, types

from src.trainer.agent_loop import ModelReply, ToolCall
from src.trainer.tools import ToolSpec, JsonDict

MAX_RETRIES = 6
RETRYABLE_CODES = {429, 500, 502, 503, 504}

def to_gemini_tool(specs: list[ToolSpec]) -> types.Tool:
    declarations: list[dict[str, object]] = []
    for spec in specs:
        declaration: dict[str, object] = {
            "name": spec.name,
            "description": spec.description
        }
        if spec.parameters is not None:
            declaration["parameters"] = spec.parameters
        declarations.append(declaration)
    return types.Tool(function_declarations=declarations)

class GeminiModel:
    def __init__(
        self,
        client: genai.Client,
        model: str,
        system_prompt: str,
        tools: list[ToolSpec],
    ) -> None:
        self._client = client
        self._model = model
        self._config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=[to_gemini_tool(tools)],
        )

    def user_message(self, text: str) -> types.Content:
        return types.Content(role="user", parts=[types.Part.from_text(text=text)])

    def model_message(self, text: str) -> types.Content:
        return types.Content(role="model", parts=[types.Part.from_text(text=text)])

    def tool_results_message(self, results: list[tuple[str, JsonDict]]):
        parts = [
            types.Part.from_function_response(name=name, response=result)
            for name, result in results
        ]
        return types.Content(role="user", parts=parts)

    def generate(self, history: list[Any]) -> ModelReply:
        response = self._generate_with_retry(history)
        candidates = response.candidates or []
        content = candidates[0].content if candidates else None

        if content is None or not  content.parts:
            text = "(El modelo no devolvió  respuesta, inteta reformular)"
            message = types.Content(role="model", parts=[types.Part.from_text(text=text)])
            return ModelReply(message=message, text=text, tool_calls=[])

        text = "".join(part.text for part in content.parts if part.text and not part.thought)
        calls = [
            ToolCall(name=part.function_call.name or "", args=dict(part.function_call.args or {}))
            for part in content.parts
            if part.function_call
        ]
        return ModelReply(message=content, text=text, tool_calls=calls)

    def _generate_with_retry(self, history: list[Any]) -> types.GenerateContentResponse:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return self._client.models.generate_content(
                    model=self._model, contents=history, config=self._config
                )
            except errors.APIError as exc:
                if exc.code not in RETRYABLE_CODES or attempt == MAX_RETRIES:
                    raise
                wait = min(2**attempt, 20)
                print(f" (Servicio ocupado, reintentando en {wait}s...)")
                time.sleep(wait)
        raise RuntimeError("Inalcanzable")


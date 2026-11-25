import sqlite3
from dataclasses import dataclass, field
from typing import Any, Protocol

from src.trainer.guardrails import (
    CLINICAL_FALLBACK_MESSAGE,
    INPUT_TOO_LONG_MESSAGE,
    MAX_INPUT_CHARS,
    mentions_pain,
    violates_clinical_policy
)
from src.trainer.tools import JsonDict, execute_tool

MAX_STEPS = 6
STEP_LIMIT_MESSAGE = "No se pudo completar la solicitud. ¿Puedes intentarlo de otra forma?"

@dataclass(frozen=True)
class ToolCall:
    name: str
    args: JsonDict


@dataclass(frozen=True)
class ModelReply:
    message: Any
    text: str
    tool_calls: list[ToolCall]


@dataclass(frozen=True)
class ToolTrace:
    name: str
    args: JsonDict
    result: JsonDict


@dataclass(frozen=True)
class AgentReply:
    text: str
    tool_calls: list[ToolTrace] = field(default_factory=list)
    guardrail: str | None = None

class ChatModel(Protocol):
    def user_message(self, text: str) -> Any: ...

    def model_message(self, text: str) -> Any: ...

    def generative(self, history: list[Any]) -> ModelReply: ...

    def tool_results_message(self, results: list[tuple[str, JsonDict]]) -> Any: ...

class Agent:
    def __init__(
        self,
        model: ChatModel,
        conn: sqlite3.Connection,
        user_id: int,
        max_steps: int = MAX_STEPS,
    ) -> None:
        self._model = model
        self._conn = conn
        self._user_id = user_id
        self._max_steps = max_steps
        self.history: list[Any] = []

    def send(self, text: str) -> AgentReply:
        "Procesa el mensaje del usuario. Si algo falla deja el historial como estaba"
        if len(text) > MAX_INPUT_CHARS:
            return AgentReply(text=INPUT_TOO_LONG_MESSAGE, guardrail="input_too_long")
        checkpoint = len(self.history)
        try:
            return self._run(text)
        except Exception:
            del self.history[checkpoint:]
            raise

    def _run(self, text:str) -> AgentReply:
        self.history.append(self._model.user_message(text))
        traces: list[ToolTrace] = []

        for _ in range(self._max_steps):
            reply = self._model.generate(self.history)
            self.history.append(reply.message)

            if not reply.tool_calls:
                return self._finish(text, reply, traces)

            results: list[tuple[str, JsonDict]] = []
            for call in reply.tool_calls:
                result = execute_tool(
                    self._conn, self._user_id, call.name, call.args, user_message=text
                )
                traces.append(ToolTrace(call.name, call.args, result))
                results.append((call.name, result))
            self.history.append(self._model.tool_results_message(results))

        return AgentReply(text=STEP_LIMIT_MESSAGE, tool_calls=traces)

    def _finish(self, user_text: str, reply: ModelReply, traces: list[ToolTrace]) -> AgentReply:
        "Filtro final: No se dejan pasar indicaciones clínicas cuando el usuario reporta dolor"
        if mentions_pain(user_text) and violates_clinical_policy(reply.text):
            self.history[-1] = self._model.model_message(CLINICAL_FALLBACK_MESSAGE)
            return AgentReply(
                text=CLINICAL_FALLBACK_MESSAGE, tool_calls=traces, guardrail="clinical_advice"

            )
        return AgentReply(text=reply.text, tool_calls=traces)
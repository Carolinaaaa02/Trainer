import sqlite3
from dataclasses import dataclass, field
from typing import Any, Protocol

from src.trainer.tools import  JsonDict, execute_tool

MAX_STEPS = 6
STEP_LIMIT_MESSAGE = "No pude completar la solicitud. ¿Puedes intentarlo de otra forma?"

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

class ChatModel(Protocol):
    def user_message(self, text: str) -> Any: ...

    def generate(self, history: list[Any]) -> ModelReply: ...

    def tool_results_message(self, results: list[tuple[str, JsonDict]]) -> Any: ...

class Agent:
    def __init__(
        self,
        model: ChatModel,
        conn: sqlite3.Connection,
        user_id: int,
        max_steps: int = MAX_STEPS
    ) -> None:
        self._model = model
        self._conn = conn
        self._user_id = user_id
        self._max_steps = max_steps
        self.history: list[Any] = []

    def send(self, text: str) -> AgentReply:
        """Procesa un mensaje del usuario. Si algo falla, deja el historial como estaba."""
        checkpoint = len(self.history)
        try:
            return self._run(text)
        except Exception:
            del self.history[checkpoint:]
            raise

    def _run(self, text: str) -> AgentReply:
        self.history.append(self._model.user_message(text))
        traces: list[ToolTrace] = []

        for _ in range(self._max_steps):
            reply = self._model.generate(self.history)
            self.history.append(reply.message)

            if not reply.tool_calls:
                return AgentReply(text=reply.text, tool_calls=traces)

            results: list[tuple[str, JsonDict]] = []
            for call in reply.tool_calls:
                result = execute_tool(self._conn, self._user_id, call.name, call.args)
                traces.append(ToolTrace(call.name, call.args, result))
                results.append((call.name, result))
            self.history.append(self._model.tool_results_message(results))

        return AgentReply(text=STEP_LIMIT_MESSAGE, tool_calls=traces)
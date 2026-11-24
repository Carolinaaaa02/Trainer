import sqlite3
import pytest
from typing import Any

from src.trainer.agent_loop import Agent, ModelReply, ToolCall
from src.trainer.repository import add_exercise, add_user, get_recent_workouts
from src.trainer.tools import JsonDict

def say(text: str) -> ModelReply:
    return ModelReply(message={"role": "model", "text": text}, text=text, tool_calls=[])

def call(name: str, args: JsonDict) -> ModelReply:
    return ModelReply(
        message={"role": "model", "call": name},
        text="",
        tool_calls=[ToolCall(name, args)]
    )

class FakeModel:

    def __init__(self, replies: list[ModelReply]) -> None:
        self._replies = list(replies)
        self.history_sizes: list[int] = []

    def user_message(self, text: str) -> Any:
        return {"role": "user", "text": text}

    def generate(self, history: list[Any]) -> ModelReply:
        self.history_sizes.append(len(history))
        return self._replies.pop(0)

    def tool_results_message(self, results: list[tuple[str, JsonDict]]) -> Any:
        return {"role": "tool", "results": results}

def seed(conn: sqlite3.Connection) -> int:
    user_id = add_user(conn, "Ana", "ganar masa muscular", 3, "mancuernas")
    add_exercise(conn, "Sentadilla goblet", "piernas", "mancuernas", "principiante")
    return user_id


def test_plain_answer_uses_no_tools(conn: sqlite3.Connection) -> None:
    agent = Agent(FakeModel([say("Hola, Ana")]), conn, seed(conn))
    reply = agent.send("hola")
    assert reply.text == "Hola, Ana"
    assert reply.tool_calls == []


def test_tool_is_executed_and_result_is_fed_back(conn: sqlite3.Connection) -> None:
    model = FakeModel([call("get_user_profile", {}), say("Hola, Ana")])
    agent = Agent(model, conn, seed(conn))
    reply = agent.send("hola")
    assert reply.text == "Hola, Ana"
    assert [t.name for t in reply.tool_calls] == ["get_user_profile"]
    assert len(agent.history) == 4
    assert agent.history[2]["results"][0][1]["name"] == "Ana"


def test_agent_saves_workout_to_database(conn: sqlite3.Connection) -> None:
    user_id = seed(conn)
    sets = [{"exercise_name": "Sentadilla goblet", "reps": 10, "weight_kg": 20}] * 3
    model = FakeModel(
        [
            call("search_exercises", {"muscle_group": "piernas"}),
            call("log_workout", {"sets": sets, "performed_on": "2026-11-23"}),
            say("Anotado"),
        ]
    )
    Agent(model, conn, user_id).send("Hice 3x10 de sentadilla goblet con 20 kg")
    workouts = get_recent_workouts(conn, user_id)
    assert len(workouts) == 1
    assert workouts[0].total_sets == 3
    assert workouts[0].volume_kg == 600.0


def test_tool_error_goes_back_to_the_model_and_saves_nothing(conn: sqlite3.Connection) -> None:
    user_id = seed(conn)
    incomplete = [{"exercise_name": "Sentadilla goblet", "weight_kg": 20}]  # sin reps
    model = FakeModel(
        [call("log_workout", {"sets": incomplete}), say("¿Cuántas repeticiones hiciste?")]
    )
    agent = Agent(model, conn, user_id)
    reply = agent.send("Hice 3 series de sentadilla goblet con 20 kg")
    assert "error" in agent.history[2]["results"][0][1]
    assert reply.text == "¿Cuántas repeticiones hiciste?"
    assert get_recent_workouts(conn, user_id) == []


def test_history_is_kept_between_messages(conn: sqlite3.Connection) -> None:
    model = FakeModel([say("¿Cuántas repeticiones?"), say("Anotado")])
    agent = Agent(model, conn, seed(conn))
    agent.send("Hice sentadillas")
    agent.send("10 repeticiones")
    assert model.history_sizes == [1, 3]


def test_loop_stops_at_max_steps(conn: sqlite3.Connection) -> None:
    model = FakeModel([call("get_user_profile", {})] * 10)
    agent = Agent(model, conn, seed(conn), max_steps=3)
    reply = agent.send("hola")
    assert "no pude" in reply.text.lower()
    assert len(model.history_sizes) == 3

class BrokenModel(FakeModel):
    def generate(self, history: list[Any]) -> ModelReply:
        raise RuntimeError("503")


def test_history_is_rolled_back_when_the_model_fails(conn: sqlite3.Connection) -> None:
    agent = Agent(BrokenModel([]), conn, seed(conn))
    with pytest.raises(RuntimeError):
        agent.send("hola")
    assert agent.history == []
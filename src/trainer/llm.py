from google.genai import types
from src.trainer.tools import ToolSpec

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
from __future__ import annotations

import json

from openai import OpenAI

from .config import Settings


RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "supplier_evaluation",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["supplier_name", "criteria", "risks", "overall_summary"],
            "properties": {
                "supplier_name": {"type": "string"},
                "criteria": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["criterion_id", "score", "max_score", "justification", "evidence"],
                        "properties": {
                            "criterion_id": {"type": "integer"},
                            "score": {"type": "number"},
                            "max_score": {"type": "number"},
                            "justification": {"type": "string"},
                            "evidence": {"type": "string"},
                        },
                    },
                },
                "risks": {"type": "array", "items": {"type": "string"}},
                "overall_summary": {"type": "string"},
            },
        },
    },
}


class OpenAIEvaluator:
    def __init__(self, settings: Settings):
        if not settings.openai_api_key:
            raise ValueError("No API key is available. Enter your OpenAI API key in the sidebar.")
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.llm_model

    def evaluate(self, prompt: str) -> dict[str, object]:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You evaluate supplier proposals and return only valid structured JSON."},
                    {"role": "user", "content": prompt},
                ],
                response_format=RESPONSE_FORMAT,
                temperature=0,
            )
            content = response.choices[0].message.content
            if not content:
                raise ValueError("The LLM returned an empty response.")
            return json.loads(content)
        except Exception as exc:
            raise RuntimeError("The LLM evaluation request failed. Check the model configuration and try again.") from exc

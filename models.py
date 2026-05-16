import json
import re

from pydantic import BaseModel, field_validator


class TutorialStep(BaseModel):
    step_number: int
    title: str
    description: str
    action: str
    anchor: str
    relative_position: str
    recovery_hint: str
    recovery_anchor: str

    @field_validator("recovery_hint")
    @classmethod
    def truncate_recovery_hint(cls, v: str) -> str:
        words = v.split()
        return " ".join(words[:15]) if len(words) > 15 else v


class CoordinateResult(BaseModel):
    x: float
    y: float
    width: float = 0.0
    height: float = 0.0
    confidence: str
    note: str = ""


def parse_steps(raw: str) -> list[TutorialStep]:
    # Strip markdown fences
    cleaned = re.sub(r"```[a-z]*\n?", "", raw).strip()

    # Find first JSON array
    match = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if not match:
        raise ValueError("No JSON array found in input")

    data = json.loads(match.group())

    steps: list[TutorialStep] = []
    for item in data:
        try:
            steps.append(TutorialStep(**item))
        except Exception as e:
            print(f"WARNING: Skipping invalid step {item.get('step_number', '?')}: {e}")

    if not steps:
        raise ValueError("Zero valid steps parsed")

    return steps

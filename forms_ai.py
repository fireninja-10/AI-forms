from __future__ import annotations

import json
from dataclasses import dataclass

from openai import OpenAI


@dataclass
class FormQuestion:
    title: str
    kind: str
    required: bool
    options: list[str]


def build_bulk_prompt(questions: list[FormQuestion], user_context: str) -> str:
    lines = [
        "Tu dois preparer des reponses pour un Google Form.",
        "Retourne uniquement un JSON valide sous la forme:",
        '{"answers":[{"index":1,"answer":"..."},{"index":2,"answer":["...","..."]}]}',
        "Utilise une chaine pour une question simple et un tableau pour des cases a cocher.",
        "Si une information manque, fais une reponse raisonnable et concise.",
        "",
        "Contexte utilisateur:",
        user_context or "Aucun contexte fourni.",
        "",
        "Questions:",
    ]

    for index, question in enumerate(questions, start=1):
        lines.append(
            json.dumps(
                {
                    "index": index,
                    "title": question.title,
                    "kind": question.kind,
                    "required": question.required,
                    "options": question.options,
                },
                ensure_ascii=True,
            )
        )

    return "\n".join(lines)


def build_single_question_prompt(question: FormQuestion, user_context: str) -> str:
    return "\n".join(
        [
            "Tu dois repondre a une seule question de Google Form.",
            "Retourne uniquement un JSON valide sous la forme:",
            '{"answer":"..."}',
            'ou {"answer":["...", "..."]} pour une question a cases a cocher.',
            "Sois concis et choisis des options existantes quand une liste est fournie.",
            "",
            "Contexte utilisateur:",
            user_context or "Aucun contexte fourni.",
            "",
            "Question:",
            json.dumps(
                {
                    "title": question.title,
                    "kind": question.kind,
                    "required": question.required,
                    "options": question.options,
                },
                ensure_ascii=True,
            ),
        ]
    )


def generate_bulk_answers(
    client: OpenAI,
    model: str,
    questions: list[FormQuestion],
    user_context: str,
) -> dict[int, str | list[str]]:
    response = client.responses.create(
        model=model,
        input=build_bulk_prompt(questions, user_context),
    )
    raw_text = response.output_text.strip()
    data = json.loads(raw_text)
    answers: dict[int, str | list[str]] = {}
    for item in data.get("answers", []):
        index = int(item["index"])
        answers[index] = item["answer"]
    return answers


def generate_single_answer(
    client: OpenAI,
    model: str,
    question: FormQuestion,
    user_context: str,
) -> str | list[str]:
    response = client.responses.create(
        model=model,
        input=build_single_question_prompt(question, user_context),
    )
    raw_text = response.output_text.strip()
    data = json.loads(raw_text)
    return data["answer"]

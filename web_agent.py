from __future__ import annotations

import os

from dotenv import load_dotenv
from flask import Flask
from flask import jsonify
from flask import render_template
from flask import request
from openai import OpenAI

from forms_ai import FormQuestion
from forms_ai import generate_single_answer


load_dotenv()

app = Flask(__name__)


def get_client() -> tuple[OpenAI, str, str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY manquant. Configure le fichier .env.")

    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    system_prompt = os.getenv(
        "OPENAI_SYSTEM_PROMPT",
        "Tu es un agent IA utile, clair et efficace.",
    )
    return OpenAI(api_key=api_key), model, system_prompt


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@app.get("/")
def index() -> str:
    return render_template("index.html")


@app.post("/api/chat")
def chat():
    payload = request.get_json(silent=True) or {}
    message = str(payload.get("message", "")).strip()
    history = payload.get("history", [])

    if not message:
        return jsonify({"error": "Message vide."}), 400

    try:
        client, model, system_prompt = get_client()
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 500

    messages = [{"role": "system", "content": system_prompt}]
    for item in history:
        role = item.get("role")
        content = item.get("content")
        if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
            messages.append({"role": role, "content": content.strip()})

    messages.append({"role": "user", "content": message})

    try:
        response = client.responses.create(model=model, input=messages)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Erreur API : {exc}"}), 500

    return jsonify({"reply": response.output_text.strip()})


@app.route("/api/forms/answer", methods=["POST", "OPTIONS"])
def answer_form_question():
    if request.method == "OPTIONS":
        return ("", 204)

    payload = request.get_json(silent=True) or {}
    question_payload = payload.get("question") or {}
    context = str(payload.get("context", "")).strip()

    title = str(question_payload.get("title", "")).strip()
    kind = str(question_payload.get("kind", "unknown")).strip() or "unknown"
    required = bool(question_payload.get("required", False))
    raw_options = question_payload.get("options", [])
    options = [str(item).strip() for item in raw_options if str(item).strip()]

    if not title:
        return jsonify({"error": "Question introuvable."}), 400

    try:
        client, model, _system_prompt = get_client()
        answer = generate_single_answer(
            client,
            model,
            FormQuestion(
                title=title,
                kind=kind,
                required=required,
                options=options,
            ),
            context,
        )
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Erreur API : {exc}"}), 500

    return jsonify({"answer": answer})


@app.get("/api/health")
def health():
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)

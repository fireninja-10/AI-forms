from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI


def build_messages(system_prompt: str, history: list[dict[str, str]]) -> list[dict[str, str]]:
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    return messages


def ask_model(client: OpenAI, model: str, system_prompt: str, history: list[dict[str, str]]) -> str:
    response = client.responses.create(
        model=model,
        input=build_messages(system_prompt, history),
    )
    return response.output_text.strip()


def print_help() -> None:
    print("Commandes disponibles :")
    print("  /reset           Réinitialiser la conversation")
    print("  /system <texte>  Changer le prompt système")
    print("  /quit            Quitter")


def main() -> None:
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY manquant. Configure le fichier .env avant de lancer l'agent.")

    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    system_prompt = os.getenv(
        "OPENAI_SYSTEM_PROMPT",
        "Tu es un agent IA utile, clair et efficace.",
    )

    client = OpenAI(api_key=api_key)
    history: list[dict[str, str]] = []

    print(f"Agent IA prêt avec le modèle {model}.")
    print("Tape /quit pour sortir, /reset pour vider l'historique, /help pour l'aide.")

    while True:
        try:
            user_input = input("\nTu > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAu revoir.")
            break

        if not user_input:
            continue

        if user_input == "/quit":
            print("Au revoir.")
            break

        if user_input == "/help":
            print_help()
            continue

        if user_input == "/reset":
            history.clear()
            print("Historique réinitialisé.")
            continue

        if user_input.startswith("/system "):
            system_prompt = user_input[len("/system ") :].strip()
            print("Prompt système mis à jour.")
            continue

        history.append({"role": "user", "content": user_input})

        try:
            answer = ask_model(client, model, system_prompt, history)
        except Exception as exc:  # noqa: BLE001
            history.pop()
            print(f"Erreur API : {exc}")
            continue

        history.append({"role": "assistant", "content": answer})
        print(f"Agent > {answer}")


if __name__ == "__main__":
    main()

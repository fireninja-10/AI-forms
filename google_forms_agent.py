from __future__ import annotations

import argparse
import json
import os
import re
import time
from dataclasses import dataclass

from dotenv import load_dotenv
from openai import OpenAI
from playwright.sync_api import Locator
from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


@dataclass
class Question:
    index: int
    title: str
    kind: str
    required: bool
    options: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Agent IA pour lire et remplir un Google Form.")
    parser.add_argument("url", help="URL du Google Form")
    parser.add_argument(
        "--context",
        default="",
        help="Contexte utilisateur pour aider l'IA a repondre aux questions",
    )
    parser.add_argument(
        "--fill",
        action="store_true",
        help="Pre-remplit le formulaire avec les reponses generees",
    )
    parser.add_argument(
        "--submit",
        action="store_true",
        help="Soumet le formulaire apres remplissage",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Lance le navigateur en mode headless",
    )
    return parser.parse_args()


def get_client() -> tuple[OpenAI, str]:
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY manquant. Configure le fichier .env avant de lancer le script.")
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    return OpenAI(api_key=api_key), model


def clean_text(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    value = value.removesuffix("*").strip()
    return value


def unique_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = clean_text(item)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def detect_kind(block: Locator) -> str:
    if block.locator("textarea").count() > 0:
        return "paragraph"
    if block.locator("input[type='text']").count() > 0:
        return "short_text"
    if block.locator("[role='radio']").count() > 0:
        return "multiple_choice"
    if block.locator("[role='checkbox']").count() > 0:
        return "checkboxes"
    if block.locator("[role='listbox']").count() > 0 or block.locator("[role='combobox']").count() > 0:
        return "dropdown"
    return "unknown"


def extract_options(block: Locator) -> list[str]:
    options: list[str] = []

    for selector in ("[role='radio']", "[role='checkbox']", "[role='option']"):
        for node in block.locator(selector).all():
            text = clean_text(node.inner_text())
            if text:
                options.append(text)

    for label in block.locator("label").all():
        text = clean_text(label.inner_text())
        if text:
            options.append(text)

    return unique_preserve_order(options)


def extract_questions(page: Page) -> list[Question]:
    page.wait_for_load_state("domcontentloaded")
    page.locator("div[role='listitem']").first.wait_for(timeout=15000)

    questions: list[Question] = []
    blocks = page.locator("div[role='listitem']").all()
    for index, block in enumerate(blocks, start=1):
        headings = [clean_text(value) for value in block.locator("[role='heading']").all_inner_texts()]
        title = next((value for value in headings if value), "")
        if not title:
            title = clean_text(block.inner_text().split("\n")[0])
        if not title:
            continue

        required = "*" in block.inner_text()
        kind = detect_kind(block)
        options = extract_options(block)

        questions.append(
            Question(
                index=index,
                title=title,
                kind=kind,
                required=required,
                options=options,
            )
        )

    return questions


def questions_to_prompt(questions: list[Question], user_context: str) -> str:
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

    for question in questions:
        lines.append(
            json.dumps(
                {
                    "index": question.index,
                    "title": question.title,
                    "kind": question.kind,
                    "required": question.required,
                    "options": question.options,
                },
                ensure_ascii=True,
            )
        )

    return "\n".join(lines)


def generate_answers(client: OpenAI, model: str, questions: list[Question], user_context: str) -> dict[int, str | list[str]]:
    response = client.responses.create(
        model=model,
        input=questions_to_prompt(questions, user_context),
    )
    raw_text = response.output_text.strip()
    data = json.loads(raw_text)

    answers: dict[int, str | list[str]] = {}
    for item in data.get("answers", []):
        index = int(item["index"])
        answers[index] = item["answer"]
    return answers


def print_plan(questions: list[Question], answers: dict[int, str | list[str]]) -> None:
    print("\nQuestions detectees et reponses proposees:\n")
    for question in questions:
        answer = answers.get(question.index, "")
        print(f"[{question.index}] {question.title}")
        print(f"    type: {question.kind}")
        if question.options:
            print(f"    options: {', '.join(question.options)}")
        print(f"    reponse: {answer}")
        print()


def click_option_by_text(block: Locator, option_text: str) -> bool:
    candidates = [
        block.get_by_text(option_text, exact=False).first,
        block.locator("label").get_by_text(option_text, exact=False).first,
        block.locator("[role='radio']").get_by_text(option_text, exact=False).first,
        block.locator("[role='checkbox']").get_by_text(option_text, exact=False).first,
    ]

    for candidate in candidates:
        if candidate.count() == 0:
            continue
        try:
            candidate.click(timeout=2000)
            return True
        except PlaywrightTimeoutError:
            continue
    return False


def fill_question(page: Page, block: Locator, question: Question, answer: str | list[str]) -> None:
    if question.kind == "paragraph":
        block.locator("textarea").first.fill(str(answer))
        return

    if question.kind == "short_text":
        block.locator("input[type='text']").first.fill(str(answer))
        return

    if question.kind == "multiple_choice":
        click_option_by_text(block, str(answer))
        return

    if question.kind == "checkboxes":
        values = answer if isinstance(answer, list) else [str(answer)]
        for value in values:
            click_option_by_text(block, value)
        return

    if question.kind == "dropdown":
        value = answer[0] if isinstance(answer, list) and answer else str(answer)
        combobox = block.locator("[role='listbox'], [role='combobox']").first
        combobox.click()
        page.get_by_text(str(value), exact=False).first.click(timeout=3000)


def fill_form(page: Page, questions: list[Question], answers: dict[int, str | list[str]]) -> None:
    blocks = page.locator("div[role='listitem']").all()
    by_index = {question.index: question for question in questions}

    for index, block in enumerate(blocks, start=1):
        question = by_index.get(index)
        if question is None or index not in answers:
            continue
        try:
            fill_question(page, block, question, answers[index])
        except Exception as exc:  # noqa: BLE001
            print(f"Impossible de remplir la question {index}: {exc}")


def submit_form(page: Page) -> None:
    for selector in ("div[role='button']:has-text('Submit')", "div[role='button']:has-text('Envoyer')"):
        button = page.locator(selector).first
        if button.count() == 0:
            continue
        button.click()
        return
    raise RuntimeError("Bouton de soumission introuvable.")


def main() -> None:
    args = parse_args()
    client, model = get_client()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=args.headless)
        page = browser.new_page()
        page.goto(args.url, wait_until="domcontentloaded")

        print("Chargement du formulaire...")
        time.sleep(2)

        questions = extract_questions(page)
        if not questions:
            raise SystemExit("Aucune question detectee. Le formulaire demande peut-etre une connexion Google.")

        answers = generate_answers(client, model, questions, args.context)
        print_plan(questions, answers)

        if args.fill:
            fill_form(page, questions, answers)
            print("Le formulaire a ete pre-rempli dans le navigateur.")

        if args.submit:
            if not args.fill:
                raise SystemExit("--submit exige aussi --fill.")
            submit_form(page)
            print("Le formulaire a ete soumis.")
        elif args.fill and not args.headless:
            print("Le navigateur reste ouvert pour verification manuelle. Ferme-le quand tu as termine.")
            page.wait_for_timeout(120000)

        browser.close()


if __name__ == "__main__":
    main()

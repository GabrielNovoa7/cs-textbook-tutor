import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


ENV_PATH = Path(__file__).resolve().parent / ".env"

load_dotenv(ENV_PATH)

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise RuntimeError(
        "OPENAI_API_KEY was not found in backend/.env"
    )

client = OpenAI(api_key=api_key)


def generate_tutor_response(
    question,
    passages,
    chat_history=None
):
    context_sections = []

    for passage in passages:
        context_sections.append(
            f"""
PAGE {passage["page_number"]}

{passage["text"]}
"""
        )

    textbook_context = "\n\n---\n\n".join(context_sections)

    history_sections = []

    if chat_history:
        for message in chat_history[-10:]:
            role = message["role"].upper()

            history_sections.append(
                f"{role}: {message['content']}"
            )

    conversation_history = "\n\n".join(
        history_sections
    )

    response = client.responses.create(
        model="gpt-6-luna",

        instructions="""
You are an interactive computer science textbook tutor.

Your goal is to help the student actually learn the material,
not simply give them answers.

Follow these rules:

1. Base your explanation primarily on the supplied textbook context.
2. Ignore retrieved passages that are irrelevant to the student's question.
3. Never claim that the textbook says something unless the supplied context supports it.
4. Explain concepts clearly using beginner-friendly language.
5. Use programming examples when they would help.
6. Mention relevant textbook page numbers when possible.
7. If the textbook context is insufficient, clearly say so.
8. For practice problems, guide the student before giving the complete answer unless they explicitly ask for it.
9. Encourage understanding instead of memorization.
""",

        input=f"""
PREVIOUS CONVERSATION:

{conversation_history}


CURRENT STUDENT QUESTION:

{question}


RETRIEVED TEXTBOOK CONTEXT:

{textbook_context}
"""
    )

    return response.output_text
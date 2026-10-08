import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from fastapi import HTTPException
from backend.config import BACKEND_DIR

ENV_PATH = BACKEND_DIR / ".env"

if not os.getenv('CSTUTOR_DESKTOP_MODE'):
    load_dotenv(ENV_PATH)

class ConfiguredClient:
    def get(self):
        key = os.getenv('OPENAI_API_KEY')
        if not key:
            raise HTTPException(409, 'Add your OpenAI API key in Desktop Settings to use AI features.')
        return OpenAI(api_key=key)

    @property
    def responses(self):
        return self.get().responses

    def with_options(self, **options):
        return self.get().with_options(**options)

client = ConfiguredClient()


def generate_tutor_response(question, passages, chat_history=None):
    context_sections = []

    for passage in passages:
        context_sections.append(f"""
PAGE {passage["page_number"]}

{passage["text"]}
""")

    textbook_context = "\n\n---\n\n".join(context_sections)

    history_sections = []

    if chat_history:
        for message in chat_history[-10:]:
            role = message["role"].upper()

            history_sections.append(f"{role}: {message['content']}")

    conversation_history = "\n\n".join(history_sections)

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
""",
    )

    return response.output_text

from typing import Dict, List
from google import genai
from google.genai import types
from google.genai.errors import APIError
from app.config.settings import Settings
from app.prompts.qa_prompt import SYSTEM_PROMPT
from app.utils.logging_config import setup_logger

logger = setup_logger(__name__)

class ServiceError(Exception):
    pass

class GeminiService:
    def __init__(self, settings: Settings) -> None:
        self._model = settings.model
        self._temperature = settings.temperature
        try:
            self._client = genai.Client(api_key=settings.api_key)
        except Exception as exc:
            raise ServiceError("Unable to initialize AI client.") from exc

    def generate_answer(self, conversation_history: List[Dict[str, str]]) -> str:
        if not conversation_history:
            raise ServiceError("Conversation history cannot be empty.")

        contents = []
        for msg in conversation_history:
            role = "user" if msg.get("role") == "user" else "model"
            text = msg.get("content", "").strip()
            if text:
                contents.append(types.Content(role=role, parts=[types.Part.from_text(text=text)]))

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=self._temperature,
        )

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=contents,
                config=config,
            )
            return response.text or "I was unable to generate a response."
        except APIError:
            raise ServiceError("The AI service encountered an error processing your request.")
        except Exception:
            raise ServiceError("An unexpected error occurred.")
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

class ConfigurationError(Exception):
    pass

@dataclass(frozen=True)
class Settings:
    api_key: str
    model: str
    temperature: float

    @classmethod
    def load(cls) -> "Settings":
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise ConfigurationError("Missing GEMINI_API_KEY in .env file.")
        
        model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()
        
        try:
            temperature = float(os.getenv("TEMPERATURE", "0.2").strip())
        except ValueError:
            temperature = 0.2

        return cls(api_key=api_key, model=model, temperature=temperature)
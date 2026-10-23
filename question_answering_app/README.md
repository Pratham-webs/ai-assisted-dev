# AI Question & Answering System

A modular, production-ready Question & Answering conversational application powered by Google AI Studio Gemini models and Streamlit.

## Features
- **Multi-turn Conversation Memory:** Maintains context for follow-up questions using Streamlit session state.
- **Dynamic System Prompting:** Ensures accurate, factual, and concise responses.
- **Secure Error Handling:** Encapsulates API failures to prevent credential or internal logic leakage to the UI.
- **Official SDK Integration:** Uses the modern `google-genai` Python library.
- **Clean Architecture:** Strict separation of UI, API services, configuration, and prompts.

## Prerequisites
- Python 3.10 or higher
- A [Google AI Studio API Key](https://aistudio.google.com/app/apikey)

## Project Structure
```text
question_answering_app/
├── app/
│   ├── config/settings.py         # Environment and configuration loading
│   ├── prompts/qa_prompt.py       # System instructions for the AI
│   ├── services/gemini_service.py # Google GenAI API integration
│   ├── utils/logging_config.py    # Application logging setup
│   └── main.py                    # Streamlit frontend
├── tests/                         # Pytest unit tests
├── .env                           # API keys (ignored by git)
├── .env.example                   # Template for environment variables
├── requirements.txt               # Project dependencies
└── README.md                      # Documentation
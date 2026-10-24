import streamlit as st
from app.config.settings import ConfigurationError, Settings
from app.services.gemini_service import GeminiService, ServiceError

st.set_page_config(page_title="AI Q&A System", page_icon="💬", layout="centered")


@st.cache_resource(show_spinner=False)
def get_service():
    return GeminiService(Settings.load())


def main():
    if "messages" not in st.session_state:
        st.session_state.messages = []

    st.title("AI Question & Answering System")

    try:
        settings = Settings.load()
        service = get_service()
    except ConfigurationError as e:
        st.error(f"Configuration Error: {e}")
        st.stop()
    except ServiceError as e:
        st.error(f"Service Error: {e}")
        st.stop()

    with st.sidebar:
        st.header("Settings")
        st.markdown(f"**Model:** `{settings.model}`")
        if st.button("Clear Conversation"):
            st.session_state.messages = []
            st.rerun()

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask a question..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Think"):
                try:
                    response = service.generate_answer(st.session_state.messages)
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except ServiceError as err:
                    st.error(str(err))


if __name__ == "__main__":
    main()
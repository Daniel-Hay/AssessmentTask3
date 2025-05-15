import whisper
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
import streamlit as st
import os
import tempfile

# --- Simple user database ---
USERS = {
    "user1": "pass123",
    "admin": "admin123"
}

def login():
    st.title("Login Page")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username in USERS and USERS[username] == password:
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.success(f"Welcome {username}!")
            st.rerun()
        else:
            st.error("Invalid username or password")

def main_menu():
    st.title(f"Welcome {st.session_state['username']}!")
    uploaded_file = st.file_uploader("Upload an audio file", type=["mp3", "wav", "ogg", "flac"])

    if uploaded_file:
        st.audio(uploaded_file)
        st.session_state["audio_file"] = uploaded_file

        if st.button("Transcribe"):
            st.session_state["page"] = "transcribe"
            st.rerun()

    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

def transcribe_page():
    st.title("Transcription Result")

    uploaded_file = st.session_state.get("audio_file", None)
    if uploaded_file:
        st.success(f"Transcribing: {uploaded_file.name}")

        # Save uploaded file to a temporary file with correct extension
        file_extension = uploaded_file.name.split(".")[-1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as tmp_file:
            tmp_file.write(uploaded_file.read())
            temp_audio_path = tmp_file.name

        # Load whisper model
        model = whisper.load_model("base")

        # Load audio from saved file
        audio = whisper.load_audio(temp_audio_path)
        audio = whisper.pad_or_trim(audio)
        mel = whisper.log_mel_spectrogram(audio).to(model.device)

        # Decode
        options = whisper.DecodingOptions()
        result = whisper.decode(model, mel, options)

        # Output transcription
        st.info("🔊 Transcription:")
        st.write(result.text)

        # Clean up
        os.remove(temp_audio_path)

    else:
        st.warning("No audio file found. Please upload and transcribe again.")

    if st.button("Back to Menu"):
        st.session_state["page"] = "main"
        st.rerun()

def main():
    # Initialize session state
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    if "page" not in st.session_state:
        st.session_state["page"] = "main"
    if "username" not in st.session_state:
        st.session_state["username"] = ""

    if not st.session_state["logged_in"]:
        login()
    else:
        if st.session_state["page"] == "main":
            main_menu()
        elif st.session_state["page"] == "transcribe":
            transcribe_page()

if __name__ == "__main__":
    main()
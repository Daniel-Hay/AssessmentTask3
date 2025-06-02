import whisper
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
import streamlit as st
import sqlite3
import os
import tempfile
import hashlib

# --- User Database Using sqlite ---
conn = sqlite3.connect('data.db')
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS userstable (username TEXT, password TEXT)')
conn.commit()

def add_user(username, password):
    hashed = hash_password(password)
    c.execute('INSERT INTO userstable(username, password) VALUES (?, ?)', (username, hashed))
    conn.commit()

def login_user(username, password):
    hashed = hash_password(password)
    c.execute('SELECT * FROM userstable WHERE username=? AND password=?', (username, hashed))
    return c.fetchone()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register():
    st.title("Register")
    new_username = st.text_input("New Username")
    new_password = st.text_input("New Password", type="password")
    if st.button("Register"):
        # Check if username already exists
        c.execute('SELECT * FROM userstable WHERE username=?', (new_username,))
        if c.fetchone():
            st.error("Username already exists. Please choose another.")
        elif not new_username or not new_password:
            st.error("Username and password cannot be empty.")
        else:
            add_user(new_username, new_password)
            st.success("Registration successful! You can now log in.")

def login():
    st.title("Login Page")
    menu = ["Login", "Register"]
    choice = st.sidebar.selectbox("Menu", menu)
    if choice == "Login":
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if login_user(username, password):
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.success(f"Welcome {username}!")
                st.rerun()
            else:
                st.error("Invalid username or password")
    else:
        register()

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
        st.info("Transcription:")
        st.write(result.text)

        # Summarise the transcription
        st.markdown("### Summarise Transcription")
        num_sentences = st.slider("Select number of sentences for summary:", min_value=1, max_value=10, value=3)
        if st.button("Summarise Transcription"):
            parser = PlaintextParser.from_string(result.text, Tokenizer("english"))
            summarizer = LsaSummarizer()
            summary_sentences = summarizer(parser.document, num_sentences)
            summary = " ".join(str(sentence) for sentence in summary_sentences)
            st.info("Summary:")
            st.write(summary)

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
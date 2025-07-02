import whisper
import streamlit as st
import sqlite3
import os
import tempfile
import hashlib
import numpy as np
from summa.summarizer import summarize

# Cache model loading, improving performance
@st.cache_resource
def get_whisper_model():
    return whisper.load_model("tiny")

conn = sqlite3.connect('data.db')
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS userstable (username TEXT, password TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS summaries (username TEXT, title TEXT, summary TEXT, tags TEXT, date TEXT)')
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
    st.title("Shout - Audio Transcription Service")
    menu = ["Login", "Register"]
    choice = st.pills("Select action", menu, default="Login")
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
    
    if st.button("View Past Summaries"):
        st.session_state["page"] = "review"
        st.rerun()

    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

def transcribe_page():
    st.title("Transcription Result")

    uploaded_file = st.session_state.get("audio_file", None)
    temp_audio_path = st.session_state.get("temp_audio_path", None)
    result = st.session_state.get("result", None)

    # Only create temp file and transcribe if not already done
    if uploaded_file and (not temp_audio_path or not os.path.exists(temp_audio_path) or not result):
        file_extension = uploaded_file.name.split(".")[-1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as tmp_file:
            uploaded_file.seek(0)
            tmp_file.write(uploaded_file.read())
            temp_audio_path = tmp_file.name
            st.session_state["temp_audio_path"] = temp_audio_path

        model = get_whisper_model()
        try:
            audio = whisper.load_audio(temp_audio_path)
            if audio is None or (isinstance(audio, np.ndarray) and audio.size == 0):
                st.error("The uploaded audio file is empty or invalid. Please upload a valid audio file.")
                os.remove(temp_audio_path)
                st.session_state["temp_audio_path"] = None
                return
            result = model.transcribe(temp_audio_path)
            st.session_state["result"] = result
        except Exception as e:
            st.error(f"Failed to transcribe audio: {e}")
            if temp_audio_path and os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)
            st.session_state["temp_audio_path"] = None
            return

        # Show transcription progress only once
        if "transcription_shown" not in st.session_state:
            st.success(f"Transcribing: {uploaded_file.name}... Please wait.")
            st.write("Audio shape:", audio.shape)
            st.write("First 10 samples:", audio[:10])
            st.session_state["transcription_shown"] = True
            st.rerun()

    result = st.session_state.get("result", None)
    temp_audio_path = st.session_state.get("temp_audio_path", None)

    if result:
        st.write(result["text"])

        # Count sentence length 
        sentence_count = result["text"].count('.') + result["text"].count('!') + result["text"].count('?')
        if sentence_count <= 1:
            sentence_count = 2
        st.write("Sentence length: ", sentence_count)

        # Summarise the transcription
        st.markdown("### Summarise Transcription")
        if "show_summary" not in st.session_state:
            st.session_state["show_summary"] = False
        if not st.session_state["show_summary"]:
            num_sentences = st.slider("Select number of sentences for summary:", min_value=1, max_value=sentence_count, value=min(3, sentence_count))
            if st.button("Summarise Transcription"):
                try:
                    ratio = min(1.0, num_sentences / sentence_count)
                    summary = summarize(result["text"], ratio=ratio)
                    summary = summary if summary else "Summary could not be generated. Text may be too short."
                except Exception as e:
                    summary = f"Error generating summary: {e}"
                st.session_state["summary"] = summary
                st.session_state["show_summary"] = True
                st.session_state["transcription_shown"] = False
                st.rerun()
        else:
            st.info("📝 Summary:")
            summary_text = st.session_state.get("summary", "")
            st.write(summary_text)
            if st.button("Save Summary"):
                st.session_state["pending_save"] = True
                st.session_state["pending_summary"] = summary_text
                st.rerun()
        
        if st.session_state.get("pending_save", False):
            st.header("Save Your Summary")
            title = st.text_input("Title for your summary")
            tags = st.text_input("Tags (comma-separated)")
            if st.button("Submit"):
                save_summary(st.session_state["username"], title, st.session_state["pending_summary"], tags)
                st.success("Summary saved successfully!")
                st.session_state["pending_save"] = False
                st.session_state["pending_summary"] = ""
    else:
        st.warning("No audio file found. Please upload and transcribe again.")

    # Only delete the temp file when leaving the page
    if st.button("Back to Menu"):
        st.session_state["page"] = "main"
        st.session_state["show_summary"] = False
        st.session_state["transcription_shown"] = False
        temp_audio_path = st.session_state.get("temp_audio_path")
        if temp_audio_path and os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
        st.session_state["temp_audio_path"] = None
        st.session_state["result"] = None
        st.session_state["audio_file"] = None
        st.rerun()

def save_summary(username, title, summary, tags):
    c.execute('INSERT INTO summaries (username, title, summary, tags, date) VALUES (?, ?, ?, ?, datetime("now"))', (username, title, summary, tags))
    conn.commit()

def review_summaries():
    st.title("Your Saved Summaries")
    c.execute('SELECT title, summary, tags, date FROM summaries WHERE username=? ORDER BY date DESC', (st.session_state["username"],))
    rows = c.fetchall()
    if not rows:
        st.info("You have no saved summaries.")
    else:
        for title, summary, tags, date in rows:
            st.subheader(title if title else "(No Title)")
            st.caption(f"Tags: {tags if tags else 'None'} | Saved: {date}")
            st.write(summary)
            delete_key = f"delete_{title}_{date}"
            if st.button("Delete Summary", key=delete_key):
                delete_summary(st.session_state["username"], title, date)
                st.success(f"Summary '{title}' deleted successfully!")
                st.rerun()
            st.markdown("---")
    if st.button("Back to Menu"):
        st.session_state["page"] = "main"
        st.rerun()

def delete_summary(username, title, date):
    c.execute('DELETE FROM summaries WHERE username=? AND title=? AND date=?', (username, title, date))
    conn.commit()

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
        elif st.session_state["page"] == "review":
            review_summaries()

if __name__ == "__main__":
    main()
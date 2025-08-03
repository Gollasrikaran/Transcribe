import streamlit as st
import requests
import os
from dotenv import load_dotenv

# Load API keys
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env.local'))

ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Set page config
st.set_page_config(page_title="Auto Prescribe", layout="wide", page_icon="💊")

# Add branding
col1, col2 = st.columns([0.15, 0.85])
with col1:
    st.image("logo.png", width=80)
with col2:
    st.markdown(
        "<h1 style='margin-bottom:0;'>Auto Prescribe</h1><p style='color:gray;'>Smart medical transcription & AI-powered summaries</p>",
        unsafe_allow_html=True
    )

st.markdown("---")

# Sidebar
with st.sidebar:
    st.title("📂 Navigation")
    page = st.radio("Choose a page", ["🎙️ Transcription", "📄 Summary", "💡 Key Insights"])
    

# Initialize session state
for key in ['transcript', 'summary', 'key_actions']:
    st.session_state.setdefault(key, "")

# --- Page 1: Transcription ---
if page.startswith("🎙️"):
    st.subheader("Upload and Transcribe Audio")
    st.info("Supported formats: MP3, WAV, M4A, MP4", icon="📎")

    audio_file = st.file_uploader("Choose an audio file", type=["wav", "mp3", "m4a", "mp4"])

    if audio_file and st.button("🚀 Start Transcription"):
        with st.spinner("Uploading and transcribing..."):
            headers = {"authorization": ASSEMBLYAI_API_KEY}

            # Upload audio
            upload_res = requests.post("https://api.assemblyai.com/v2/upload", headers=headers, data=audio_file)
            if upload_res.status_code != 200:
                st.error("Audio upload failed. Please check your API key or network.")
            else:
                upload_url = upload_res.json()["upload_url"]

                # Request transcription
                transcript_res = requests.post(
                    "https://api.assemblyai.com/v2/transcript",
                    headers={"authorization": ASSEMBLYAI_API_KEY, "content-type": "application/json"},
                    json={"audio_url": upload_url}
                )

                if transcript_res.status_code != 200:
                    st.error("Failed to request transcription.")
                else:
                    transcript_id = transcript_res.json()["id"]
                    status = "queued"

                    # Poll until done
                    while status not in ["completed", "error"]:
                        poll_res = requests.get(
                            f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
                            headers=headers
                        )
                        status = poll_res.json()["status"]
                        if status == "completed":
                            st.session_state['transcript'] = poll_res.json()["text"]
                            st.success("✅ Transcription completed!")
                        elif status == "error":
                            st.error("Transcription failed.")
                        else:
                            st.info(f"Status: {status}... Waiting...")

    if st.session_state['transcript']:
        st.subheader("📝 Transcript")
        st.text_area("Transcript", st.session_state['transcript'], height=300)
        st.download_button(
            label="⬇️ Download Transcript",
            data=st.session_state['transcript'],
            file_name="transcript.txt",
            mime="text/plain"
        )

# --- Page 2: Summary ---
elif page.startswith("📄"):
    st.subheader("Summarize the Transcript")
    if not st.session_state['transcript']:
        st.warning("Please transcribe an audio file first.")
    else:
        if st.button("🧠 Generate Summary"):
            with st.spinner("Generating summary using Gemini..."):
                headers = {"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY}
                prompt = f"""
You are a medical transcription summarizer.
Given the following conversation transcript between a doctor and a patient, do the following:
1. Provide a concise summary of the discussion.
2. List the key actions or decisions discussed.
Important: Do NOT use markdown. Use plain text only. Structure as:
Summary: ...
Key Actions: ...
Transcript:
{st.session_state['transcript']}
"""
                url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
                data = {
                    "contents": [{"parts": [{"text": prompt}]}],
                }
                res = requests.post(url, headers=headers, json=data)

                if res.status_code == 200:
                    try:
                        gemini_text = res.json()["candidates"][0]["content"]["parts"][0]["text"]
                        st.session_state['summary'] = gemini_text
                        st.success("✅ Summary generated!")
                    except Exception as e:
                        st.error(f"Response parsing failed: {e}")
                else:
                    st.error(f"Gemini API error: {res.text}")

        if st.session_state['summary']:
            summary_text = st.session_state['summary']
            if "Key Actions:" in summary_text:
                summary_text = summary_text.split("Key Actions:", 1)[0]
            if summary_text.lower().strip().startswith("summary:"):
                summary_text = summary_text[len("summary:"):].strip()

            st.subheader("📋 Summary")
            st.text_area("", summary_text, height=300)
            st.download_button(
                label="⬇️ Download Summary",
                data=summary_text,
                file_name="summary.txt",
                mime="text/plain"
            )

# --- Page 3: Key Insights ---
elif page.startswith("💡"):
    st.subheader("Key Insights from Summary")
    if st.session_state['summary']:
        summary = st.session_state['summary']
        key_actions = ""
        if "Key Actions:" in summary:
            key_actions = summary.split("Key Actions:", 1)[-1].strip()
        # Format key actions as bullet points if not already formatted
        display_key_actions = key_actions
        if key_actions and not ("- " in key_actions or "\n" in key_actions):
            # Split by period or semicolon, remove empty
            points = [pt.strip() for pt in key_actions.replace(';', '.').split('.') if pt.strip()]
            if len(points) > 1:
                display_key_actions = '\n'.join([f"- {pt}" for pt in points])
        st.text_area("Key Actions", display_key_actions or "No key actions found.", height=200)
        st.download_button(
            label="Download Key Insights",
            data=display_key_actions or "No key actions found.",
            file_name="key_insights.txt",
            mime="text/plain"
        )
    else:
        st.warning("Please generate a summary first.")

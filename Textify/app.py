import streamlit as st
import yt_dlp
from pydub import AudioSegment
import os
import shutil
import subprocess

def set_button_style():
    st.markdown("""
        <style>
        .nav-button {
            display: block;
            width: 100%;
            margin-bottom: 10px;
            text-align: center;
            padding: 10px 20px;
            border: none;
            background-color: #f0f2f6;
            color: #333;
            font-size: 16px;
            border-radius: 8px;
            cursor: pointer;
        }
        .nav-button:hover {
            background-color: #e0e3ea;
        }
        </style>
    """, unsafe_allow_html=True)


def check_dependencies():
    if not shutil.which("yt-dlp"):
        raise FileNotFoundError("yt-dlp is not installed or not in PATH. Install it using 'pip install yt-dlp'.")

    if not shutil.which("ffmpeg"):
        raise FileNotFoundError(
            "ffmpeg is not installed or not in PATH. Download it from https://ffmpeg.org/download.html.")

    if not shutil.which("whisper"):
        raise FileNotFoundError(
            "Whisper CLI is not installed or not in PATH. Install it using 'pip install openai-whisper'.")


def download_youtube_audio(url, save_path='.', filename='audio'):
    try:
        check_dependencies()
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(save_path, 'temp_audio.%(ext)s'),
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            temp_file = ydl.prepare_filename(info_dict)

        audio = AudioSegment.from_file(temp_file)
        mp3_path = os.path.join(save_path, f"{filename}.mp3")
        audio.export(mp3_path, format="mp3")
        os.remove(temp_file)
        return mp3_path
    except Exception as e:
        return str(e)


def transcribe_audio_with_whisper(audio_path, model_type):
    global status_text
    try:
        progress_bar = st.progress(0)
        status_text = st.empty()
        transcription_placeholder = st.empty()
        status_text.text("Starting transcription...")
        progress_bar.progress(0.1)
        command = f"whisper {audio_path} --model {model_type}"
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        while True:
            output = process.stderr.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                if "Detecting language" in output:
                    status_text.text("Detecting language...")
                    progress_bar.progress(0.3)
                elif "Transcribing" in output:
                    status_text.text("Transcribing audio...")
                    progress_bar.progress(0.6)
        base_filename = os.path.splitext(audio_path)[0]
        srt_path = f"{base_filename}.srt"
        txt_path = f"{base_filename}.txt"
        tsv_path = f"{base_filename}.tsv"
        if os.path.exists(txt_path):
            progress_bar.progress(0.8)
            status_text.text("Reading transcription...")
            with open(txt_path, 'r', encoding='utf-8') as file:
                final_transcription = file.read()
                transcription_placeholder.text_area("Transcription", final_transcription, height=300)
            progress_bar.progress(1.0)
            status_text.text("Complete!")
            return srt_path, txt_path, tsv_path
        else:
            status_text.text("Error: Transcription failed")
            return None, None, None

    except Exception as e:
        status_text.text(f"Error: {str(e)}")
        return None, None, None

def youtube_transcribe_page():
    st.title('Transcribe your YouTube video')

    url = st.text_input('Enter the YouTube URL')
    filename = st.text_input('Enter the desired filename (without extension)', 'audio')

    model_type = st.selectbox(
        'Select Whisper AI Model Type',
        ["base"]
    )

    if st.button('Download and Transcribe'):
        if url:
            try:
                with st.spinner('Downloading and converting...'):
                    save_path = '.'
                    audio_path = download_youtube_audio(url, save_path, filename)
                    if os.path.exists(audio_path):
                        st.success(f'Download completed! Audio saved to: {audio_path}')

                        with st.spinner('Transcribing with Whisper AI...'):
                            srt_path, txt_path, tsv_path = transcribe_audio_with_whisper(audio_path, model_type)
                            if srt_path and os.path.exists(srt_path):
                                st.success('Transcription completed!')

                                with open(srt_path, 'r') as file:
                                    srt_content = file.read()
                                with open(txt_path, 'r') as file:
                                    txt_content = file.read()
                                with open(tsv_path, 'r') as file:
                                    tsv_content = file.read()

                                st.download_button(label="Download SRT", data=srt_content, file_name=f"{filename}.srt")
                                st.download_button(label="Download TXT", data=txt_content, file_name=f"{filename}.txt")
                                st.download_button(label="Download TSV", data=tsv_content, file_name=f"{filename}.tsv")

                            else:
                                st.error(f'An error occurred during transcription: {srt_path}')
                    else:
                        st.error(f'An error occurred during download: {audio_path}')
            except FileNotFoundError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f'An unexpected error occurred: {str(e)}')
        else:
            st.warning('Please enter a valid YouTube URL')


def file_upload_page():
    st.title('Transcribe Audio/Video File')

    uploaded_file = st.file_uploader("Choose an audio/video file", type=['mp3', 'wav', 'mp4', 'avi', 'mov'])
    filename = st.text_input('Enter the desired filename (without extension)', 'transcription')

    model_type = st.selectbox(
        'Select Whisper AI Model Type',
        ["base"]
    )

    if uploaded_file is not None and st.button('Transcribe'):
        try:
            temp_path = f"temp_{uploaded_file.name}"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            with st.spinner('Transcribing with Whisper AI...'):
                srt_path, txt_path, tsv_path = transcribe_audio_with_whisper(temp_path, model_type)
                if srt_path and os.path.exists(srt_path):
                    st.success('Transcription completed!')
                    with open(srt_path, 'r') as file:
                        srt_content = file.read()
                    with open(txt_path, 'r') as file:
                        txt_content = file.read()
                    with open(tsv_path, 'r') as file:
                        tsv_content = file.read()
                    st.download_button(label="Download SRT", data=srt_content, file_name=f"{filename}.srt")
                    st.download_button(label="Download TXT", data=txt_content, file_name=f"{filename}.txt")
                    st.download_button(label="Download TSV", data=tsv_content, file_name=f"{filename}.tsv")
                    os.remove(temp_path)
                    os.remove(srt_path)
                    os.remove(txt_path)
                    os.remove(tsv_path)
                else:
                    st.error(f'An error occurred during transcription: {srt_path}')
        except Exception as e:
            st.error(f'An unexpected error occurred: {str(e)}')

def main():
    set_button_style()
    st.sidebar.title('Textify')
    selected_page = st.sidebar.radio(
        "by Noor Afaqi",
        ["🎥 YouTube Transcribe", "📁 File Transcribe"],
        index=0,
    )
    if selected_page == "🎥 YouTube Transcribe":
        youtube_transcribe_page()
    elif selected_page == "📁 File Transcribe":
        file_upload_page()

if __name__ == "__main__":
    main()

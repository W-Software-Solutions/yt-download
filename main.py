import streamlit as st
from yt_dlp import YoutubeDL
import math

st.set_page_config(page_title="YouTube Downloader", layout="centered")
st.title("📹 YouTube Downloader with Quality Selector + Progress Bar")

url = st.text_input("Enter YouTube video URL:")

def format_bytes(bytes):
    if bytes is None:
        return "N/A"
    mb = bytes / (1024 * 1024)
    return f"{mb:.2f} MiB"

def format_eta(seconds):
    if seconds is None:
        return "N/A"
    minutes = math.floor(seconds / 60)
    seconds = int(seconds % 60)
    return f"{minutes}:{seconds:02}"

if url:
    with st.spinner("Fetching video info..."):
        try:
            with YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                formats = info.get('formats', [])
        except Exception as e:
            st.error(f"Error: {e}")
            formats = []

    if formats:
        st.subheader(f"🎞️ {info.get('title')}")
        st.video(info.get('url'))

        video_formats = []
        audio_formats = []

        for f in formats:
            if f.get('vcodec') != 'none' and f.get('acodec') == 'none':
                height = f.get('height')
                if height:
                    label = f"{height}p | {f['ext']} | {f['format_id']}"
                    video_formats.append((label, f['format_id'], height))
            elif f.get('vcodec') == 'none' and f.get('acodec') != 'none':
                abr = f.get('abr')
                label = f"{abr} kbps | {f['ext']} | {f['format_id']}" if abr else f"{f['format_id']}"
                audio_formats.append((label, f['format_id'], abr))

        video_formats.sort(key=lambda x: x[2], reverse=True)
        audio_formats.sort(key=lambda x: x[2] or 0, reverse=True)

        st.markdown("### 🎥 Choose Video Quality")
        video_choice = st.radio("Video Options:", [v[0] for v in video_formats])
        selected_video_id = next(v[1] for v in video_formats if v[0] == video_choice)

        st.markdown("### 🎧 Choose Audio Only (optional separate download)")
        audio_choice = st.radio("Audio Options:", [a[0] for a in audio_formats])
        selected_audio_id = next(a[1] for a in audio_formats if a[0] == audio_choice)

        # --- VIDEO DOWNLOAD SECTION ---
        st.markdown("### ⬇️ Download Video with Audio")
        video_btn_col, progress_col_v = st.columns([1, 2])
        with video_btn_col:
            download_video = st.button("🎬 Download Video with Audio")

        progress_bar_v = progress_col_v.empty()
        progress_text_v = progress_col_v.empty()

        def build_video_progress_hook():
            def hook(d):
                if d['status'] == 'downloading':
                    downloaded = d.get('downloaded_bytes', 0)
                    total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                    percent = (downloaded / total) * 100 if total else 0
                    speed = d.get('speed', 0)
                    eta = d.get('eta', 0)

                    bar_progress = percent / 100
                    progress_bar_v.progress(bar_progress)
                    progress_text_v.markdown(
                        f"📥 **Downloading...** {percent:.2f}% of {format_bytes(total)} at {format_bytes(speed)}/s | ETA: {format_eta(eta)}"
                    )
                elif d['status'] == 'finished':
                    progress_bar_v.progress(1.0)
                    progress_text_v.markdown("✅ **Download complete, merging...**")
            return [hook]

        if download_video:
            best_audio_id = audio_formats[0][1]
            final_format = f"{selected_video_id}+{best_audio_id}"

            ydl_opts = {
                'format': final_format,
                'outtmpl': "%(title)s.%(ext)s",
                'merge_output_format': 'mp4',
                'quiet': True,
                'progress_hooks': build_video_progress_hook(),
            }

            with YoutubeDL(ydl_opts) as ydl:
                try:
                    ydl.download([url])
                    st.success("✅ Video with audio downloaded successfully!")
                except Exception as e:
                    st.error(f"Download error: {e}")

        # --- AUDIO DOWNLOAD SECTION ---
        st.markdown("### ⬇️ Download Audio Only")
        audio_btn_col, progress_col_a = st.columns([1, 2])
        with audio_btn_col:
            download_audio = st.button("🎵 Download Audio Only")

        progress_bar_a = progress_col_a.empty()
        progress_text_a = progress_col_a.empty()

        def build_audio_progress_hook():
            def hook(d):
                if d['status'] == 'downloading':
                    downloaded = d.get('downloaded_bytes', 0)
                    total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                    percent = (downloaded / total) * 100 if total else 0
                    speed = d.get('speed', 0)
                    eta = d.get('eta', 0)

                    bar_progress = percent / 100
                    progress_bar_a.progress(bar_progress)
                    progress_text_a.markdown(
                        f"📥 **Downloading...** {percent:.2f}% of {format_bytes(total)} at {format_bytes(speed)}/s | ETA: {format_eta(eta)}"
                    )
                elif d['status'] == 'finished':
                    progress_bar_a.progress(1.0)
                    progress_text_a.markdown("✅ **Download complete!**")
            return [hook]

        if download_audio:
            ydl_opts = {
                'format': selected_audio_id,
                'outtmpl': "%(title)s.%(ext)s",
                'quiet': True,
                'progress_hooks': build_audio_progress_hook(),
            }

            with YoutubeDL(ydl_opts) as ydl:
                try:
                    ydl.download([url])
                    st.success("✅ Audio downloaded successfully!")
                except Exception as e:
                    st.error(f"Download error: {e}")

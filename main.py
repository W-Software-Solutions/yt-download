import streamlit as st
from yt_dlp import YoutubeDL
import os, shutil, zipfile, re, tempfile

st.set_page_config(page_title="YouTube Downloader", layout="centered")
st.title("📥 YouTube Downloader")

mode = st.radio("Select download type:", ["🎬 Single Video", "📃 Playlist"], horizontal=True)
url = st.text_input("Enter YouTube URL:")

DOWNLOAD_DIR = "downloads"
ZIP_FILE = os.path.join(DOWNLOAD_DIR, "playlist_downloads.zip")

def fmt_bytes(b): return f"{b/1024/1024:.2f} MiB" if b else "N/A"
def fmt_eta(s): return f"{s//60}:{int(s%60):02}" if s else "N/A"
def sanitize_filename(title): return re.sub(r'[^\w\-_\. ]', '_', title)

def hook_factory(c): 
    prog = c.progress(0); txt = c.empty()
    def hook(d):
        if d['status'] == "downloading":
            dl, tot = d.get('downloaded_bytes', 0), d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            pct = (dl / tot) * 100 if tot else 0
            prog.progress(pct / 100)
            txt.markdown(f"⏬ {pct:.1f}% of {fmt_bytes(tot)} at {fmt_bytes(d.get('speed', 0))}/s ETA {fmt_eta(d.get('eta', 0))}")
        elif d['status'] == "finished":
            prog.progress(1.0)
            txt.markdown("✅ Download complete")
    return [hook]

def download_mp4(u, outdir, progress_container=None):
    opts = {
        'format': 'bestvideo+bestaudio',
        'merge_output_format': 'mp4',
        'outtmpl': os.path.join(outdir, "%(title).200s [%(id)s].%(ext)s"),
        'quiet': True
    }
    if progress_container:
        opts['progress_hooks'] = hook_factory(progress_container)
    with YoutubeDL(opts) as ydl:
        ydl.download([u])

def download_video(video_url, outdir, progress_container=None):
    try:
        opts = {
            'format': 'bestvideo+bestaudio',
            'merge_output_format': 'mp4',
            'outtmpl': os.path.join(outdir, "%(title).200s [%(id)s].%(ext)s"),
            'quiet': True
        }
        if progress_container:
            opts['progress_hooks'] = hook_factory(progress_container)
        with YoutubeDL(opts) as ydl:
            ydl.download([video_url])
        return True, None
    except Exception as e:
        return False, str(e)

# --- Single Video Mode ---
if mode == "🎬 Single Video" and url:
    st.subheader("🎬 Single Video Download")

    with st.spinner("Fetching video info..."):
        try:
            with YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                formats = info.get('formats', [])
        except Exception as e:
            st.error(f"Error fetching info: {e}")
            formats = []

    if formats:
        st.markdown(f"**Video Title:** `{info.get('title')}`")
        st.video(info.get('url'))

        video_formats = [f for f in formats if f.get('vcodec') != 'none' and f.get('acodec') == 'none']
        audio_formats = [f for f in formats if f.get('vcodec') == 'none' and f.get('acodec') != 'none']

        compatible_pairs = []
        for v in video_formats:
            for a in audio_formats:
                if v['ext'] == a['ext']:
                    compatible_pairs.append({'video': v, 'audio': a})

        compatible_pairs.sort(
            key=lambda x: (
                x['video'].get('height') or 0,
                x['audio'].get('abr') or 0
            ),
            reverse=True
        )

        if not compatible_pairs:
            st.error("No compatible video/audio format pairs found.")
        else:
            video_display_list = [
                f"{pair['video'].get('height', 'N/A')}p | {pair['video']['ext']} | {pair['video']['format_id']}"
                for pair in compatible_pairs
            ]
            audio_display_list = [
                f"{pair['audio'].get('abr', 'N/A')} kbps | {pair['audio']['ext']} | {pair['audio']['format_id']}"
                for pair in compatible_pairs
            ]

            selected_idx = 0
            selected_video_display = st.selectbox("🎥 Select Video Quality:", video_display_list, index=selected_idx)
            selected_audio_display = st.selectbox("🎧 Select Audio Quality:", audio_display_list, index=selected_idx)

            selected_pair = compatible_pairs[selected_idx]
            selected_video_id = selected_pair['video']['format_id']
            selected_audio_id = selected_pair['audio']['format_id']

            col1, col2 = st.columns(2)

            with col1:
                if st.button("⬇️ Download Video with Audio"):
                    safe_title = sanitize_filename(info.get('title', 'video'))
                    filename = f"{safe_title}.mp4"
                    ydl_opts = {
                        'format': f"{selected_video_id}+{selected_audio_id}",
                        'merge_output_format': 'mp4',
                        'outtmpl': filename,
                        'quiet': True,
                        'progress_hooks': hook_factory(st.container())
                    }
                    with YoutubeDL(ydl_opts) as ydl:
                        try:
                            ydl.download([url])
                            with open(filename, "rb") as f:
                                st.success("Download finished ✅")
                                st.download_button("📥 Download Merged Video", f, file_name=filename, mime="video/mp4")
                        except Exception as e:
                            st.error(f"Error: {e}")

            with col2:
                if st.button("⭐ Download Best Quality"):
                    safe_title = sanitize_filename(info.get('title', 'video'))
                    filename = f"{safe_title}_best.mp4"
                    ydl_opts = {
                        'format': 'bestvideo+bestaudio',
                        'merge_output_format': 'mp4',
                        'outtmpl': filename,
                        'quiet': True,
                        'progress_hooks': hook_factory(st.container())
                    }
                    with YoutubeDL(ydl_opts) as ydl:
                        try:
                            ydl.download([url])
                            with open(filename, "rb") as f:
                                st.success("Best quality video downloaded ✅")
                                st.download_button("📥 Download Best Video", f, file_name=filename, mime="video/mp4")
                        except Exception as e:
                            st.error(f"Error: {e}")

# --- Playlist Mode ---
if mode == "📃 Playlist" and url:
    if st.button("📦 Download Playlist as ZIP"):
        with st.spinner("Fetching playlist info..."):
            try:
                with YoutubeDL({'quiet': True, 'extract_flat': True}) as ydl:
                    playlist_info = ydl.extract_info(url, download=False)
                    entries = playlist_info.get('entries', [])
                    playlist_title = sanitize_filename(playlist_info.get('title', 'playlist'))
            except Exception as e:
                st.error(f"Error: {e}")
                st.stop()

        st.subheader(f"📃 Playlist: {playlist_title}")
        st.markdown("### 📄 Videos to be downloaded:")
        for idx, video in enumerate(entries, 1):
            st.write(f"{idx}. {video.get('title')}")

        with tempfile.TemporaryDirectory() as temp_dir:
            downloaded_files = []

            for idx, video in enumerate(entries, 1):
                st.markdown(f"---\n### ⏬ Downloading {idx}/{len(entries)}: **{video.get('title')}**")
                video_url = f"https://www.youtube.com/watch?v={video['id']}"
                progress_area = st.container()

                success, err = download_video(video_url, temp_dir, progress_area)
                if success:
                    downloaded_files.append(video['title'])
                else:
                    st.error(f"❌ Failed to download: {video['title']} | Error: {err}")

            zip_path = os.path.join(temp_dir, f"{playlist_title}.zip")
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for file in os.listdir(temp_dir):
                    if file.endswith(".mp4"):
                        zipf.write(os.path.join(temp_dir, file), arcname=file)

            with open(zip_path, "rb") as zf:
                st.success("✅ Playlist downloaded and zipped successfully!")
                st.download_button("📦 Download ZIP", zf, file_name=f"{playlist_title}.zip")














































# import streamlit as st
# from yt_dlp import YoutubeDL
# import os, shutil, zipfile, math

# st.set_page_config(page_title="YouTube Downloader", layout="centered")
# st.title("📥 YouTube Downloader (Single + Bulk Playlist)")

# url = st.text_input("Enter YouTube URL (video or playlist):")
# DOWNLOAD_DIR = "downloads"
# ZIP_FILE = os.path.join(DOWNLOAD_DIR, "playlist_downloads.zip")

# def fmt_bytes(b): return f"{b/1024/1024:.2f} MiB" if b else "N/A"
# def fmt_eta(s): return f"{s//60}:{int(s%60):02}" if s else "N/A"

# def hook_factory(c): 
#     prog = c.progress(0); txt = c.empty()
#     def hook(d):
#         if d['status']=="downloading":
#             dl, tot = d.get('downloaded_bytes',0), d.get('total_bytes') or d.get('total_bytes_estimate',0)
#             pct = (dl/tot)*100 if tot else 0
#             prog.progress(pct/100)
#             txt.markdown(f"⏬ {pct:.1f}% of {fmt_bytes(tot)} at {fmt_bytes(d.get('speed',0))}/s ETA {fmt_eta(d.get('eta',0))}")
#         elif d['status']=="finished":
#             prog.progress(1.0); txt.markdown("✅ downloaded & merged")
#     return [hook]

# def download_mp4(u, outdir):
#     opts = {
#         'format': 'bestvideo+bestaudio',
#         'merge_output_format': 'mp4',
#         'outtmpl': os.path.join(outdir, "%(title).200s.%(ext)s"),
#         'progress_hooks': hook_factory(st.container()),
#         'quiet': True
#     }
#     with YoutubeDL(opts) as ydl:
#         ydl.download([u])

# def zip_all(outdir, zipf):
#     with zipfile.ZipFile(zipf, 'w') as z:
#         for f in os.listdir(outdir):
#             if f.endswith('.mp4'):
#                 z.write(os.path.join(outdir,f), f)

# if url:
#     st.write("🔍 Checking URL type...")
#     with YoutubeDL({'quiet':True, 'extract_flat':'in_playlist', 'dump_single_json':True}) as ydl:
#         info = ydl.extract_info(url, download=False)
#     is_pl = info.get('_type') == 'playlist'

#     choice = "Playlist" if is_pl else "Single Video"
#     st.success(f"Detected as: **{choice}**")

#     if is_pl:
#         if st.button("⬇️ Download Entire Playlist"):
#             shutil.rmtree(DOWNLOAD_DIR, ignore_errors=True); os.makedirs(DOWNLOAD_DIR, exist_ok=True)
#             for entry in info['entries']:
#                 vid_url = f"https://www.youtube.com/watch?v={entry['id']}"
#                 st.write(f"▶️ Downloading: {entry['title']}")
#                 download_mp4(vid_url, DOWNLOAD_DIR)
#             zip_all(DOWNLOAD_DIR, ZIP_FILE)
#             with open(ZIP_FILE, "rb") as f:
#                 st.download_button("📦 Download Playlist ZIP", f, file_name="youtube_playlist.zip", mime="application/zip")
#     else:
#         st.write(f"▶️ Video: **{info['title']}**")
#         if st.button("⬇️ Download Best Quality"):
#             os.makedirs(DOWNLOAD_DIR, exist_ok=True)
#             download_mp4(url, DOWNLOAD_DIR)
#             st.success("✅ Video downloaded!")



































# # import streamlit as st
# # from yt_dlp import YoutubeDL
# # import math
# # import os
# # import re

# # st.set_page_config(page_title="YouTube Downloader", layout="centered")
# # st.title("📹 YouTube Downloader with Quality Selector + Progress Bar")

# # url = st.text_input("Enter YouTube video URL:")

# # def format_bytes(bytes):
# #     if bytes is None:
# #         return "N/A"
# #     mb = bytes / (1024 * 1024)
# #     return f"{mb:.2f} MiB"

# # def format_eta(seconds):
# #     if seconds is None:
# #         return "N/A"
# #     minutes = math.floor(seconds / 60)
# #     seconds = int(seconds % 60)
# #     return f"{minutes}:{seconds:02}"

# # def sanitize_filename(title):
# #     return re.sub(r'[^\w\-_\. ]', '_', title)

# # if url:
# #     with st.spinner("Fetching video info..."):
# #         try:
# #             with YoutubeDL({'quiet': True}) as ydl:
# #                 info = ydl.extract_info(url, download=False)
# #                 formats = info.get('formats', [])
# #         except Exception as e:
# #             st.error(f"Error: {e}")
# #             formats = []

# #     if formats:
# #         st.subheader(f"🎞️ {info.get('title')}")
# #         st.video(info.get('url'))

# #         video_formats = []
# #         audio_formats = []

# #         for f in formats:
# #             if f.get('vcodec') != 'none' and f.get('acodec') == 'none':
# #                 height = f.get('height')
# #                 if height:
# #                     label = f"{height}p | {f['ext']} | {f['format_id']}"
# #                     video_formats.append((label, f['format_id'], height))
# #             elif f.get('vcodec') == 'none' and f.get('acodec') != 'none':
# #                 abr = f.get('abr')
# #                 label = f"{abr} kbps | {f['ext']} | {f['format_id']}" if abr else f"{f['format_id']}"
# #                 audio_formats.append((label, f['format_id'], abr))

# #         video_formats.sort(key=lambda x: x[2], reverse=True)
# #         audio_formats.sort(key=lambda x: x[2] or 0, reverse=True)

# #         st.markdown("### 🎥 Choose Video Quality")
# #         video_choice = st.radio("Video Options:", [v[0] for v in video_formats])
# #         selected_video_id = next(v[1] for v in video_formats if v[0] == video_choice)

# #         st.markdown("### 🎧 Choose Audio Only (optional separate download)")
# #         audio_choice = st.radio("Audio Options:", [a[0] for a in audio_formats])
# #         selected_audio_id = next(a[1] for a in audio_formats if a[0] == audio_choice)

# #         # --- VIDEO DOWNLOAD SECTION ---
# #         st.markdown("### ⬇️ Download Video with Audio")
# #         video_btn_col, progress_col_v = st.columns([1, 2])
# #         with video_btn_col:
# #             download_video = st.button("🎬 Download Video with Audio")

# #         progress_bar_v = progress_col_v.empty()
# #         progress_text_v = progress_col_v.empty()

# #         def build_video_progress_hook():
# #             def hook(d):
# #                 if d['status'] == 'downloading':
# #                     downloaded = d.get('downloaded_bytes', 0)
# #                     total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
# #                     percent = (downloaded / total) * 100 if total else 0
# #                     speed = d.get('speed', 0)
# #                     eta = d.get('eta', 0)
# #                     bar_progress = percent / 100
# #                     progress_bar_v.progress(bar_progress)
# #                     progress_text_v.markdown(
# #                         f"📥 **Downloading...** {percent:.2f}% of {format_bytes(total)} at {format_bytes(speed)}/s | ETA: {format_eta(eta)}"
# #                     )
# #                 elif d['status'] == 'finished':
# #                     progress_bar_v.progress(1.0)
# #                     progress_text_v.markdown("✅ **Download complete, merging...**")
# #             return [hook]

# #         if download_video:
# #             best_audio_id = audio_formats[0][1]
# #             final_format = f"{selected_video_id}+{best_audio_id}"
# #             safe_title = sanitize_filename(info.get('title', 'video'))
# #             video_filename = f"{safe_title}.mp4"

# #             ydl_opts = {
# #                 'format': final_format,
# #                 'outtmpl': video_filename,
# #                 'merge_output_format': 'mp4',
# #                 'quiet': True,
# #                 'progress_hooks': build_video_progress_hook(),
# #             }

# #             with YoutubeDL(ydl_opts) as ydl:
# #                 try:
# #                     ydl.download([url])
# #                     st.success("✅ Video with audio downloaded successfully!")
# #                     with open(video_filename, "rb") as f:
# #                         st.download_button("📥 Click to Download Video", f, file_name=video_filename, mime="video/mp4")
# #                 except Exception as e:
# #                     st.error(f"Download error: {e}")

# #         # --- AUDIO DOWNLOAD SECTION ---
# #         st.markdown("### ⬇️ Download Audio Only")
# #         audio_btn_col, progress_col_a = st.columns([1, 2])
# #         with audio_btn_col:
# #             download_audio = st.button("🎵 Download Audio Only")

# #         progress_bar_a = progress_col_a.empty()
# #         progress_text_a = progress_col_a.empty()

# #         def build_audio_progress_hook():
# #             def hook(d):
# #                 if d['status'] == 'downloading':
# #                     downloaded = d.get('downloaded_bytes', 0)
# #                     total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
# #                     percent = (downloaded / total) * 100 if total else 0
# #                     speed = d.get('speed', 0)
# #                     eta = d.get('eta', 0)
# #                     bar_progress = percent / 100
# #                     progress_bar_a.progress(bar_progress)
# #                     progress_text_a.markdown(
# #                         f"📥 **Downloading...** {percent:.2f}% of {format_bytes(total)} at {format_bytes(speed)}/s | ETA: {format_eta(eta)}"
# #                     )
# #                 elif d['status'] == 'finished':
# #                     progress_bar_a.progress(1.0)
# #                     progress_text_a.markdown("✅ **Download complete!**")
# #             return [hook]

# #         if download_audio:
# #             safe_title = sanitize_filename(info.get('title', 'audio'))
# #             audio_filename = f"{safe_title}.webm"  # default format from yt-dlp for audio
# #             ydl_opts = {
# #                 'format': selected_audio_id,
# #                 'outtmpl': audio_filename,
# #                 'quiet': True,
# #                 'progress_hooks': build_audio_progress_hook(),
# #             }

# #             with YoutubeDL(ydl_opts) as ydl:
# #                 try:
# #                     ydl.download([url])
# #                     st.success("✅ Audio downloaded successfully!")
# #                     with open(audio_filename, "rb") as f:
# #                         st.download_button("🎵 Click to Download Audio", f, file_name=audio_filename, mime="audio/webm")
# #                 except Exception as e:
# #                     st.error(f"Download error: {e}")

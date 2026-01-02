import streamlit as st
import os
import sys
import shutil
import time
import json
from pathlib import Path
from datetime import datetime
import contextlib
import io

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

from otbreview.pipeline.main import analyze_video

# Config
RUNS_DIR = PROJECT_ROOT / "runs"
RUNS_DIR.mkdir(exist_ok=True)

st.set_page_config(
    page_title="Chess Video Analysis",
    page_icon="♟️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Session State ---
if 'run_id' not in st.session_state:
    st.session_state.run_id = None
if 'page' not in st.session_state:
    st.session_state.page = "home"

# --- Sidebar: History ---
st.sidebar.title("History")
runs = sorted([d for d in RUNS_DIR.iterdir() if d.is_dir()], key=lambda x: x.name, reverse=True)

if st.sidebar.button("🏠 New Analysis"):
    st.session_state.run_id = None
    st.session_state.page = "home"
    st.rerun()

st.sidebar.markdown("---")
for run_dir in runs:
    run_name = run_dir.name
    # Try to read meta for better name?
    label = run_name
    if st.sidebar.button(f"📄 {label}", key=f"hist_{run_name}"):
        st.session_state.run_id = run_name
        st.session_state.page = "results"
        st.rerun()

# --- Functions ---

def run_analysis(video_file, params):
    # Create Run ID
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    
    # Save Video
    video_path = run_dir / video_file.name
    with open(video_path, "wb") as f:
        f.write(video_file.getbuffer())
    
    # Save Params
    with open(run_dir / "meta.json", "w") as f:
        json.dump(params, f, indent=2)
        
    # Run Pipeline
    log_capture_string = io.StringIO()
    
    status_container = st.status("Processing video...", expanded=True)
    log_area = status_container.empty()
    
    # Custom stdout to capture logs and update UI
    class StreamlitSink:
        def write(self, message):
            log_capture_string.write(message)
            sys.__stdout__.write(message)
            # Update UI occasionally? (Can be slow)
            # log_area.code(log_capture_string.getvalue()[-1000:]) 
        def flush(self):
            sys.__stdout__.flush()

    # We use a simple redirect for now, updating UI after steps might be hard without callbacks
    # Instead, we'll just run it and show the log at the end or if it fails
    
    try:
        with contextlib.redirect_stdout(StreamlitSink()), contextlib.redirect_stderr(StreamlitSink()):
            analyze_video(
                video_path=str(video_path),
                outdir=str(run_dir),
                use_markers=params['use_markers'],
                use_piece_tags=params.get('use_piece_tags', True),
                motion_threshold=params['motion_threshold'],
                stable_duration=params['stable_duration']
            )
        status_container.update(label="Analysis Complete!", state="complete", expanded=False)
        st.session_state.run_id = run_id
        st.session_state.page = "results"
        st.rerun()
        
    except Exception as e:
        status_container.update(label="Analysis Failed!", state="error", expanded=True)
        st.error(f"Error during analysis: {str(e)}")
        st.text_area("Logs", log_capture_string.getvalue(), height=300)
        # Save logs even on failure
        with open(run_dir / "logs.txt", "w") as f:
            f.write(log_capture_string.getvalue())
        raise e

    # Save logs
    with open(run_dir / "logs.txt", "w") as f:
        f.write(log_capture_string.getvalue())


def show_results(run_id):
    run_dir = RUNS_DIR / run_id
    st.title(f"Results: {run_id}")
    
    if not run_dir.exists():
        st.error("Run directory not found.")
        return

    # Layout
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📝 PGN")
        pgn_path = run_dir / "game.pgn"
        if pgn_path.exists():
            pgn_text = pgn_path.read_text()
            st.text_area("PGN", pgn_text, height=200)
            st.download_button("Download PGN", pgn_text, file_name=f"{run_id}.pgn")
        else:
            st.warning("No PGN generated.")

    with col2:
        st.subheader("📊 Files")
        # Zip download
        shutil.make_archive(str(run_dir / "export"), 'zip', run_dir)
        zip_path = run_dir / "export.zip"
        if zip_path.exists():
             with open(zip_path, "rb") as fp:
                 st.download_button("Download Full Report (ZIP)", fp, file_name=f"{run_id}_export.zip")
    
    st.divider()
    
    # Debug Images
    st.subheader("🔍 Debug Visualization")
    debug_dir = run_dir / "debug"
    
    tabs = st.tabs(["Stable Frames", "Warped Board", "Grid Overlay", "Occupancy", "Replay"])
    
    with tabs[0]:
        stable_dir = debug_dir / "stable_frames"
        if stable_dir.exists():
            images = sorted(list(stable_dir.glob("*.png")) + list(stable_dir.glob("*.jpg")))
            if images:
                st.image(str(images[0]), caption="First Stable Frame", use_container_width=True)
                if len(images) > 1:
                    st.info(f"Total stable frames: {len(images)}")
            else:
                st.write("No stable frames found.")
    
    with tabs[1]:
        # Warped board debug
        warped_debug = debug_dir / "warped_board_debug.png"
        if warped_debug.exists():
             st.image(str(warped_debug), caption="Warped Board (Check Perspective)", use_container_width=True)
        else:
             st.write("No warped board debug image.")

    with tabs[2]:
        grid_overlay = debug_dir / "grid_overlay.png"
        if grid_overlay.exists():
             st.image(str(grid_overlay), caption="Grid Overlay (Check Alignment)", use_container_width=True)
        else:
             st.write("No grid overlay image.")
             
    with tabs[3]:
        # Occupancy / Cells
        # Maybe show a grid of recognized cells for the first frame?
        # Or just link to the folder
        st.write("Cell images are saved in debug/cells/")
    
    with tabs[4]:
        st.subheader("♟️ Web Replay")
        # Check if index.html exists
        index_html = run_dir / "index.html"
        if index_html.exists():
            # We need to serve this or read it. 
            # Embedding raw HTML with iframes might run into path issues if it references local files (like css/js).
            # But the generator likely embeds CSS/JS or uses CDNs.
            # Let's check if we can display it.
            # Reading content and using components.html usually works if self-contained.
            # If it references 'game.pgn' via relative path, it might break in streamlit component iframe sandbox.
            
            # Option 1: Read content and try to fix paths?
            # Option 2: Just serve a link? (Can't easily serve local link)
            # Option 3: Use Streamlit Static File Serving? (Too complex setup)
            # Option 4: Assume the generated HTML embeds the PGN or is robust.
            
            # Let's try dumping the HTML directly.
            html_content = index_html.read_text(encoding='utf-8')
            st.components.v1.html(html_content, height=800, scrolling=True)
        else:
            st.warning("Web replay file (index.html) not found.")


# --- Main Logic ---

if st.session_state.page == "home":
    st.title("♟️ OTB Chess Video Analysis")
    st.markdown("""
    Turn your over-the-board chess videos into PGNs automatically!
    
    **Instructions:**
    1. Upload a video (hold phone steady, ensure full board is visible).
    2. Click Run.
    3. Review the PGN and analysis.
    """)
    
    st.divider()
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Settings")
        use_markers = st.checkbox("Use ArUco/AprilTag Markers", value=True, help="Requires markers on board corners")
        motion_threshold = st.number_input("Motion Threshold", value=0.01, format="%.3f", help="Lower = more sensitive to motion")
        stable_duration = st.number_input("Stable Duration (s)", value=0.5, format="%.1f", help="How long board must be still")
        
    with col2:
        st.subheader("Upload Video")
        uploaded_file = st.file_uploader("Choose a video...", type=['mp4', 'mov', 'avi'])
        
        if uploaded_file is not None:
            if st.button("🚀 Run Analysis", type="primary", use_container_width=True):
                params = {
                    "use_markers": use_markers,
                    "motion_threshold": motion_threshold,
                    "stable_duration": stable_duration
                }
                run_analysis(uploaded_file, params)

elif st.session_state.page == "results":
    if st.session_state.run_id:
        show_results(st.session_state.run_id)
    else:
        st.error("No run selected.")
        if st.button("Back to Home"):
            st.session_state.page = "home"
            st.rerun()

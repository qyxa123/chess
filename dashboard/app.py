from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import streamlit as st

from dashboard.utils import (
    create_run_dir,
    discover_runs,
    key_artifacts,
    load_board_grid,
    load_run_metadata,
    save_uploaded_file,
    stream_process,
    write_run_metadata,
    zip_run_directory,
)

st.set_page_config(page_title="OTBReview Web Runner", layout="wide")


def _stream_logs(cmd):
    placeholder = st.empty()
    logs = []
    process_stream = stream_process(cmd)
    for line in process_stream:
        logs.append(line)
        placeholder.code("\n".join(logs[-200:]), language="bash")
    placeholder.code("\n".join(logs[-200:]), language="bash")
    return getattr(process_stream, "returncode", 0), "\n".join(logs)


def _run_marker_pipeline(input_path: Path, run_dir: Path) -> bool:
    cmd = [
        sys.executable,
        "scripts/run_debug_pipeline.py",
        "--input",
        str(input_path),
        "--outdir",
        str(run_dir),
        "--use_markers",
        "1",
    ]
    st.info("Running marker pipeline…")
    code1, logs1 = _stream_logs(cmd)

    report_cmd = [sys.executable, "scripts/make_check_report.py", "--outdir", str(run_dir)]
    st.info("Generating CHECK.html…")
    code2, logs2 = _stream_logs(report_cmd)
    return code1 == 0 and code2 == 0 and "fail" not in (logs1 + logs2).lower()


def _run_tag_pipeline(input_path: Path, run_dir: Path) -> bool:
    script_path = Path("scripts/run_tag_demo.py")
    if not script_path.exists():
        st.error("Tag pipeline script is missing.")
        return False
    cmd = [sys.executable, str(script_path), "--input", str(input_path), "--outdir", str(run_dir)]
    st.info("Running tag pipeline…")
    code, logs = _stream_logs(cmd)
    return code == 0 and "fail" not in logs.lower()


def _sidebar_runs() -> Optional[Path]:
    st.sidebar.title("Previous runs")
    runs = discover_runs()
    if not runs:
        st.sidebar.info("No runs yet")
        return None

    labels = []
    mapping = {}
    for run_id, path in runs:
        meta = load_run_metadata(path)
        label = f"{run_id} | {meta.get('mode', '')} | {meta.get('input_file', path.name)}"
        labels.append(label)
        mapping[label] = path
    selected = st.sidebar.radio("Select run", labels, index=0)
    st.sidebar.divider()
    return mapping.get(selected)


def _board_table(grid):
    st.markdown("#### First board_ids grid")
    st.table(grid)


def _show_results(run_dir: Path):
    st.markdown(f"### Results: {run_dir.name}")
    meta = load_run_metadata(run_dir)
    st.caption(
        f"Input: {meta.get('input_file', 'unknown')} • Mode: {meta.get('mode', 'n/a')} • Timestamp: {meta.get('timestamp', '')}"
    )

    artifacts = key_artifacts(run_dir)
    cols = st.columns(3)
    if artifacts.get("stable"):
        cols[0].image(str(artifacts["stable"]), caption="Stable frame", use_column_width=True)
    if artifacts.get("warped"):
        cols[1].image(str(artifacts["warped"]), caption="Warped board", use_column_width=True)
    if artifacts.get("tag_overlay"):
        cols[2].image(str(artifacts["tag_overlay"]), caption="Tag overlay", use_column_width=True)

    board_path = run_dir / "board_ids.json"
    if not board_path.exists():
        board_path = run_dir / "debug" / "board_ids.json"
    grid = load_board_grid(board_path)
    if grid:
        _board_table(grid)

    report_paths = []
    for fname in ["TAG_CHECK.html", "CHECK.html"]:
        fpath = run_dir / fname
        if fpath.exists():
            report_paths.append(fpath)
    for report in report_paths:
        st.markdown(f"#### {report.name}")
        try:
            st.components.v1.html(report.read_text(encoding="utf-8", errors="ignore"), height=600, scrolling=True)
        except Exception:
            st.warning("Preview not available; open directly below.")
        st.markdown(f"[Open in new tab]({report.resolve().as_uri()})")

    st.markdown("#### Downloads")
    zip_bytes = zip_run_directory(run_dir)
    st.download_button(
        "Download ZIP",
        data=zip_bytes,
        file_name=f"{run_dir.name}.zip",
        mime="application/zip",
    )
    pgn_path = run_dir / "game.pgn"
    if pgn_path.exists():
        with pgn_path.open("rb") as f:
            st.download_button(
                "Download PGN",
                data=f.read(),
                file_name=pgn_path.name,
                mime="application/x-chess-pgn",
            )


def main():
    selected_from_sidebar = _sidebar_runs()
    st.title("OTBReview Web Runner")
    st.caption("Upload a video, choose a mode, click Run.")

    uploaded_file = st.file_uploader("Upload video", type=["mp4", "mov", "MP4", "MOV"])
    mode = st.radio("Mode", ["Marker mode", "Tag mode"], horizontal=True)
    run_clicked = st.button("Run", type="primary")

    if run_clicked:
        if uploaded_file is None:
            st.error("Please upload a video first.")
        else:
            run_dir, run_id = create_run_dir()
            input_path = save_uploaded_file(uploaded_file, run_dir)
            write_run_metadata(
                run_dir,
                {
                    "run_id": run_id,
                    "input_file": uploaded_file.name,
                    "mode": mode,
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                },
            )
            st.success(f"Saved to {input_path}")
            success = False
            try:
                if mode == "Tag mode":
                    success = _run_tag_pipeline(input_path, run_dir)
                else:
                    success = _run_marker_pipeline(input_path, run_dir)
            except Exception as exc:  # noqa: BLE001
                st.error(f"Pipeline failed: {exc}")
            st.session_state["selected_run"] = str(run_dir)
            if success:
                st.success("Run completed.")
            else:
                st.warning("Run finished with warnings. Check logs above and reports below.")

    selected_run: Optional[Path] = None
    if "selected_run" in st.session_state:
        candidate = Path(st.session_state["selected_run"])
        if candidate.exists():
            selected_run = candidate
    if selected_from_sidebar:
        selected_run = selected_from_sidebar

    st.divider()
    if selected_run and selected_run.exists():
        _show_results(selected_run)
    else:
        st.info("Select a previous run from the sidebar or start a new one.")


if __name__ == "__main__":
    main()

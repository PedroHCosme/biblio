"""Ingestion panel. Calls pipeline.ingest() and shows its progress.

No search, no reading, no chat.
"""
from pathlib import Path

import gradio as gr


def _choose_folder() -> str:
    """Opens the native folder picker."""
    import tkinter as tk
    from tkinter import filedialog

    root_tk = tk.Tk()
    root_tk.withdraw()
    root_tk.attributes("-topmost", True)
    try:
        return filedialog.askdirectory(title="Choose the folder with documents") or ""
    finally:
        root_tk.destroy()

from biblio import index, meta, pipeline, skill
from biblio.paths import DEFAULT_BIBLIOTHECA, known_bibliothecas, root


def _search_example(bibliotheca: Path) -> str:
    """A real term from what just went in, so the user doesn't have to invent one."""
    for folder in sorted((p for p in bibliotheca.iterdir() if p.is_dir()),
                         key=lambda p: p.stat().st_mtime, reverse=True):
        if terms := meta.read(folder).get("terms"):
            return terms[0]
        return folder.name.replace("-", " ")
    return "your query here"


def _process(files, folder, dest, do_summary, force):
    folder = (folder or "").strip().strip('"')
    targets = list(files or []) + ([folder] if folder else [])
    if not targets:
        yield "Choose files (.pdf, .md, .txt) or provide a folder."
        return

    bibliotheca = root(dest)
    lines, queue = [], []
    for target in targets:
        count = pipeline.ingest(
            target, output=bibliotheca, force=force,
            summary="yes" if do_summary else "no",
            ask=lambda _: True, warn=queue.append,
        )
        lines += queue
        queue.clear()
        lines.append(f"→ {count['ok']} processed, {count['skipped']} unchanged, "
                     f"{count['failed']} failed")
        yield "\n".join(lines)

    index.generate(output=bibliotheca, summary="no")
    skill.install(warn=lines.append)

    lines += [
        "",
        "─" * 60,
        f"Bibliotheca: {bibliotheca.resolve()}",
        "INDEX.md and CLAUDE.md updated. The Claude Code skill is installed,",
        "so it already knows how to search — no setup needed.",
        "",
        "Try it in Claude Code or the terminal:",
        f'    biblio search "{_search_example(bibliotheca)}"',
        "",
        "To restrict a project to this bibliotheca, point the agent to this folder:",
        "the CLAUDE.md in it already restricts search to this corpus.",
    ]
    yield "\n".join(lines)


def launch(output=None, share: bool = False) -> None:
    known = [Path(c).name for c in known_bibliothecas()]
    default = Path(output).name if output else (known[0] if known
                                                else DEFAULT_BIBLIOTHECA.name)

    from biblio.version_check import _installed_version, _remote_version
    v_local, v_remote = _installed_version(), _remote_version()
    version_notice = (f"  **Version {v_remote} available** (installed: {v_local})"
                      f" — run `biblio update` in the terminal to upgrade."
                      if v_remote and v_remote != v_local else "")

    with gr.Blocks(title="biblio") as app:
        gr.Markdown(f"# biblio{version_notice}")
        dest = gr.Dropdown(
            label="Bibliotheca",
            info="One topic per bibliotheca. Type a new name to start another.",
            choices=sorted({*known, default}), value=default,
            allow_custom_value=True,
        )
        file_input = gr.File(label="Files", file_count="multiple",
                             file_types=[".pdf", ".md", ".txt"])
        with gr.Row():
            folder = gr.Textbox(
                label="or an entire folder", scale=4,
                placeholder=r"click Choose folder  —  or paste the path here",
                info="Processes all .pdf, .md and .txt in the folder and subfolders.")
            choose_btn = gr.Button("📁 Choose folder", scale=1)
        choose_btn.click(_choose_folder, None, folder)
        with gr.Row():
            do_summary = gr.Checkbox(
                value=False,
                label="Generate summary and keywords for each document",
                info="Optional. Uses a local model (Ollama). Checking this authorizes "
                     "downloading ~3 GB the first time. Without this, search works the "
                     "same — only the terms line in the index is missing.")
            force = gr.Checkbox(label="Reprocess even without changes")
        btn = gr.Button("Add documents", variant="primary")
        progress = gr.Textbox(label="Progress", lines=18, max_lines=18, autoscroll=True)

        btn.click(_process, [file_input, folder, dest, do_summary, force], progress)
    app.launch(inbrowser=True, share=share)

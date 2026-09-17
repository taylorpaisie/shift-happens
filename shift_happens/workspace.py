"""Per-browser state: source text stays in a memory Store, not global server state."""
from uuid import uuid4
from .demo import create_demo
from .imports import decode_upload, parse_results
from .config import Settings

def initial_workspace():
    return {"demo": True, "files": []}


def options(workspace):
    choices = [{"label": "SYNTHETIC · FEL + MEME + Contrast-FEL", "value": "demo"}] if workspace["demo"] else []
    choices.extend({"label": f"{f['method']} {f['version']} · {f['filename']} · independent", "value": f["id"]} for f in workspace["files"])
    return choices


def import_files(workspace, contents, filenames, settings=None):
    settings = settings or Settings()
    updated = {"demo": workspace["demo"], "files": list(workspace["files"])}
    errors, selected, count = [], None, 0
    used = sum(len(f["text"].encode("utf-8")) for f in updated["files"])
    for content, filename in zip(contents or [], filenames or []):
        try:
            text = decode_upload(content, settings.max_file_bytes)
            if used + len(text.encode("utf-8")) > settings.max_workspace_bytes or len(updated["files"]) >= 20:
                raise ValueError(f"Workspace limit reached ({settings.max_workspace_mib} MiB / 20 files). Remove an analysis before importing more.")
            a = parse_results(text, filename, settings.max_file_bytes, settings.max_codons)
            selected = uuid4().hex
            updated["files"].append({"id": selected, "filename": filename, "text": text, "method": a.method, "version": a.version})
            used += len(text.encode("utf-8"))
            count += 1
        except (ValueError, TypeError, OverflowError) as error:
            errors.append(f"{filename}: {error}")
    notice = f"Imported {count} file(s). Native analyses remain independent because alignment identity cannot be verified." if count else ""
    return updated, selected, "\n".join(filter(None, [notice, *errors]))


def active_analyses(workspace, selected, settings=None):
    settings = settings or Settings()
    if selected == "demo" and workspace["demo"]:
        return create_demo()
    for source in workspace["files"]:
        if source["id"] == selected:
            return [parse_results(source["text"], source["filename"], settings.max_file_bytes, settings.max_codons)]
    return []

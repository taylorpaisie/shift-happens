"""Per-browser state: source text stays in a memory Store, not global server state."""
from uuid import uuid4
from .demo import create_demo
from .imports import decode_upload, parse_results
from .config import Settings
from .model import native_comparison_key

COMPARISON_PREFIX = "compare:"

def initial_workspace():
    return {"demo": True, "files": []}


def comparison_pairs(workspace, settings=None):
    settings = settings or Settings()
    groups = {}
    for source in workspace["files"]:
        try:
            analysis = parse_results(source["text"], source["filename"], settings.max_file_bytes, settings.max_codons)
        except (ValueError, TypeError, OverflowError):
            continue
        key = native_comparison_key(analysis)
        if key is not None:
            groups.setdefault(key, []).append((source, analysis))
    pairs = []
    for key, members in groups.items():
        fels = [item for item in members if item[1].method == "FEL"]
        memes = [item for item in members if item[1].method == "MEME"]
        if len(fels) == len(memes) == 1:
            sources = (fels[0][0], memes[0][0])
            pairs.append({
                "value": COMPARISON_PREFIX + ":".join(source["id"] for source in sources),
                "label": f"FEL + MEME · {key[0]} · metadata-matched",
                "source_ids": tuple(source["id"] for source in sources),
                "analyses": (fels[0][1], memes[0][1]),
            })
    return pairs


def options(workspace, settings=None):
    choices = [{"label": "SYNTHETIC · FEL + MEME + Contrast-FEL", "value": "demo"}] if workspace["demo"] else []
    choices.extend({"label": pair["label"], "value": pair["value"]} for pair in comparison_pairs(workspace, settings))
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
    pairs = comparison_pairs(updated, settings)
    selected_pair = next((pair for pair in pairs if selected in pair["source_ids"]), None)
    if selected_pair:
        selected = selected_pair["value"]
    notice = (f"Imported {count} file(s). Added a metadata-matched FEL + MEME comparison; alignment content remains unverified."
              if count and selected_pair else
              f"Imported {count} file(s). Native analyses remain independent because alignment identity cannot be verified." if count else "")
    return updated, selected, "\n".join(filter(None, [notice, *errors]))


def active_analyses(workspace, selected, settings=None):
    settings = settings or Settings()
    if selected == "demo" and workspace["demo"]:
        return create_demo()
    for pair in comparison_pairs(workspace, settings):
        if pair["value"] == selected:
            return list(pair["analyses"])
    for source in workspace["files"]:
        if source["id"] == selected:
            return [parse_results(source["text"], source["filename"], settings.max_file_bytes, settings.max_codons)]
    return []


def source_ids_for_selection(workspace, selected, settings=None):
    if selected is None:
        return set()
    for pair in comparison_pairs(workspace, settings):
        if pair["value"] == selected:
            return set(pair["source_ids"])
    return {selected}

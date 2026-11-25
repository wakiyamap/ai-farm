#!/usr/bin/env python3
"""Write the human-side documents of one claude.ai Project from a data export.

Usage: python3 -I extract_project_docs.py <projects.json> <project name> <out dir>

Reads projects.json from the claude.ai data export, finds the project by name,
and writes each document under <out dir>, keeping its path minus the leading
"farm/". Code that is already published from the server (phase bundles,
current/ copies, tools/, publish/) is skipped. Prints counts only.
"""
import json
import os
import sys

SKIP_PREFIXES = ("farm/phase", "farm/current/", "farm/tools/", "farm/publish/")


def first(d, *keys):
    for k in keys:
        if isinstance(d, dict) and d.get(k) not in (None, ""):
            return d[k]
    return None


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    src, name, out = sys.argv[1:]
    with open(src, encoding="utf-8") as f:
        data = json.load(f)
    projects = data if isinstance(data, list) else first(data, "projects") or [data]
    match = [p for p in projects if first(p, "name") == name]
    if not match:
        names = sorted(str(first(p, "name")) for p in projects)
        sys.exit("project not found. projects in the export:\n  " + "\n  ".join(names))
    proj = match[0]
    docs = first(proj, "docs", "documents", "knowledge") or []
    if not docs:
        sys.exit(f"project found but it has no docs; keys: {sorted(proj)}")

    written = skipped = 0
    seen = set()
    for d in docs:
        path = first(d, "filename", "path", "name", "title")
        content = first(d, "content", "text", "body")
        if not path or content is None:
            sys.exit(f"unexpected doc shape; keys: {sorted(d)}")
        if path.startswith(SKIP_PREFIXES):
            skipped += 1
            continue
        rel = path[len("farm/"):] if path.startswith("farm/") else path
        rel = os.path.normpath(rel)
        if rel.startswith("..") or os.path.isabs(rel):
            sys.exit(f"unsafe path in export: {path!r}")
        if rel in seen:
            continue
        seen.add(rel)
        dest = os.path.join(out, rel)
        os.makedirs(os.path.dirname(dest) or out, exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            f.write(content)
        written += 1
    print(f"project '{name}': {len(docs)} docs, wrote {written}, skipped {skipped} (code already in server/)")


if __name__ == "__main__":
    main()

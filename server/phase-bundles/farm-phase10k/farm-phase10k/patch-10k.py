#!/usr/bin/env python3
"""Phase 10k: exact-text patch for assemble-prompt (a note to meta before a prompt hits its limit).

  patch-10k.py check <assemble-prompt>
  patch-10k.py apply <assemble-prompt> <outdir>

Every old text must occur exactly once, or nothing is written. Safe to re-run (markers).
"""
import os
import sys

HUNKS = [
("WARN_BYTES and the note writer",
'''MAX_BYTES=60000   # dsh loads at most 64 KiB of instructions
''',
'''MAX_BYTES=60000   # dsh loads at most 64 KiB of instructions
WARN_BYTES=56000  # 10k: above this, leave a note for meta before the next edit breaks the instance
NOTE_DIR=/srv/farm/ws/inbox/meta

# One note per instance, rewritten only when the size changes, removed when the prompt is back
# under WARN_BYTES. Written as harness: inbox/ is harness-writable, and root must not write
# through a symlink planted there. A failure here never stops the session.
size_note() {   # $1 = headline, $2 = what it means
  local note="$NOTE_DIR/prompt-size-$INSTANCE.md"
  if runuser -u harness -- grep -qsx "size: $size" "$note"; then
    return 0
  fi
  printf '%s\\n' "# $1" "" "size: $size" "warn above: $WARN_BYTES" "limit: $MAX_BYTES" "" \\
    "$2" "" \\
    "Parts: common.md $(stat -c %s "$PROMPTS/common.md" 2>/dev/null || echo '?') bytes (human-owned), roles/$ROLE.md and roles/TOOLS.md the rest." \\
    "Move detail to wiki pages and keep one line with the page name; run tools/prompt-size.py after every edit." \\
    "(Written by assemble-prompt at $(date -u +%Y-%m-%dT%H:%MZ); it removes this note once the prompt is at or under $WARN_BYTES bytes.)" \\
    | runuser -u harness -- tee "$note" > /dev/null || true
}
''',
"WARN_BYTES=56000"),

("note on failure, note above the warning size, note removed when the prompt is small again",
'''size="$(stat -c %s "$tmp")"
if (( size > MAX_BYTES )); then
  echo "assemble-prompt: prompt for $INSTANCE is $size bytes (max $MAX_BYTES)" >&2
  exit 1
fi
''',
'''size="$(stat -c %s "$tmp")"
if (( size > MAX_BYTES )); then
  echo "assemble-prompt: prompt for $INSTANCE is $size bytes (max $MAX_BYTES)" >&2
  size_note "$INSTANCE cannot start: its prompt is over the size limit" \\
    "Every session of $INSTANCE fails at once until the assembled prompt (common.md + roles/$ROLE.md + roles/TOOLS.md) is at or under $MAX_BYTES bytes. Fix this before anything else."
  exit 1
fi
if (( size > WARN_BYTES )); then
  size_note "$INSTANCE prompt is close to its size limit" \\
    "$INSTANCE still starts, but $(( MAX_BYTES - size )) more bytes in common.md, roles/$ROLE.md or roles/TOOLS.md will stop it."
else
  runuser -u harness -- rm -f "$NOTE_DIR/prompt-size-$INSTANCE.md" 2>/dev/null || true
fi
''',
'size_note "$INSTANCE cannot start'),
]


def plan(text, hunks):
    lines = []
    for title, old, new, marker in hunks:
        if marker in text:
            lines.append(f"  already applied: {title}")
            continue
        n = text.count(old)
        if n != 1:
            raise ValueError(f"{title}: the expected text occurs {n} times (must be exactly 1); nothing was changed")
        text = text.replace(old, new)
        lines.append(f"  ok: {title}")
    return text, lines


def main(argv):
    if len(argv) < 2 or argv[0] not in ("check", "apply") or (argv[0] == "apply" and len(argv) != 3):
        sys.exit(__doc__)
    with open(argv[1], encoding="utf-8") as f:
        text = f.read()
    try:
        out, lines = plan(text, HUNKS)
    except ValueError as exc:
        sys.exit(f"patch-10k: {os.path.basename(argv[1])}: {exc}")
    print(f"{os.path.basename(argv[1])}:")
    print("\n".join(lines))
    if argv[0] == "apply":
        with open(os.path.join(argv[2], os.path.basename(argv[1])), "w", encoding="utf-8") as f:
            f.write(out)


if __name__ == "__main__":
    main(sys.argv[1:])

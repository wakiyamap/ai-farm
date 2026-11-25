#!/usr/bin/env python3
"""Assembled prompt size per role (common.md + role file + TOOLS.md, as /opt/farm/bin/assemble-prompt builds it).

The human's limit for the local earner model is 60000 bytes with >= 4000 bytes headroom
(inbox/meta/2026-11-11-earner-prompt-over-limit.md). Run after every edit of a role file or TOOLS.md.
Exit 1 if any role is above --budget (default 56000).
"""
import argparse
import os
import sys

P = "/srv/farm/prompts"
ROLES = ["earner", "paper-reviewer", "live-operator", "meta", "researcher", "builder", "scout"]


def size(path):
    return os.path.getsize(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=int, default=56000)
    a = ap.parse_args()
    common = size(f"{P}/common.md")
    tools = size(f"{P}/roles/TOOLS.md")
    print(f"common.md {common}  TOOLS.md {tools}")
    bad = 0
    for r in ROLES:
        role = size(f"{P}/roles/{r}.md")
        total = common + 2 + role + 2 + tools
        flag = "OVER" if total > a.budget else "ok"
        bad += total > a.budget
        print(f"{r:15s} role {role:6d}  assembled {total:6d}  headroom_to_60000 {60000 - total:6d}  {flag}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()

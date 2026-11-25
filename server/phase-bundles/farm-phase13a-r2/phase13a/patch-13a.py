#!/usr/bin/env python3
"""Phase 13a text patch.

  patch-13a.py check <run-role>            the old text occurs exactly once
  patch-13a.py apply <run-role> <out>      write the patched copy to <out>

run-role: a claude-harness instance of the earner role (earner-claude) gets the tool list it
needs to build paper bots. The dsh earners never read this list. Until now the earner role fell
through to the common list, which cannot write bots/paper or claims and cannot start a paper bot.
"""
import sys

OLD = """    *)
      echo "$common" ;;
  esac
}
"""
NEW = """    earner)
      # claude-harness earner (13a: earner-claude; the dsh earners never read this list). It builds
      # paper bots like the dsh earner. python3 already means any code as the harness user, so the
      # boundary is the OS user and the gate, not this list. No gate promote, no paper archive.
      echo "$common,Bash(date*),Bash(python3 *),Bash(jq *),Bash(node *),Bash(npm *),Bash(forge *),Bash(cast *),Bash(paper start *),Bash(paper restart *),Bash(paper stop *),Bash(ls *),Bash(cat *),Bash(head *),Bash(tail *),Bash(grep *),Bash(wc *),Bash(sleep *),Bash(cp *),Bash(mkdir -p $wsb/scratch/*),Bash(mkdir -p $wsb/bots/paper/*),Bash(chmod +x $wsb/scratch/*),Bash(chmod +x $wsb/bots/paper/*),Bash(setfacl *),Bash(rm $wsb/claims/*),Bash(bash $wsb/scratch/*),Bash(bash $wsb/bots/paper/*),Bash($wsb/scratch/*),Bash($wsb/bots/paper/*),Edit($ws/bots/paper/**),Edit($ws/claims/**),Edit($ws/inbox/**)" ;;
    *)
      echo "$common" ;;
  esac
}
"""


def main():
    a = sys.argv
    if len(a) < 3 or a[1] not in ("check", "apply"):
        sys.exit(__doc__)
    text = open(a[2], encoding="utf-8").read()
    n = text.count(OLD)
    if n != 1:
        sys.exit(f"{a[2]}: the patch matches {n} times (expected 1); nothing was changed")
    if a[1] == "check":
        print("  run-role: 1 patch matches")
        return
    with open(a[3], "w", encoding="utf-8") as f:
        f.write(text.replace(OLD, NEW))
    print(f"  patched copy written to {a[3]}")


if __name__ == "__main__":
    main()

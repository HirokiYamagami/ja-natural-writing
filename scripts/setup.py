#!/usr/bin/env python3
"""ja-natural-writing を Claude Code（ユーザー全体の設定）に組み込む／外す。

  python3 scripts/setup.py install     組み込む（何度実行しても同じ結果になる）
  python3 scripts/setup.py uninstall   外す
  python3 scripts/setup.py status      組み込み状況を表示する

変更するファイル（変更前に .bak を作る）:
  ~/.claude/CLAUDE.md      日本語ガイドを読み込む1行を追加する
  ~/.claude/settings.json  PostToolUse に textlint の hook を追加する
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[1]
GUIDE = REPO_DIR / "guide" / "japanese_writing_guide.md"
HOOK = REPO_DIR / "hooks" / "textlint_hook.py"
CLAUDE_DIR = Path.home() / ".claude"
CLAUDE_MD = CLAUDE_DIR / "CLAUDE.md"
SETTINGS = CLAUDE_DIR / "settings.json"

BEGIN = "<!-- ja-natural-writing:begin -->"
END = "<!-- ja-natural-writing:end -->"
HOOK_MATCHER = "Write|Edit|MultiEdit"
HOOK_COMMAND = f'python3 "{HOOK}"'


def backup(path):
    if path.exists():
        shutil.copy2(path, path.with_name(path.name + ".bak"))


def claude_md_block():
    return (
        f"{BEGIN}\n"
        "日本語を書く時は、次のガイドに従ってください。\n"
        f"@{GUIDE}\n"
        f"{END}\n"
    )


def strip_block(text):
    if BEGIN not in text:
        return text
    head, rest = text.split(BEGIN, 1)
    tail = rest.split(END, 1)[1] if END in rest else ""
    return (head.rstrip("\n") + "\n" + tail.lstrip("\n")).strip("\n") + "\n"


def is_our_hook(h):
    return str(HOOK) in h.get("command", "") or "ja-natural-writing" in h.get("command", "")


def remove_hook(settings):
    groups = settings.get("hooks", {}).get("PostToolUse", [])
    for g in groups:
        g["hooks"] = [h for h in g.get("hooks", []) if not is_our_hook(h)]
    groups[:] = [g for g in groups if g.get("hooks")]
    if "hooks" in settings and not groups:
        settings["hooks"].pop("PostToolUse", None)


def load_settings():
    if not SETTINGS.exists():
        return {}
    return json.loads(SETTINGS.read_text(encoding="utf-8"))


def save_settings(settings):
    SETTINGS.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def install():
    if not (REPO_DIR / "node_modules" / "textlint").exists():
        print("textlint をインストールします（npm ci）")
        subprocess.run(["npm", "ci"], cwd=REPO_DIR, check=True)

    CLAUDE_DIR.mkdir(exist_ok=True)
    text = CLAUDE_MD.read_text(encoding="utf-8") if CLAUDE_MD.exists() else ""
    new_text = strip_block(text).rstrip("\n") + "\n\n" + claude_md_block() if text.strip() else claude_md_block()
    if new_text != text:
        backup(CLAUDE_MD)
        CLAUDE_MD.write_text(new_text, encoding="utf-8")
    print(f"✓ {CLAUDE_MD} に日本語ガイドの読み込みを設定")

    settings = load_settings()
    remove_hook(settings)
    groups = settings.setdefault("hooks", {}).setdefault("PostToolUse", [])
    groups.append({
        "matcher": HOOK_MATCHER,
        "hooks": [{"type": "command", "command": HOOK_COMMAND, "timeout": 60}],
    })
    backup(SETTINGS)
    save_settings(settings)
    print(f"✓ {SETTINGS} に textlint の hook を登録")
    print("Claude Code を再起動すると有効になります。")


def uninstall():
    if CLAUDE_MD.exists():
        text = CLAUDE_MD.read_text(encoding="utf-8")
        if BEGIN in text:
            backup(CLAUDE_MD)
            CLAUDE_MD.write_text(strip_block(text), encoding="utf-8")
    settings = load_settings()
    if settings:
        backup(SETTINGS)
        remove_hook(settings)
        save_settings(settings)
    print("✓ 日本語ガイドの読み込みと textlint の hook を外しました")


def status():
    md = CLAUDE_MD.exists() and BEGIN in CLAUDE_MD.read_text(encoding="utf-8")
    groups = load_settings().get("hooks", {}).get("PostToolUse", [])
    hook = any(is_our_hook(h) for g in groups for h in g.get("hooks", []))
    print(f"日本語ガイド（CLAUDE.md）: {'組み込み済み' if md else '未設定'}")
    print(f"textlint hook（settings.json）: {'組み込み済み' if hook else '未設定'}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"install": install, "uninstall": uninstall, "status": status}.get(
        cmd, lambda: sys.exit(__doc__))()

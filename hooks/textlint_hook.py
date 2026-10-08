#!/usr/bin/env python3
"""Claude Code の PostToolUse hook。Claude が書いた日本語を textlint でチェックする。

Write / Edit / MultiEdit の直後に呼ばれ、Claude が書き換えた行だけを対象にする。
ファイル内のもともとの文章には指摘を出さない（Claude が触っていない行で止めないため）。
指摘があれば exit 2 で Claude に返し、その場で直させる。

チェックしないもの:
  - 拡張子が .md / .markdown / .txt 以外のファイル
  - 書き換えた部分に日本語がほとんどないもの
  - 引用（行頭が ">"）、行末に style-ignore / textlint-ignore を付けた行
  - config/ignore.txt に書いたパターンに当たるファイル

textlint が見つからない・タイムアウトした等で判定できない時は素通しする（fail open）。
"""
import fnmatch
import glob
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[1]
TEXTLINT_JS = REPO_DIR / "node_modules" / "textlint" / "bin" / "textlint.js"
CONFIG = REPO_DIR / ".textlintrc.json"
IGNORE_FILE = REPO_DIR / "config" / "ignore.txt"

EXTENSIONS = {".md", ".markdown", ".txt"}
MIN_JA_CHARS = 30      # 書き換えた部分の日本語がこれ未満なら見ない
MAX_REPORT = 15        # Claude に返す指摘の上限
TIMEOUT = 40
IGNORE_MARKS = ("style-ignore", "textlint-ignore")
JA_CHAR = re.compile(r"[぀-ヿ一-鿿]")


def find_node():
    if os.environ.get("JA_TEXTLINT_NODE"):
        return os.environ["JA_TEXTLINT_NODE"]
    node = shutil.which("node")
    if node:
        return node
    # nvm で入れた node は hook 実行時の PATH に載っていないことがある
    cands = sorted(glob.glob(os.path.expanduser("~/.nvm/versions/node/*/bin/node")))
    for c in ["/opt/homebrew/bin/node", "/usr/local/bin/node"] + cands[::-1]:
        if os.path.exists(c):
            return c
    return None


def load_ignore_patterns():
    try:
        lines = IGNORE_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    return [l.strip() for l in lines if l.strip() and not l.startswith("#")]


def is_ignored(path):
    p = Path(path).as_posix()
    return any(fnmatch.fnmatch(p, pat) or fnmatch.fnmatch(Path(p).name, pat)
               for pat in load_ignore_patterns())


def changed_line_ranges(tool_name, tool_input, text):
    """Claude が書き換えた行の範囲 [(開始, 終了), ...]（1始まり・両端含む）を返す。"""
    if tool_name == "Write":
        return [(1, text.count("\n") + 1)], tool_input.get("content", "")
    if tool_name == "Edit":
        new_parts = [tool_input.get("new_string", "")]
    elif tool_name == "MultiEdit":
        new_parts = [e.get("new_string", "") for e in tool_input.get("edits", [])]
    else:
        return [], ""
    ranges = []
    for part in new_parts:
        if not part.strip():
            continue
        start = 0
        while True:
            i = text.find(part, start)
            if i < 0:
                break
            first = text.count("\n", 0, i) + 1
            ranges.append((first, first + part.count("\n")))
            start = i + len(part)
    return ranges, "\n".join(new_parts)


def run_textlint(node, path):
    result = subprocess.run(
        [node, str(TEXTLINT_JS), "--config", str(CONFIG), "--format", "json", path],
        cwd=REPO_DIR, capture_output=True, text=True, timeout=TIMEOUT,
    )
    # textlint は指摘ありで exit 1、設定エラー等で exit 2 以上
    if result.returncode not in (0, 1) or not result.stdout.strip():
        return None
    return [m for f in json.loads(result.stdout) for m in f.get("messages", [])]


def short_message(msg):
    # ルールによっては解説や URL が長く続くので、最初の1文程度に切る
    first = msg.strip().split("\n")[0].strip()
    first = re.sub(r"\s*解説: https?://\S+", "", first)
    return first[:120]


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input") or {}
    path = tool_input.get("file_path", "")
    if not path or Path(path).suffix.lower() not in EXTENSIONS:
        return 0
    if "node_modules" in Path(path).parts or is_ignored(path):
        return 0
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return 0

    ranges, written = changed_line_ranges(tool_name, tool_input, text)
    if not ranges or len(JA_CHAR.findall(written)) < MIN_JA_CHARS:
        return 0

    node = find_node()
    if not node or not TEXTLINT_JS.exists():
        return 0
    try:
        messages = run_textlint(node, path)
    except (subprocess.TimeoutExpired, OSError, json.JSONDecodeError):
        return 0
    if not messages:
        return 0

    lines = text.split("\n")
    hits = []
    for m in messages:
        no = m.get("line", 0)
        if not any(a <= no <= b for a, b in ranges):
            continue
        line = lines[no - 1] if 0 < no <= len(lines) else ""
        if line.lstrip().startswith(">") or any(k in line for k in IGNORE_MARKS):
            continue
        rule = m.get("ruleId", "").split("/")[-1]
        hits.append(f"- L{no} [{rule}] {short_message(m.get('message', ''))}")
    if not hits:
        return 0

    more = f"\n（ほか {len(hits) - MAX_REPORT} 件）" if len(hits) > MAX_REPORT else ""
    print(
        f"日本語チェック（textlint）：{Path(path).name} の書き換えた箇所に {len(hits)} 件の指摘があります。\n"
        + "\n".join(hits[:MAX_REPORT]) + more + "\n\n"
        "該当箇所を自然な日本語に直してください。内容は変えず、言い回しだけを直します。\n"
        "固有名詞・引用・意図した表現で直せない行は、行末に <!-- textlint-ignore --> を付けてください。",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())

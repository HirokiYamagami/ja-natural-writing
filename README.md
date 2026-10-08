# ja-natural-writing

Claude Code が書く日本語を自然にするための仕組みです。どのプロジェクトでも使えるように、ユーザー全体の設定（`~/.claude/`）に組み込みます。

仕組みは2つあります。

| 仕組み | タイミング | 役割 |
|---|---|---|
| 日本語ライティングガイド | 書く前 | Claude に最初から自然な日本語で書かせる |
| textlint の hook | 書いた直後 | 機械的に分かる不自然さを見つけて、Claude にその場で直させる |

## 1. 日本語ライティングガイド

`guide/japanese_writing_guide.md` に、自然な日本語で書くためのルールを悪い例と良い例付きでまとめています。翻訳調、AI っぽい定型の言い回し、長すぎる文、カタカナ語の多用などを扱います。

`~/.claude/CLAUDE.md` からこのファイルを読み込むので、すべてのプロジェクトで、チャットの返答も含めて効きます。プロジェクト側に独自の文体ガイドがある場合は、そちらが優先されます。

## 2. textlint の hook

Claude がファイルを書いた・編集した直後（PostToolUse）に、[textlint](https://textlint.github.io/) で日本語をチェックします。指摘があれば Claude に返して、その場で直させます。

- 対象：`.md` `.markdown` `.txt` のうち、日本語を含むもの
- **Claude が書き換えた行だけ**を見ます。もともとあった文章には指摘を出しません
- 引用（行頭が `>`）と、行末に `<!-- textlint-ignore -->` を付けた行は見ません
- textlint が動かない時は素通しします

ルールは [textlint-rule-preset-ja-technical-writing](https://github.com/textlint-ja/textlint-rule-preset-ja-technical-writing) をもとに、誤検知の多いものを外しています（`.textlintrc.json`）。

<!-- textlint-disable -->

| 見つけるもの | 例 |
|---|---|
| 長すぎる文 | 100字を超える文 |
| 読点が多すぎる文 | 1文に「、」が4つ以上 |
| 同じ助詞の重複 | 「私の会社の部署の方針」 |
| 逆接の「が」の重複 | 「〜ですが、〜ですが、」 |
| 冗長な表現 | 「確認を行う」→「確認する」 |
| ら抜き言葉 | 「見れる」「来れる」 |
| 二重否定 | 「〜しないわけではない」 |
| 文体の混在 | 「です・ます」と「だ・である」 |

<!-- textlint-enable -->

外したルールは次のとおりです。

- 句点のない文：箇条書きで誤検知するため
- 漢字の連続：固有名詞で誤検知するため
- 漢数字：「一つ」も自然な日本語のため
- 弱い表現：「思う」を使う場面があるため
- 不自然なアルファベット：単位で誤検知するため

## インストール

Node.js と Python 3 が必要です。

```bash
git clone git@github.com:HirokiYamagami/ja-natural-writing.git ~/GitHub/ja-natural-writing
cd ~/GitHub/ja-natural-writing
python3 scripts/setup.py install
```

`~/.claude/CLAUDE.md` と `~/.claude/settings.json` を書き換えます（変更前のファイルは `.bak` として残ります）。Claude Code を再起動すると有効になります。

```bash
python3 scripts/setup.py status      # 組み込み状況を確認
python3 scripts/setup.py uninstall   # 外す
```

リポジトリのフォルダを移動した時は、`install` をもう一度実行してください（設定には絶対パスが入っています）。

## 調整

- **ガイドを直す**：`guide/japanese_writing_guide.md` を編集します。次のセッションから反映されます
- **ルールを変える**：`.textlintrc.json` を編集します
- **チェックしないファイルを足す**：`config/ignore.txt` に glob を書きます
- **手動でチェックする**：`npx textlint <ファイル>`

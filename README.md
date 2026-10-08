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

### 参考資料

hook のコード（`hooks/textlint_hook.py`）は、いつ・どの行をチェックするかを決めるだけです。何を不自然と判定するかは、プリセットに入っている各ルールが決めています。下の表は、各ルールの README に書かれている参考文献です。

<!-- textlint-disable -->

| チェック内容 | ルール | ルールの参考文献 |
|---|---|---|
| 冗長な表現 | [ja-no-redundant-expression](https://github.com/textlint-ja/textlint-rule-ja-no-redundant-expression) | [「することができる」は有害と考えられる（Qiita）](https://qiita.com/takahi-i/items/a93dc2ff42af6b93f6e0)、[読みやすい文章を書くために心がけたい１０のポイント](https://web.archive.org/web/20170608111205/http://www.sekaihaasobiba.com/entry/2014/10/24/204024)、[誰にでも分かるSEのための文章術（6）（@IT）](http://www.atmarkit.co.jp/ait/articles/1001/19/news106_2.html) |
| 同じ助詞の重複 | [no-doubled-joshi](https://github.com/textlint-ja/textlint-rule-no-doubled-joshi) | [RedPen の Doubled Joshi Validator](https://github.com/redpen-cc/redpen/issues/460)、[事象の構造から見る二重デ格構文の発生（国立国語研究所）](https://www.ninjal.ac.jp/event/specialists/project-meeting/files/JCLWorkshop_no6_papers/JCLWorkshop_No6_01.pdf)、[読みやすさへの工夫 3（てにおは助詞）](http://www.asca-co.com/takumi/2010/07/3.html)、[作文入門](http://www.slideshare.net/takahi-i/ss-13429892) |
| 逆接の「が」の重複 | [no-doubled-conjunctive-particle-ga](https://github.com/textlint-ja/textlint-rule-no-doubled-conjunctive-particle-ga) | [中野智彦ほか「文章中の重複表現の指摘方法の提案」（情報処理学会 第73回全国大会）](https://ipsj.ixsq.nii.ac.jp/ej/?action=pages_view_main&active_action=repository_view_main_item_detail&item_id=108359&item_no=1&page_id=13&block_id=8) |
| 二重否定 | [no-double-negative-ja](https://github.com/textlint-ja/textlint-rule-no-double-negative-ja) | [二重否定表現の使い分けを巡って（京都大学）](https://repository.kulib.kyoto-u.ac.jp/dspace/bitstream/2433/187059/1/Ronko3_043.pdf)、[RedPen の二重否定辞書](https://github.com/redpen-cc/redpen/blob/master/redpen-core/src/main/resources/default-resources/double-negative/double-negative-expression-ja.dat) |
| ら抜き言葉 | [no-dropping-the-ra](https://github.com/textlint-ja/textlint-rule-no-dropping-the-ra) | [クリアコードのブログ](http://www.clear-code.com/blog/2015/8/29.html) |
| 同じ接続詞の連続 | [no-doubled-conjunction](https://github.com/textlint-ja/textlint-rule-no-doubled-conjunction) | no-doubled-joshi をもとに作成 |
| 同じ語の連続 | [ja-no-successive-word](https://github.com/textlint-ja/textlint-rule-ja-no-successive-word) | [RedPen のドキュメント](http://redpen.cc/docs/latest/index_ja.html#successiveword) |
| 長すぎる文 | [sentence-length](https://github.com/textlint-rule/textlint-rule-sentence-length) | 記載なし |
| 読点が多すぎる文 | [max-ten](https://github.com/textlint-ja/textlint-rule-max-ten) | 記載なし |
| 文体の混在 | [no-mix-dearu-desumasu](https://github.com/textlint-ja/textlint-rule-no-mix-dearu-desumasu) | 記載なし |

<!-- textlint-enable -->

文の長さ100字と読点3つまでという上限は、`.textlintrc.json` で決めた値です。どの資料にもとづく数値かは記録していません。

次の動きは hook 独自に決めたもので、元になった資料はありません。

- Claude が書き換えた行だけを見る
- 書き換えた部分の日本語が30字未満なら見ない
- Claude に返す指摘は15件まで
- 引用（行頭が `>`）は見ない

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

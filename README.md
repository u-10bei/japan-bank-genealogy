# 日本の銀行系譜図 (japan-bank-genealogy)

日本の銀行の **合併・統合・改称・再編・破綻** の変遷を、年表上の系譜図としてインタラクティブに可視化するプロジェクトです。

**▶ 系譜図を見る: https://u-10bei.github.io/japan-bank-genealogy/**

- 銀行ごとに設立〜消滅を横線で表示し、合併・改称などのイベントで前身と後継をつなぎます
- 前身・後継でつながる銀行を「系統」としてまとめ、系統ごとに見出し（現存行名・本店所在地・収録行数）を付けて表示します。系統の並び順は「規模順／本店所在地順（北から南）／業態順／起源が古い順」から選べます
- 系統の中では、後継行の上下に前身行を設立順に配置します
- 事業譲渡（`transfer`）は、譲渡元が消滅し、事業の全部を1行が承継した場合のみ系統のつながりとして扱います。一部の事業譲渡（信託業務の移管、破綻行の分割譲渡など）は点線で描き、関係する銀行を選択したときだけ表示します
- 銀行名で検索、またはクリックすると、その銀行の前身・後継の系統全体をハイライトします
- Ctrl/⌘ + ホイール または ドラッグで年表を拡大・移動できます
- `#bank=<id>` を付けた URL で特定の銀行を選択した状態で開けます（例: `#bank=sanwa`）

> [!NOTE]
> 収録状況:
> - **地方銀行（現存62行）・第二地方銀行（現存34行）とその前身行**（国立銀行、戦前の普通銀行、無尽、相互銀行、破綻行など）
> - **信託銀行**: 三菱UFJ信託銀行・三井住友信託銀行・みずほ信託銀行・日本カストディ銀行の系譜（前身の信託会社を含む）
> - **出典**: 有価証券報告書の【沿革】（EDINET。抜粋を [`sources/edinet/`](sources/edinet/) に保存）を一次資料とし、日本語版 Wikipedia の各行記事で補っています。両者が食い違う場合は有価証券報告書を採用し、`note` に記録しています。出典に日付がない場合は年・年月のみ、または設立日を省略しています。
> - **都市銀行・長期信用銀行**: メガバンク・りそな・あおぞら・SBI新生銀行の有価証券報告書の沿革で照合し、日付の細部を Wikipedia で補っています（千代田銀行・大阪銀行・帝国銀行などの戦後改称や戦時合同を含む）。
> - **現存するすべての銀行**: 金融庁「銀行免許一覧」（[`sources/fsa/`](sources/fsa/)、外国銀行支店を除く）に載る132行をすべて収録し、`scripts/compare_fsa.py` で一致を確認しています。新形態銀行（ネット銀行・流通系）、ゆうちょ銀行、信託銀行、政府系（日本政策投資銀行・国際協力銀行）を含みます。
> - 有価証券報告書のない銀行は、全国銀行協会「銀行変遷史データベース」の記述（出典URLを記載）や Wikipedia で補っています。
> - **旧銀行**: 有価証券報告書の【沿革】に名前と日付が記載された旧銀行・無尽・貯蓄銀行は、戦前の小規模な吸収・買収も含めて収録しています（設立日が出典にないものは省略）。出典や note に名前があるが未収録の銀行は `scripts/find_unlisted.py` で一覧化できます。
>
> 誤りの指摘や追加を歓迎します。

### 有価証券報告書との照合

```sh
python scripts/edinet_history.py --years 2021-2026   # EDINET API から【沿革】を取得（要 API キー: EDINET_API_KEY）
python scripts/compare_edinet.py > report.md         # データとの突き合わせレポート
python scripts/find_unlisted.py > unlisted.md        # 出典・note に名前があるが未収録の銀行の一覧
python scripts/compare_fsa.py                        # 金融庁の銀行免許一覧と存続中の銀行の突き合わせ
```

## データ構造

データは `data/` 以下の YAML で管理しています。

### `data/banks.yaml` — 銀行マスタ

```yaml
- id: sanwa                 # 一意なID（英小文字・数字・ハイフン。後から変更しない）
  name: 三和銀行             # 当時の正式名称
  name_en: The Sanwa Bank   # 英語名（任意）
  type: city                # 種別（下表）
  founded: "1933-12-09"     # 設立日 YYYY / YYYY-MM / YYYY-MM-DD（文字列で。不明なら省略）
  dissolved: "2002-01-15"   # 消滅日（存続中なら省略）
  prefecture: 大阪府         # 本店所在地（任意）
  note: 補足                 # 任意
  sources: [https://ja.wikipedia.org/wiki/三和銀行]
```

| type | 種別 |
|---|---|
| `city` | 都市銀行 |
| `regional` | 地方銀行 |
| `regional2` | 第二地方銀行 |
| `trust` | 信託銀行 |
| `long_term` | 長期信用銀行 |
| `new` | 新形態銀行等（ネット銀行・流通系・ゆうちょ銀行など） |
| `special` | 特殊銀行・政府系（横浜正金・勧銀、日本政策投資銀行など） |
| `other` | その他（戦前の普通銀行、新形態銀行など） |

### `data/events.yaml` — 変遷イベント

```yaml
- date: "2002-01-15"
  type: merger
  from: [sanwa, tokai]
  to: [ufj]
  note: 補足（任意）
  sources: [https://...]
```

| type | 意味 |
|---|---|
| `merger` | 新設・対等合併（from が消え、to が生まれる） |
| `absorption` | 吸収合併（from が to に吸収され、to は存続） |
| `rename` | 商号変更 |
| `reorganization` | 分割・再編（複数 → 複数 など） |
| `transfer` | 事業譲渡（破綻行の受け皿など） |
| `failure` | 経営破綻・国有化（`to` は省略可） |

## ローカルでの確認

```sh
pip install pyyaml
python scripts/build.py          # 検証して docs/data.json を生成
python -m http.server -d docs    # http://localhost:8000 を開く
```

`python scripts/build.py --check` で検証のみ行えます（未定義ID・日付形式・設立日とイベント日の不一致などを検出）。

## 貢献のしかた

1. `data/banks.yaml` に銀行を、`data/events.yaml` にイベントを追加
2. `sources` に出典 URL を記載（有価証券報告書・公式の沿革を優先。出典のない項目は検証で警告されます）
3. `python scripts/build.py --check` が通ることを確認して Pull Request

Pull Request では GitHub Actions が自動でデータを検証します。`main` にマージされると GitHub Pages に自動で公開されます。

## 構成

```
data/banks.yaml          銀行マスタ
data/events.yaml         変遷イベント
scripts/build.py         検証 & docs/data.json 生成
docs/index.html          可視化ページ（D3.js）
.github/workflows/       検証・GitHub Pages デプロイ
```

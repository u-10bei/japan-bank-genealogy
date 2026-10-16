# 日本の銀行系譜図 (japan-bank-genealogy)

日本の銀行の **合併・統合・改称・再編・破綻** の変遷を、年表上の系譜図としてインタラクティブに可視化するプロジェクトです。

**▶ 系譜図を見る: https://u-10bei.github.io/japan-bank-genealogy/**

- 銀行ごとに設立〜消滅を横線で表示し、合併・改称などのイベントで前身と後継をつなぎます
- 前身・後継でつながる銀行を「系統」としてまとめ、系統ごとに見出し（現存行名・本店所在地・収録行数）を付けて表示します。系統の並び順は「規模順／本店所在地順（北から南）／業態順／起源が古い順」から選べます
- 系統の中では、後継行の上下に前身行を設立順に配置します
- 銀行名で検索、またはクリックすると、その銀行の前身・後継の系統全体をハイライトします
- Ctrl/⌘ + ホイール または ドラッグで年表を拡大・移動できます
- `#bank=<id>` を付けた URL で特定の銀行を選択した状態で開けます（例: `#bank=sanwa`）

> [!NOTE]
> 収録状況:
> - **地方銀行（現存62行）とその前身行**: 日本語版 Wikipedia の各行記事（沿革）を取得して照合したデータです。出典に日付がない場合は年・年月のみ、または設立日を省略しています。
> - **都市銀行・長信銀などの初期データ**: 出典未照合です（`sources` は対応する記事を示すのみ）。
> - 第二地方銀行の大半、信託銀行、戦前の銀行統合の多くは未収録です。
>
> Wikipedia は二次資料のため、有価証券報告書・各行公式の沿革などの一次資料での確認を進めています。誤りの指摘や追加を歓迎します。

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
| `special` | 特殊銀行（横浜正金・勧銀など） |
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
2. できるだけ `sources` に出典 URL を記載
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

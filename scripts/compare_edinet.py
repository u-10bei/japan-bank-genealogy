#!/usr/bin/env python3
"""sources/edinet/ の【沿革】抜粋と data/*.yaml を突き合わせ、差異のレポートを出力する。

使い方:
    python scripts/compare_edinet.py > report.md

出力するもの:
- 沿革の各項目（設立・合併・商号変更・営業譲受など系譜に関わるもの）について、
  言及された銀行のデータ上の日付と、沿革の日付を並べる
- 日付が一致しない、またはデータの方が粗い（年・年月のみ）ものに印を付ける
"""
from __future__ import annotations

import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "sources" / "edinet"
KEYWORDS = ("設立", "創立", "合併", "商号", "改称", "譲受", "譲渡", "転換", "分割", "承継", "統合", "開業", "営業開始")
BANKISH = ("銀行", "無尽", "相互", "国立")  # 関連会社の設立などを除く
ERAS = {"明治": 1867, "大正": 1911, "昭和": 1925, "平成": 1988, "令和": 2018}
DATE_RE = re.compile(
    r"^(?:(?P<era>明治|大正|昭和|平成|令和)(?P<ey>\d+|元)|(?P<y>\d{4}))年"
    r"(?:\s*\((?:明治|大正|昭和|平成|令和)?\s*(?:\d+|元)年\))?"
    r"(?:\s*(?P<m>\d{1,2})月(?:\s*(?P<d>\d{1,2})日)?)?"
    r"(?:\s*\((?:\d{4}|(?:明治|大正|昭和|平成|令和)(?:\d+|元))年[^)]*\))?\s*[|]?\s*(?P<rest>.*)$"
)


def norm(s: str) -> str:
    return unicodedata.normalize("NFKC", s)


def parse_history(text: str) -> list[tuple[str, str]]:
    """沿革テキスト → [(YYYY[-MM[-DD]], 記述)]"""
    items: list[tuple[str, str]] = []
    cur = None
    for raw in text.splitlines():
        if raw.startswith("#"):
            continue
        line = norm(raw).strip()
        m = DATE_RE.match(line)
        if m:
            if m["era"]:
                y = ERAS[m["era"]] + (1 if m["ey"] == "元" else int(m["ey"]))
            else:
                y = int(m["y"])
            d = f"{y:04d}"
            if m["m"]:
                d += f"-{int(m['m']):02d}"
                if m["d"]:
                    d += f"-{int(m['d']):02d}"
            cur = [d, m["rest"].strip(" |")]
            items.append(cur)
        elif cur is not None and line and line != "|":
            cur[1] = (cur[1] + " " + line.strip(" |")).strip()
    return [(d, t) for d, t in items if t]


def latest_files() -> list[Path]:
    by_filer: dict[str, Path] = {}
    for f in sorted(SRC_DIR.glob("*.txt")):
        by_filer[f.name.split("_")[0]] = f  # ファイル名は 提出日順に並ぶので最後が最新
    return list(by_filer.values())


def main() -> int:
    banks = yaml.safe_load(open(ROOT / "data/banks.yaml", encoding="utf-8"))
    events = yaml.safe_load(open(ROOT / "data/events.yaml", encoding="utf-8"))
    by_name: dict[str, list[dict]] = defaultdict(list)
    for b in banks:
        by_name[norm(b["name"]).split("（")[0]].append(b)
    names = sorted(by_name, key=len, reverse=True)
    ev_by_bank: dict[str, list[dict]] = defaultdict(list)
    for e in events:
        for bid in [*e["from"], *(e.get("to") or [])]:
            ev_by_bank[bid].append(e)

    out = ["# EDINET 有価証券報告書【沿革】との突き合わせ", ""]
    for f in latest_files():
        text = f.read_text(encoding="utf-8")
        header = dict(re.findall(r"^# (\S+): (.*)$", text, re.M))
        items = [(d, t) for d, t in parse_history(text)
                 if any(k in t for k in KEYWORDS) and any(k in t for k in BANKISH)]
        out.append(f"## {header.get('提出者', f.name)}")
        out.append(f"出典: `{f.relative_to(ROOT)}`（{header.get('書類', '')}）")
        out.append("")
        out.append("| 沿革の日付 | 沿革の記述 | 言及された銀行 | データ上の日付 | 判定 |")
        out.append("|---|---|---|---|---|")
        for d, t in items:
            t_clean = re.sub(r"株式会社|\(株\)", "", t)
            hits, rest = [], t_clean
            for n in names:
                if n in rest:
                    hits.append(n)
                    rest = rest.replace(n, "")
            cells = []
            verdict = ""
            for n in hits:
                for b in by_name[n]:
                    dates = {str(b.get("founded")), str(b.get("dissolved"))} | {str(e["date"]) for e in ev_by_bank[b["id"]]}
                    dates.discard("None")
                    same_year = sorted(x for x in dates if x[:4] == d[:4])
                    if not same_year:
                        continue
                    cells.append(f"{b['id']}: {', '.join(same_year)}")
                    if d in same_year:
                        verdict = verdict or "一致"
                    elif any(d.startswith(x) for x in same_year):
                        verdict = "詳細化可"
                    else:
                        verdict = "要確認"
            out.append(f"| {d} | {t.replace('|', '／')} | {' '.join(hits) or '-'} | {'<br>'.join(cells) or '-'} | {verdict or '未収録?'} |")
        out.append("")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())

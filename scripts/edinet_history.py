#!/usr/bin/env python3
"""EDINET API から銀行の有価証券報告書を探し、【沿革】を抜き出して保存する。

保存先: sources/edinet/<EDINETコード>_<提出日>_<書類番号>.txt
（一次資料の抜粋として、出典 URL・提出者・対象期間をヘッダーに記録する）

使い方:
    export EDINET_API_KEY=...        # API キー（プロキシ等でヘッダー注入済みなら不要）
    python scripts/edinet_history.py --years 2021-2026
    python scripts/edinet_history.py --from 2026-06-15 --to 2026-07-05

対象: 書類種別「有価証券報告書」(docTypeCode=120) のうち、提出者名に「銀行」を含むもの、
および提出者名が HOLDING_HINTS に当たり、沿革に「銀行」が現れるもの（銀行持株会社）。
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "sources" / "edinet"
API = "https://api.edinet-fsa.go.jp/api/v2"
# 銀行持株会社と思われる提出者名の手がかり（名称に「銀行」を含まない持株会社用）
HOLDING_HINTS = ("フィナンシャル", "ＦＧ", "FG", "ぎん", "銀", "プロクレア", "フィデア", "じもと", "トモニ", "池田泉州", "りそな")
SLEEP = 0.5  # API へのアクセス間隔（秒）


def api_get(path: str, **params) -> bytes:
    key = os.environ.get("EDINET_API_KEY")
    if key:
        params["Subscription-Key"] = key
    url = f"{API}/{path}?{urllib.parse.urlencode(params)}"
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                body = r.read()
            time.sleep(SLEEP)
            return body
        except OSError as e:
            if attempt == 3:
                raise
            print(f"  retry ({e})", file=sys.stderr)
            time.sleep(2 ** (attempt + 1))
    raise AssertionError


def list_reports(day: dt.date) -> list[dict]:
    d = json.loads(api_get("documents.json", date=day.isoformat(), type=2))
    if str(d.get("metadata", {}).get("status")) != "200":
        raise SystemExit(f"EDINET API error on {day}: {d}")
    out = []
    for r in d.get("results") or []:
        name = r.get("filerName") or ""
        if r.get("docTypeCode") != "120" or r.get("withdrawalStatus") != "0":
            continue
        if "信託受益証券" in (r.get("docDescription") or ""):
            continue
        if "銀行" in name or any(h in name for h in HOLDING_HINTS):
            out.append(r)
    return out


def extract_history(zip_bytes: bytes) -> str | None:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        for n in sorted(z.namelist()):
            if not (n.startswith("XBRL/PublicDoc/") and n.endswith(".htm")):
                continue
            src = z.read(n).decode("utf-8", errors="replace")
            m = re.search(r'name="jpcrp_cor:CompanyHistoryTextBlock"[^>]*>(.*?)</ix:nonNumeric>', src, re.S)
            if m:
                return to_text(m.group(1))
    return None


def to_text(fragment: str) -> str:
    body = re.sub(r"</(tr|p|div)>", "\n", fragment)
    body = re.sub(r"</t[dh]>", "\t", body)
    body = re.sub(r"<br\s*/?>", " ", body)
    text = html.unescape(re.sub(r"<[^>]+>", "", body))
    lines = []
    for line in text.splitlines():
        line = re.sub(r"[ 　\t]+", " ", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines) + "\n"


def daterange(a: dt.date, b: dt.date):
    while a <= b:
        yield a
        a += dt.timedelta(days=1)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--years", help="例: 2021-2026（各年 6/15〜7/5 を走査）")
    p.add_argument("--from", dest="date_from")
    p.add_argument("--to", dest="date_to")
    args = p.parse_args()

    days: list[dt.date] = []
    if args.years:
        y0, y1 = (int(x) for x in args.years.split("-"))
        for y in range(y0, y1 + 1):
            days += daterange(dt.date(y, 6, 15), dt.date(y, 7, 5))
    if args.date_from:
        days += daterange(dt.date.fromisoformat(args.date_from), dt.date.fromisoformat(args.date_to or args.date_from))
    today = dt.date.today()
    days = [d for d in days if d <= today]
    if not days:
        p.error("--years か --from/--to を指定してください")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    existing = {f.name.split("_")[-1].removesuffix(".txt") for f in OUT_DIR.glob("*.txt")}
    saved = skipped = 0
    for day in days:
        reports = list_reports(day)
        if reports:
            print(f"{day}: {len(reports)} 件", file=sys.stderr)
        for r in reports:
            doc_id = r["docID"]
            if doc_id in existing:
                continue
            text = extract_history(api_get(f"documents/{doc_id}", type=1))
            name = r["filerName"]
            if not text or ("銀行" not in name and "銀行" not in text):
                skipped += 1
                continue
            header = (
                f"# 出典: EDINET 有価証券報告書 【沿革】\n"
                f"# 提出者: {name} (EDINETコード {r['edinetCode']})\n"
                f"# 書類: {r['docDescription']}\n"
                f"# 書類番号: {doc_id} / 提出日時: {r['submitDateTime']}\n"
                f"# URL: https://disclosure2.edinet-fsa.go.jp/WZEK0040.aspx?{doc_id}\n\n"
            )
            fname = f"{r['edinetCode']}_{r['submitDateTime'][:10]}_{doc_id}.txt"
            (OUT_DIR / fname).write_text(header + text, encoding="utf-8")
            existing.add(doc_id)
            saved += 1
            print(f"  saved {fname} {name}", file=sys.stderr)
    print(f"保存 {saved} 件 / 対象外 {skipped} 件")
    return 0


if __name__ == "__main__":
    sys.exit(main())

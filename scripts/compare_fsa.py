#!/usr/bin/env python3
"""金融庁「銀行免許一覧」（sources/fsa/ginkou_menkyo.csv）と data/banks.yaml の存続中の銀行を突き合わせる。

- 免許一覧にあるのにデータにない（または消滅扱いになっている）銀行
- データでは存続中なのに免許一覧にない銀行（消滅・改称の反映漏れの可能性）

免許一覧の更新:
    curl -o ginkou.xlsx https://www.fsa.go.jp/menkyo/menkyoj/ginkou.xlsx
    （外国銀行支店を除いた行を sources/fsa/ginkou_menkyo.csv に保存）
"""
from __future__ import annotations

import csv
import re
import sys
import unicodedata
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def norm(name: str) -> str:
    return re.sub(r"株式会社|\s", "", unicodedata.normalize("NFKC", name))


def main() -> int:
    rows = list(csv.DictReader(open(ROOT / "sources/fsa/ginkou_menkyo.csv", encoding="utf-8")))
    banks = yaml.safe_load(open(ROOT / "data/banks.yaml", encoding="utf-8"))
    # 政府系金融機関（type: special）は銀行免許を持たないため対象外
    alive = {norm(b["name"]): b for b in banks if not b.get("dissolved") and b["type"] != "special"}
    fsa = {norm(r["name"]): r for r in rows}
    missing = [r for k, r in fsa.items() if k not in alive]
    extra = [b for k, b in alive.items() if k not in fsa]
    print(f"免許一覧 {len(fsa)} 行 / データの存続中 {len(alive)} 行")
    print(f"\n免許一覧にあってデータにない: {len(missing)}")
    for r in missing:
        print(f"  {r['category']}\t{r['name']}")
    print(f"\nデータで存続中だが免許一覧にない: {len(extra)}")
    for b in extra:
        print(f"  {b['id']}\t{b['name']}\t({b['type']})")
    return 1 if missing or extra else 0


if __name__ == "__main__":
    sys.exit(main())

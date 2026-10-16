#!/usr/bin/env python3
"""data/*.yaml を検証し、可視化用の docs/data.json を生成する。

使い方:
    python scripts/build.py           # 検証して docs/data.json を出力
    python scripts/build.py --check   # 検証のみ（CI用）
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUT_PATH = ROOT / "docs" / "data.json"

BANK_TYPES = {"city", "trust", "long_term", "regional", "regional2", "special", "other"}
EVENT_TYPES = {"merger", "absorption", "rename", "reorganization", "transfer", "failure"}
ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}(-(0[1-9]|1[0-2])(-(0[1-9]|[12]\d|3[01]))?)?$")
BANK_KEYS = {"id", "name", "name_en", "type", "founded", "dissolved", "prefecture", "note", "sources"}
EVENT_KEYS = {"date", "type", "from", "to", "note", "sources"}


def load_yaml(name: str) -> list:
    with open(DATA_DIR / name, encoding="utf-8") as f:
        data = yaml.safe_load(f) or []
    if not isinstance(data, list):
        raise SystemExit(f"{name}: トップレベルはリストである必要があります")
    return data


def date_key(d: str) -> str:
    """部分日付を比較用に正規化する（YYYY → YYYY-01-01）。"""
    parts = d.split("-")
    while len(parts) < 3:
        parts.append("01")
    return "-".join(parts)


def validate(banks: list, events: list) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    ids: dict[str, dict] = {}

    for i, b in enumerate(banks):
        where = f"banks.yaml[{i}] ({b.get('id', '?')})"
        if not isinstance(b, dict):
            errors.append(f"{where}: マッピングである必要があります")
            continue
        for k in set(b) - BANK_KEYS:
            errors.append(f"{where}: 未知のキー '{k}'")
        for k in ("id", "name", "type"):
            if not b.get(k):
                errors.append(f"{where}: '{k}' は必須です")
        bid = b.get("id")
        if bid:
            if not ID_RE.match(str(bid)):
                errors.append(f"{where}: id は英小文字・数字・ハイフンのみ")
            if bid in ids:
                errors.append(f"{where}: id が重複しています")
            ids[bid] = b
        if b.get("type") and b["type"] not in BANK_TYPES:
            errors.append(f"{where}: type '{b['type']}' は {sorted(BANK_TYPES)} のいずれか")
        for k in ("founded", "dissolved"):
            v = b.get(k)
            if v is not None and not DATE_RE.match(str(v)):
                errors.append(f"{where}: {k} '{v}' は YYYY / YYYY-MM / YYYY-MM-DD 形式（文字列で記述）")
        if not b.get("founded") and not b.get("dissolved"):
            errors.append(f"{where}: founded か dissolved の少なくとも一方が必要です")
        if b.get("founded") and b.get("dissolved") and DATE_RE.match(str(b["founded"])) and DATE_RE.match(str(b["dissolved"])):
            if date_key(str(b["dissolved"])) < date_key(str(b["founded"])):
                errors.append(f"{where}: dissolved が founded より前です")

    referenced: set[str] = set()
    for i, e in enumerate(events):
        n_errors = len(errors)
        where = f"events.yaml[{i}] ({e.get('date', '?')} {e.get('type', '?')})"
        if not isinstance(e, dict):
            errors.append(f"{where}: マッピングである必要があります")
            continue
        for k in set(e) - EVENT_KEYS:
            errors.append(f"{where}: 未知のキー '{k}'")
        if not e.get("date") or not DATE_RE.match(str(e["date"])):
            errors.append(f"{where}: date が不正です")
        if e.get("type") not in EVENT_TYPES:
            errors.append(f"{where}: type は {sorted(EVENT_TYPES)} のいずれか")
        src, dst = e.get("from") or [], e.get("to") or []
        if not src:
            errors.append(f"{where}: from は必須です")
        if not dst and e.get("type") != "failure":
            errors.append(f"{where}: to は必須です（failure 以外）")
        for bid in [*src, *dst]:
            referenced.add(bid)
            if bid not in ids:
                errors.append(f"{where}: 未定義の銀行ID '{bid}'")
        if len(errors) > n_errors:
            continue
        d = date_key(str(e["date"]))
        for bid in src:
            b = ids[bid]
            if b.get("founded") and date_key(str(b["founded"])) > d:
                warnings.append(f"{where}: '{bid}' の設立日より前のイベントです")
        for bid in dst:
            b = ids[bid]
            if e["type"] in ("merger", "rename", "reorganization") and str(b.get("founded")) != str(e["date"]) and bid not in src:
                warnings.append(f"{where}: '{bid}' の founded ({b['founded']}) がイベント日と一致しません")

    for bid in ids:
        if bid not in referenced and ids[bid].get("dissolved"):
            warnings.append(f"banks.yaml ({bid}): 消滅日があるのに関連イベントがありません")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="検証のみ行い、ファイルを出力しない")
    args = parser.parse_args()

    banks = load_yaml("banks.yaml")
    events = load_yaml("events.yaml")
    errors, warnings = validate(banks, events)
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    for e in errors:
        print(f"error: {e}", file=sys.stderr)
    if errors:
        print(f"\n{len(errors)} 件のエラー", file=sys.stderr)
        return 1

    print(f"OK: 銀行 {len(banks)} 件 / イベント {len(events)} 件 / 警告 {len(warnings)} 件")
    if args.check:
        return 0

    events_sorted = sorted(events, key=lambda e: date_key(str(e["date"])))
    out = {
        "banks": [{k: (str(v) if k in ("founded", "dissolved") else v) for k, v in b.items()} for b in banks],
        "events": [{**e, "date": str(e["date"]), "to": e.get("to") or []} for e in events_sorted],
    }
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {OUT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

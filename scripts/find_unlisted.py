#!/usr/bin/env python3
"""出典（有価証券報告書の沿革）やデータの note に名前が出てくるのに、
data/banks.yaml に項目がない銀行・無尽を洗い出し、系統ごとに一覧にする。

使い方:
    python scripts/find_unlisted.py > unlisted.md

名前の抽出は機械的なもの（「株式会社◯◯銀行」「◯◯銀行株式会社」「第◯国立銀行」、
区切り記号の直後の漢字・カナ名）なので、取りこぼしや誤検出がありうる。
"""
from __future__ import annotations

import collections
import glob
import re
import sys
import unicodedata
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
N = lambda s: unicodedata.normalize("NFKC", s)  # noqa: E731

NAME = r"[一-鿿゠-ヿA-Za-z0-9ー぀-ゟ・]{1,16}?(?:銀行|無尽|無盡)"
PATTERNS = [
    re.compile(r"株式会社(" + NAME + ")"),
    re.compile(r"(?<![一-鿿゠-ヿA-Za-z])([一-鿿゠-ヿA-Za-zー・]{1,14}?(?:銀行|無尽))株式会社"),
    re.compile(r"(第[一二三四五六七八九十百千〇]+国立銀行)"),
    re.compile(r"(?:^|[、。・（(「\s/：:と及並])([一-鿿゠-ヿー]{1,12}(?:銀行|無尽|無盡))"),
]
PREFIX = re.compile(r"^(株式会社|合名会社|合資会社|私盟会社|財団法人|保証有限責任会社|及び|および|から|が|を|と|同日|翌年|翌月|初代|現|旧・|旧|新・|本店・)")
NOT_A_NAME = re.compile(
    r"(会員|顧客|向け|ファン|利用者|サービス|法律|条例|金融庁|子会社|当社|当行|傘下|経由|商号|合併|転換|設立|施行|基づ|保有|"
    r"Wikipedia|法第|定める|株式移転|みらいバンク|ビューカード|及び|第[一二三]次|(?<!みんな)の)"
)
GENERIC = set(
    "銀行 普通銀行 相互銀行 地方銀行 都市銀行 国立銀行 日本銀行 貯蓄銀行 信託銀行 外国銀行 特殊銀行 長期信用銀行 第二地方銀行 "
    "新銀行 子銀行 存続銀行 大手銀行 責任銀行 私立銀行 承継銀行 日本承継銀行 無尽 相互無尽 殖産無尽 県内無尽 全国銀行 全国相互銀行 "
    "外国為替公認銀行 乙種外国為替公認銀行 外国為替銀行 外国為替専門銀行 外国為替コルレス銀行 コルレス包括承認銀行 コルレス包括契約銀行 "
    "外資系信託銀行 米国外国銀行 商業銀行 地域銀行 SBI地域銀行 戦後第一号銀行 ネット銀行 インターネット銀行 海外銀行 主力銀行 "
    "県是銀行 合同銀行 受皿銀行 沖縄県銀行 関連銀行".split()
)
# 現存するが、まだ収録対象にしていない銀行（新形態銀行・政府系など）
CURRENT_UNLISTED = set(
    "セブン銀行 ゆうちょ銀行 イオン銀行 ローソン銀行 住信SBIネット銀行 楽天銀行 ソニー銀行 オリックス銀行 UI銀行 みんなの銀行 "
    "GMOあおぞらネット銀行 SBI新生信託銀行 日本マスタートラスト信託銀行 日本政策投資銀行 国際協力銀行 欧州静岡銀行 中國信託商業銀行".split()
)


def plain(name: str) -> str:
    return re.sub(r"（.*?）|\(.*?\)", "", N(name)).replace("國", "国")


def extract(text: str) -> set[str]:
    out = set()
    t = N(text)
    for p in PATTERNS:
        for m in p.finditer(t):
            raw = m.group(1)
            # 「ビー・エヌ・ピー・パリバ信託銀行」のようなカナの中黒は分割しない
            parts = [raw] if re.search(r"[\u30a0-\u30ff]・[\u30a0-\u30ff]", raw) else raw.split("・")
            for part in parts:
                n = part
                for _ in range(3):
                    n = PREFIX.sub("", n)
                if re.search(r"(銀行|無尽|無盡)$", n) and len(n) >= 3 and n not in GENERIC and not NOT_A_NAME.search(n):
                    out.add(n)
    return out


def lineages(banks: list[dict], events: list[dict]) -> dict[str, str]:
    """銀行ID → 系統名（存続中の銀行名）。docs/index.html と同じく、一部の事業譲渡ではつながない。"""
    by_id = {b["id"]: b for b in banks}
    adj = collections.defaultdict(set)
    for e in events:
        if e["type"] == "failure":
            continue
        if e["type"] == "transfer":
            out = [x for x in events if set(x["from"]) & set(e["from"]) and x["type"] != "failure"]
            whole = all(by_id[f].get("dissolved") for f in e["from"]) and all(x["type"] == "transfer" for x in out) \
                and len({t for x in out for t in x.get("to") or []}) == 1
            if not whole:
                continue
        for f in e["from"]:
            for t in e.get("to") or []:
                if f != t:
                    adj[f].add(t)
                    adj[t].add(f)
    label: dict[str, str] = {}
    for start in by_id:
        if start in label:
            continue
        comp, stack = set(), [start]
        while stack:
            x = stack.pop()
            if x in comp:
                continue
            comp.add(x)
            stack += adj[x] - comp
        alive = sorted(by_id[x]["name"] for x in comp if not by_id[x].get("dissolved"))
        name = "・".join(alive) if alive else max((by_id[x] for x in comp), key=lambda b: str(b.get("dissolved")))["name"] + "（現存行なし）"
        for x in comp:
            label[x] = name
    return label


def main() -> int:
    banks = yaml.safe_load(open(ROOT / "data/banks.yaml", encoding="utf-8"))
    events = yaml.safe_load(open(ROOT / "data/events.yaml", encoding="utf-8"))
    known = {plain(b["name"]) for b in banks}
    lineage = lineages(banks, events)
    name_to_id = {plain(b["name"]): b["id"] for b in banks if not b.get("dissolved")}

    found: dict[str, set[str]] = collections.defaultdict(set)   # 名前 → 言及元（系統名）
    refs: dict[str, set[str]] = collections.defaultdict(set)    # 名前 → 言及元（具体的な出典）
    for b in banks:
        for n in extract(b.get("note") or ""):
            found[n].add(lineage[b["id"]]); refs[n].add(f"note: {b['id']}")
    for e in events:
        for n in extract(e.get("note") or ""):
            found[n].add(lineage[e["from"][0]]); refs[n].add(f"note: {e['date']} {e['type']}")
    for f in sorted(glob.glob(str(ROOT / "sources/edinet/*.txt"))):
        text = open(f, encoding="utf-8").read()
        filer = re.sub(r"株式会社|\s", "", N(re.search(r"# 提出者: (.*?) \(", text).group(1)))
        body = text.split("\n", 6)[-1]
        lin = lineage.get(name_to_id.get(plain(filer)), f"{filer}（持株会社等）")
        for n in extract(body):
            found[n].add(lin); refs[n].add(f"有報: {filer}")

    old = {n: v for n, v in found.items() if n not in known and plain(n) not in known and n not in CURRENT_UNLISTED}
    # 国立銀行時代の名称は、多くを後身の普通銀行と同じ項目にまとめて収録している（note に記載）
    national = {n: v for n, v in old.items() if n.endswith("国立銀行")}
    old = {n: v for n, v in old.items() if n not in national}
    cur = {n: v for n, v in found.items() if n in CURRENT_UNLISTED and n not in known}

    by_lineage: dict[str, list[str]] = collections.defaultdict(list)
    for n, lins in old.items():
        for lin in lins:
            by_lineage[lin].append(n)
    print("# 出典に名前があるが未収録の銀行")
    print()
    print(f"機械抽出のため誤検出・取りこぼしがありえます。旧銀行・無尽 {len(old)} 件、国立銀行時代の名称 {len(national)} 件、現存の未収録行 {len(cur)} 件。")
    print()
    print("## 旧銀行・無尽（系統別）")
    print()
    print("| 系統 | 未収録の旧銀行・無尽 | 件数 |")
    print("|---|---|---|")
    for lin in sorted(by_lineage, key=lambda k: (-len(by_lineage[k]), k)):
        names = sorted(set(by_lineage[lin]))
        print(f"| {lin} | {'、'.join(names)} | {len(names)} |")
    print()
    print("## 国立銀行時代の名称（後身の項目にまとめているものが多い）")
    print()
    print("、".join(sorted(national)))
    print()
    print("## 現存するが収録対象外の銀行")
    print()
    print("、".join(sorted(cur)))
    print()
    print("## 言及元の詳細")
    print()
    for n in sorted(old) + sorted(national):
        print(f"- {n}: {'; '.join(sorted(refs[n]))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

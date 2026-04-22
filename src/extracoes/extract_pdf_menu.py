"""Extrai itens de cardapio a partir de PDF e gera JSON.

Uso:
python extract_pdf_menu.py \
  --pdf arquivos/CardapioMidway.pdf \
  --restaurante Camaroes \
  --out data/camaroes_extraido.json
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from pypdf import PdfReader


HEADER_PRICE_RE = re.compile(
     r"^(?P<name>.+?)\s+(?P<price>(?:\d{1,4}(?:,\d{2})?(?:\s*\|\s*\d{1,4}(?:,\d{2})?)*|sob consulta))$",
    flags=re.IGNORECASE,
)

IGNORE_LINES_EXACT = {
    "valores expressos em reais (r$)",
    "individuais",
    "kids",
    "baby",
    "saladas",
    "acompanhamentos",
}

IGNORE_NAME_PREFIX = (
    "com ",
    "e ",
    "de ",
    "cervejas",
)


def normalize_spaces(text: str) -> str:
    text = text.replace("\r", "\n")
    text = text.replace("\u2011", "-")
    text = text.replace("\u2013", "-")
    text = text.replace("\u2014", "-")
    text = text.replace("\xa0", " ")
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", text)
    return text


def extract_lines(pdf_path: Path) -> list[str]:
    reader = PdfReader(str(pdf_path))
    chunks: list[str] = []
    for page in reader.pages:
        chunks.append(page.extract_text() or "")

    text = normalize_spaces("\n".join(chunks))
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.split("\n")]
    return [ln for ln in lines if ln]


def is_probably_heading(line: str) -> bool:
    low = line.lower().strip()
    if low in IGNORE_LINES_EXACT:
        return True
    if len(low) <= 2:
        return True
    if not any(ch.isalpha() for ch in low):
        return True
    return False


def parse_menu(lines: list[str], restaurante: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    current: dict[str, str] | None = None

    for line in lines:
        match = HEADER_PRICE_RE.match(line)
        if match:
            name = match.group("name").strip()
            name_low = name.lower()

            if any(name_low.startswith(prefix) for prefix in IGNORE_NAME_PREFIX):
                continue
            if len(name) < 3:
                continue

            if current is not None:
                current["descricao"] = current["descricao"].strip()
                items.append(current)

            current = {
                "restaurante": restaurante,
                "prato": name,
                "descricao": "",
                "preco": match.group("price").strip(),
            }
            continue

        if current is None:
            continue

        if is_probably_heading(line):
            continue

        # Evita anexar linhas de preco isoladas como descricao.
        if re.fullmatch(r"\d{1,4}(?:\s*\|\s*\d{1,4})*", line):
            continue

        if current["descricao"]:
            current["descricao"] += " " + line
        else:
            current["descricao"] = line

    if current is not None:
        current["descricao"] = current["descricao"].strip()
        items.append(current)

    # Dedupe por prato+descricao+preco
    unique: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in items:
        key = (
            row["prato"].strip().lower(),
            row["descricao"].strip().lower(),
            row["preco"].strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)

    return unique


def main() -> None:
    parser = argparse.ArgumentParser(description="Extrator de cardapio em PDF")
    parser.add_argument("--pdf", type=Path, required=True, help="Arquivo PDF do cardapio")
    parser.add_argument("--restaurante", required=True, help="Nome do restaurante")
    parser.add_argument("--out", type=Path, required=True, help="JSON de saida")
    args = parser.parse_args()

    lines = extract_lines(args.pdf)
    menu = parse_menu(lines, args.restaurante)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(menu, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Linhas extraidas: {len(lines)}")
    print(f"Itens detectados: {len(menu)}")
    print(f"Arquivo gerado: {args.out}")


if __name__ == "__main__":
    main()

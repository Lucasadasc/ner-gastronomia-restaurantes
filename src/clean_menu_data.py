"""Limpa cardapio extraido para uso em analise de grafos.

Regras:
1) Remove itens de bebidas/vinhos/coqueteis
2) Remove linhas de alergeno/rotulo (ex: Gluten, Lactose, Ovo)
3) Remove duplicados por prato+descricao normalizados
4) Mantem formato final: restaurante, prato, descricao

Uso:
python src/clean_menu_data.py --in assets/data/coco_bambu_extraido.json --out assets/data/coco_bambu.json
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path


EXCLUDED_NAME_EXACT = {
    "gluten",
    "lactose",
    "ovo",
    "vegetariano",
    "vegano",
    "couvert",
    "chas",
    "cha",
}

EXCLUDED_KEYWORDS = {
    "vinho",
    "espumante",
    "cerveja",
    "whisky",
    "vodka",
    "gin",
    "rum",
    "tequila",
    "licor",
    "drink",
    "coquetel",
    "cocktail",
    "caipirinha",
    "suco",
    "refrigerante",
    "agua",
    "energetico",
    "chopp",
    "rose",
    "tinto",
    "branco",
    "sauvignon",
    "chardonnay",
    "merlot",
    "cabernet",
    "malbec",
    "kids",
    "baby",
    "infantil",
    "petit poti",
}

EXCLUDED_SINGLE_WORD_NOISE = {
    "caja",
    "manga",
    "uxmal",
    "caipirinha",
    "caipiroska",
    "mojito",
    "spritz",
}


def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def should_exclude(prato: str, descricao: str) -> bool:
    prato_norm = normalize_text(prato)
    desc_norm = normalize_text(descricao)
    full = f"{prato_norm} {desc_norm}"

    if prato_norm in EXCLUDED_NAME_EXACT:
        return True

    if re.match(r"^(com|de|e)\b", prato_norm):
        return True

    if prato_norm in EXCLUDED_SINGLE_WORD_NOISE:
        return True

    # Remove itens de nome muito fraco (geralmente ruído de extração)
    # quando a descrição não ajuda a identificar o prato.
    if len(prato_norm.split()) == 1 and len(desc_norm) < 12:
        return True

    return any(keyword in full for keyword in EXCLUDED_KEYWORDS)


def clean_records(raw_records: list[dict]) -> list[dict[str, str]]:
    cleaned: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for row in raw_records:
        restaurante = str(row.get("restaurante", "")).strip()
        prato = str(row.get("prato", "")).strip()
        descricao = str(row.get("descricao", "")).strip()

        if not prato:
            continue
        if should_exclude(prato, descricao):
            continue

        key = (normalize_text(prato), normalize_text(descricao))
        if key in seen:
            continue
        seen.add(key)

        cleaned.append(
            {
                "restaurante": restaurante,
                "prato": prato,
                "descricao": descricao,
            }
        )

    return cleaned


def main() -> None:
    parser = argparse.ArgumentParser(description="Limpeza de cardapio extraido")
    parser.add_argument("--in", dest="input_file", type=Path, required=True, help="JSON de entrada")
    parser.add_argument("--out", dest="output_file", type=Path, required=True, help="JSON limpo de saida")
    args = parser.parse_args()

    raw = json.loads(args.input_file.read_text(encoding="utf-8"))
    cleaned = clean_records(raw)

    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    args.output_file.write_text(json.dumps(cleaned, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Itens entrada: {len(raw)}")
    print(f"Itens apos limpeza: {len(cleaned)}")
    print(f"Arquivo gerado: {args.output_file}")


if __name__ == "__main__":
    main()

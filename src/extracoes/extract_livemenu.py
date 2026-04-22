"""Extrai itens de cardapio de uma pagina LiveMenu (Next.js) para JSON.

Uso:
python extract_livemenu.py \
  --url "https://beta.livemenu.app/pt/menu/611ec1ce0304be001207f64e?v=..." \
  --venue-id "611ec1ce0304be001207f64e" \
  --restaurante "Coco Bambu" \
  --out "data/coco_bambu.json"
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
from pathlib import Path


def fetch_html(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            )
        },
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read().decode("utf-8", errors="ignore")


def _unescape_field(value: str) -> str:
    # Converte sequencias JSON escapadas como \" e \u00e7 para texto normal.
    try:
        decoded = json.loads(f'"{value}"')
    except Exception:
        decoded = value

    # Corrige casos comuns de mojibake (ex: GlÃºten -> Glúten).
    if "Ã" in decoded or "Â" in decoded:
        try:
            decoded = decoded.encode("latin1").decode("utf-8")
        except Exception:
            pass

    return decoded


def extract_items(html: str, venue_id: str) -> list[dict[str, str]]:
    venue = re.escape(venue_id)

    # Captura nome e descricao do item em blocos do mesmo venue.
    # O payload vem como string JSON escapada no HTML (\"campo\":\"valor\").
    pattern = re.compile(
        rf'\\"venueId\\":\\"{venue}\\".*?'
        rf'\\"name\\":\\"(?P<name>.*?)\\".*?'
        rf'\\"description\\":\\"(?P<description>.*?)\\".*?'
        rf'\\"priceContent\\":\[(?P<price_block>.*?)\]',
        flags=re.DOTALL,
    )

    results: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()

    for match in pattern.finditer(html):
        name_raw = match.group("name")
        desc_raw = match.group("description")
        price_block = match.group("price_block")

        price_match = re.search(r'\\"price\\":\\"(.*?)\\"', price_block)
        price = _unescape_field(price_match.group(1)) if price_match else ""

        name = _unescape_field(name_raw).strip()
        description = _unescape_field(desc_raw).strip()

        # Ignora placeholders e entradas vazias.
        if not name or name == "$undefined":
            continue
        if description == "$undefined":
            description = ""

        key = (name, description, price)
        if key in seen:
            continue
        seen.add(key)

        results.append(
            {
                "prato": name,
                "descricao": description,
                "preco": price,
            }
        )

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Extrator de cardapio da LiveMenu")
    parser.add_argument("--url", required=True, help="URL publica do cardapio")
    parser.add_argument("--venue-id", required=True, help="Venue ID presente na URL")
    parser.add_argument("--restaurante", required=True, help="Nome do restaurante")
    parser.add_argument("--out", type=Path, required=True, help="Arquivo JSON de saida")
    args = parser.parse_args()

    html = fetch_html(args.url)
    items = extract_items(html, args.venue_id)

    output = [
        {
            "restaurante": args.restaurante,
            "prato": row["prato"],
            "descricao": row["descricao"],
            "preco": row["preco"],
        }
        for row in items
    ]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Itens extraidos: {len(output)}")
    print(f"Arquivo gerado: {args.out}")


if __name__ == "__main__":
    main()

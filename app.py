"""Trabalho 01 - Analise de cardapios com NER customizado e Teoria de Grafos.

Pipeline:
1) Leitura dos cardapios em JSON
2) Extracao de entidades gastronomicas por regras
3) Construcao de grafo de co-ocorrencia por restaurante
4) Calculo de metricas estruturais
5) Comparacao entre grafos e semelhanca entre pratos
"""

from __future__ import annotations

import argparse  # o argparse é usado para facilitar a execução do script com diferentes parâmetros, como arquivos de entrada e opções de filtragem. Ele permite que o usuário especifique os caminhos dos arquivos JSON dos cardápios, a pasta de saída para as figuras, e os critérios de filtragem para os pratos analisados.
import itertools  # o itertools é usado para gerar combinações de entidades para criar as arestas do grafo. Ele facilita a criação de pares de entidades que co-ocorrem em um mesmo prato, permitindo a construção do grafo de co-ocorrência.
import json
import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import networkx as nx

try:
    from pyvis.network import Network
except ModuleNotFoundError:
    Network = None

from src.constants import (
    ACOMPANHAMENTO_HINTS,
    ACTIVE_ENTITY_LEXICON,
    AUTO_EXCLUDED_KEYWORDS,
    AUTO_EXCLUDED_SINGLE_TERMS,
    AUTO_EXCLUDED_TERMS,
    AUTO_STOPWORDS,
    MOLHO_TECNICA_HINTS,
)


@dataclass
class MenuItem:
    restaurante: str
    prato: str
    descricao: str


def normalize_text(text: str) -> str:
    text = text.lower()
    text = "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_candidate_terms(text: str, max_ngram: int = 3) -> set[str]:
    tokens = [
        token
        for token in normalize_text(text).split()
        if len(token) >= 3 and token not in AUTO_STOPWORDS and not token.isdigit()
    ]

    terms: set[str] = set()
    for n in range(1, max_ngram + 1):
        for i in range(0, len(tokens) - n + 1):
            term = " ".join(tokens[i : i + n])
            if term in AUTO_EXCLUDED_TERMS:
                continue
            if term_is_excluded(term):
                continue
            terms.add(term)

    return terms


def infer_category_from_term(term: str) -> str:
    term_parts = set(term.split())

    if "molho" in term_parts or term_parts.intersection(MOLHO_TECNICA_HINTS):
        return "MOLHO_TECNICA"
    if term_parts.intersection(ACOMPANHAMENTO_HINTS):
        return "ACOMPANHAMENTO"
    return "INGREDIENTE"


def term_is_excluded(term: str) -> bool:
    parts = set(term.split())
    if parts.intersection(AUTO_EXCLUDED_SINGLE_TERMS):
        return True
    return any(keyword in term for keyword in AUTO_EXCLUDED_KEYWORDS)


def item_is_excluded(prato: str, descricao: str) -> bool:
    full = normalize_text(f"{prato} {descricao}")
    if not full:
        return True
    return any(keyword in full for keyword in AUTO_EXCLUDED_KEYWORDS)


def build_expanded_lexicon(
    menu_items: list[MenuItem], min_term_freq: int = 3
) -> tuple[dict[str, list[str]], dict[str, int]]:
    expanded = {
        category: list(terms) for category, terms in ACTIVE_ENTITY_LEXICON.items()
    }
    existing_terms = {
        normalize_text(term) for terms in expanded.values() for term in terms
    }

    counts: Counter[str] = Counter()
    for item in menu_items:
        combined_text = f"{item.prato} {item.descricao}"
        for term in extract_candidate_terms(combined_text):
            counts[term] += 1

    added_by_category = {
        "INGREDIENTE": 0,
        "ACOMPANHAMENTO": 0,
        "MOLHO_TECNICA": 0,
    }

    for term, freq in counts.items():
        if freq < min_term_freq or term in existing_terms:
            continue
        if term_is_excluded(term):
            continue

        category = infer_category_from_term(term)
        expanded[category].append(term)
        existing_terms.add(term)
        added_by_category[category] += 1

    for category in expanded:
        expanded[category] = sorted(set(expanded[category]))

    return expanded, added_by_category


def load_menu(path: Path) -> list[MenuItem]:
    data = json.loads(path.read_text(encoding="utf-8"))
    items: list[MenuItem] = []
    for row in data:
        restaurante = str(row.get("restaurante", "")).strip()
        prato = str(row.get("prato", "")).strip()
        descricao = str(row.get("descricao", "")).strip()
        if not prato:
            continue
        items.append(
            MenuItem(
                restaurante=restaurante,
                prato=prato,
                descricao=descricao,
            )
        )
    return items


def extract_entities(prato: str, descricao: str) -> dict[str, set[str]]:
    text = f"{prato} {descricao}"
    norm = normalize_text(text)

    entities: dict[str, set[str]] = {
        "PRATO": {normalize_text(prato)},
        "INGREDIENTE": set(),
        "ACOMPANHAMENTO": set(),
        "MOLHO_TECNICA": set(),
    }

    for category, terms in ACTIVE_ENTITY_LEXICON.items():
        for term in terms:
            tnorm = normalize_text(term)
            if f" {tnorm} " in f" {norm} ":
                entities[category].add(tnorm)

    return entities


def merged_non_prato_entities(item: MenuItem) -> set[str]:
    entities = extract_entities(item.prato, item.descricao)
    merged = (
        set(entities["INGREDIENTE"])
        | set(entities["ACOMPANHAMENTO"])
        | set(entities["MOLHO_TECNICA"])
    )
    return merged


def filter_low_information_items(
    menu_items: list[MenuItem], min_non_prato_entities: int = 2
) -> tuple[list[MenuItem], int]:
    filtered: list[MenuItem] = []
    dropped = 0
    for item in menu_items:
        if len(merged_non_prato_entities(item)) >= min_non_prato_entities:
            filtered.append(item)
        else:
            dropped += 1
    return filtered, dropped


def build_graph(
    menu_items: list[MenuItem],
    include_prato_nodes: bool = False,
    min_non_prato_entities: int = 2,
) -> nx.Graph:
    graph = nx.Graph()
    valid_items, _ = filter_low_information_items(
        menu_items, min_non_prato_entities=min_non_prato_entities
    )

    for item in valid_items:
        entities = extract_entities(item.prato, item.descricao)
        if include_prato_nodes:
            all_entities = set().union(*entities.values())
        else:
            all_entities = merged_non_prato_entities(item)

        for ent in all_entities:
            if graph.has_node(ent):
                graph.nodes[ent]["count"] += 1
            else:
                graph.add_node(ent, count=1)

        for u, v in itertools.combinations(sorted(all_entities), 2):
            if graph.has_edge(u, v):
                graph[u][v]["weight"] += 1
            else:
                graph.add_edge(u, v, weight=1)

    return graph


def build_core_graph(
    graph: nx.Graph, min_node_count: int = 2, min_edge_weight: int = 2
) -> nx.Graph:
    core = nx.Graph()
    for u, v, data in graph.edges(data=True):
        w = int(data.get("weight", 1))
        if w < min_edge_weight:
            continue
        u_count = int(graph.nodes[u].get("count", 1))
        v_count = int(graph.nodes[v].get("count", 1))
        if u_count < min_node_count or v_count < min_node_count:
            continue
        core.add_node(u, **graph.nodes[u])
        core.add_node(v, **graph.nodes[v])
        core.add_edge(u, v, weight=w)

    if core.number_of_nodes() == 0:
        return graph.copy()

    largest = max(nx.connected_components(core), key=len)
    return core.subgraph(largest).copy()


def build_summary_graph(
    graph: nx.Graph, top_nodes: int = 120, min_edge_weight: int = 2
) -> nx.Graph:
    if graph.number_of_nodes() == 0 or top_nodes <= 0:
        return nx.Graph()

    ranked_nodes = sorted(
        graph.nodes(data=True),
        key=lambda row: int(row[1].get("count", 1)),
        reverse=True,
    )
    selected_nodes = {name for name, _ in ranked_nodes[:top_nodes]}
    summary = graph.subgraph(selected_nodes).copy()

    if min_edge_weight > 1:
        weak_edges = [
            (u, v)
            for u, v, data in summary.edges(data=True)
            if int(data.get("weight", 1)) < min_edge_weight
        ]
        summary.remove_edges_from(weak_edges)

    isolated = list(nx.isolates(summary))
    if isolated:
        summary.remove_nodes_from(isolated)

    if summary.number_of_nodes() == 0:
        return graph.subgraph(selected_nodes).copy()

    largest = max(nx.connected_components(summary), key=len)
    return summary.subgraph(largest).copy()


def graph_metrics(graph: nx.Graph) -> dict[str, float]:
    if graph.number_of_nodes() == 0:
        return {
            "nodes": 0,
            "edges": 0,
            "density": 0.0,
            "avg_clustering": 0.0,
            "components": 0,
            "largest_component_size": 0,
        }

    components = list(nx.connected_components(graph))
    largest_size = max(len(c) for c in components)
    return {
        "nodes": float(graph.number_of_nodes()),
        "edges": float(graph.number_of_edges()),
        "density": float(nx.density(graph)),
        "avg_clustering": float(nx.average_clustering(graph)),
        "components": float(nx.number_connected_components(graph)),
        "largest_component_size": float(largest_size),
    }


def weighted_edge_vector(graph: nx.Graph) -> dict[tuple[str, str], float]:
    result: dict[tuple[str, str], float] = {}
    for u, v, data in graph.edges(data=True):
        key = tuple(sorted((u, v)))
        result[key] = float(data.get("weight", 1.0))
    return result


def cosine_similarity_sparse(
    vector_a: dict[tuple[str, str], float], vector_b: dict[tuple[str, str], float]
) -> float:
    all_keys = set(vector_a) | set(vector_b)
    if not all_keys:
        return 0.0

    dot = sum(vector_a.get(k, 0.0) * vector_b.get(k, 0.0) for k in all_keys)
    norm_a = math.sqrt(sum(v * v for v in vector_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vector_b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def compare_graphs(graph_a: nx.Graph, graph_b: nx.Graph) -> dict[str, float]:
    nodes_a = set(graph_a.nodes)
    nodes_b = set(graph_b.nodes)
    inter_nodes = nodes_a & nodes_b
    union_nodes = nodes_a | nodes_b

    edges_a = set(tuple(sorted((u, v))) for u, v in graph_a.edges())
    edges_b = set(tuple(sorted((u, v))) for u, v in graph_b.edges())
    inter_edges = edges_a & edges_b
    union_edges = edges_a | edges_b

    jaccard_nodes = len(inter_nodes) / len(union_nodes) if union_nodes else 0.0
    jaccard_edges = len(inter_edges) / len(union_edges) if union_edges else 0.0
    cosine_weighted = cosine_similarity_sparse(
        weighted_edge_vector(graph_a), weighted_edge_vector(graph_b)
    )

    return {
        "jaccard_nodes": jaccard_nodes,
        "jaccard_edges": jaccard_edges,
        "cosine_weighted_edges": cosine_weighted,
        "shared_nodes": float(len(inter_nodes)),
        "shared_edges": float(len(inter_edges)),
    }


def dish_entities_set(item: MenuItem) -> set[str]:
    return merged_non_prato_entities(item)


def compare_dishes(
    menu_a: list[MenuItem],
    menu_b: list[MenuItem],
    top_k: int = 5,
    min_entities_per_dish: int = 2,
) -> list[tuple[str, str, float]]:
    scores: list[tuple[str, str, float]] = []
    for dish_a in menu_a:
        set_a = dish_entities_set(dish_a)
        if len(set_a) < min_entities_per_dish:
            continue
        for dish_b in menu_b:
            set_b = dish_entities_set(dish_b)
            if len(set_b) < min_entities_per_dish:
                continue
            union = set_a | set_b
            score = (len(set_a & set_b) / len(union)) if union else 0.0
            scores.append((dish_a.prato, dish_b.prato, score))

    scores.sort(key=lambda x: x[2], reverse=True)
    return scores[:top_k]


def plot_graph_interactive(graph: nx.Graph, title: str, output_file: Path) -> bool:
    if Network is None:
        return False

    net = Network(
        height="800px",
        width="100%",
        bgcolor="#ffffff",
        font_color="#1f2937",
    )
    net.barnes_hut(
        gravity=-2400,
        central_gravity=0.2,
        spring_length=140,
        spring_strength=0.03,
        damping=0.09,
    )

    for node, data in graph.nodes(data=True):
        count = int(data.get("count", 1))
        size = 12 + min(count, 18)
        net.add_node(
            node,
            label=str(node),
            title=f"{node}<br>Frequencia: {count}",
            value=size,
        )

    for u, v, data in graph.edges(data=True):
        weight = int(data.get("weight", 1))
        net.add_edge(
            u,
            v,
            value=weight,
            width=max(1, min(weight, 8)),
            title=f"Co-ocorrencias: {weight}",
        )

    net.toggle_physics(True)
    net.set_options(
        """
        var options = {
          "interaction": {
            "hover": true,
            "tooltipDelay": 180,
            "navigationButtons": true,
            "keyboard": true
          },
          "edges": {
            "smooth": false,
            "color": {
              "inherit": true
            }
          }
        }
        """
    )

    output_file.parent.mkdir(parents=True, exist_ok=True)
    net.write_html(str(output_file), notebook=False, open_browser=False)
    return True


def print_metrics(label: str, metrics: dict[str, float]) -> None:
    print(f"\n=== {label} ===")
    print(f"Nos: {int(metrics['nodes'])}")
    print(f"Arestas: {int(metrics['edges'])}")
    print(f"Densidade: {metrics['density']:.4f}")
    print(f"Componentes conectados: {int(metrics['components'])}")
    print(f"Maior componente: {int(metrics['largest_component_size'])}")


def top_nodes_by_count(graph: nx.Graph, top_k: int = 20) -> list[tuple[str, int]]:
    ranked = sorted(
        (
            (str(node), int(data.get("count", 1)))
            for node, data in graph.nodes(data=True)
        ),
        key=lambda row: row[1],
        reverse=True,
    )
    return ranked[:top_k]


def print_graph_diagnostics(
    label: str,
    graph: nx.Graph,
    dropped_noise: int,
    dropped_low_info: int,
    top_k: int = 20,
) -> None:
    print(f"\n=== Diagnostico - {label} ===")
    print(f"Nos unicos no grafo: {graph.number_of_nodes()}")
    print(
        f"Descartes por filtro: ruido/bebidas={dropped_noise}, baixa-informacao(min-entidades)={dropped_low_info}"
    )

    top_nodes = top_nodes_by_count(graph, top_k=top_k)
    print(f"Top {len(top_nodes)} nos por frequencia:")
    for node, count in top_nodes:
        print(f"- {node}: {count}")


def main() -> None:
    global ACTIVE_ENTITY_LEXICON

    parser = argparse.ArgumentParser(
        description="Analise de semelhanca estrutural entre cardapios com grafos de co-ocorrencia"
    )
    parser.add_argument(
        "--camaroes",
        type=Path,
        default=Path("assets/data/camaroes_extraido.json"),
        help="Arquivo JSON do cardapio Camaroes",
    )
    parser.add_argument(
        "--coco",
        type=Path,
        default=Path("assets/data/coco_bambu_extraido.json"),
        help="Arquivo JSON do cardapio Coco Bambu",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs"),
        help="Pasta de saida para figuras",
    )
    parser.add_argument(
        "--min-entities",
        type=int,
        default=2,
        help="Minimo de entidades nao-PRATO para manter um prato na analise",
    )
    parser.add_argument(
        "--core-node-count",
        type=int,
        default=2,
        help="Minimo de frequencia do no para visualizacao do grafo central",
    )
    parser.add_argument(
        "--core-edge-weight",
        type=int,
        default=2,
        help="Minimo de peso de aresta para visualizacao do grafo central",
    )
    parser.add_argument(
        "--auto-expand-lexicon",
        action="store_true",
        help="Expande o dicionario de entidades com termos frequentes dos cardapios",
    )
    parser.add_argument(
        "--auto-min-freq",
        type=int,
        default=3,
        help="Frequencia minima para adicionar termo na expansao automatica",
    )
    parser.add_argument(
        "--summary-top-nodes",
        type=int,
        default=120,
        help="Quantidade maxima de nos no grafo resumo independente",
    )
    parser.add_argument(
        "--summary-min-edge-weight",
        type=int,
        default=2,
        help="Peso minimo de aresta no grafo resumo independente",
    )
    args = parser.parse_args()

    menu_camaroes = load_menu(args.camaroes)
    menu_coco = load_menu(args.coco)

    menu_camaroes_raw_count = len(menu_camaroes)
    menu_coco_raw_count = len(menu_coco)
    menu_camaroes = [
        item
        for item in menu_camaroes
        if not item_is_excluded(item.prato, item.descricao)
    ]
    menu_coco = [
        item for item in menu_coco if not item_is_excluded(item.prato, item.descricao)
    ]
    dropped_noise_camaroes = menu_camaroes_raw_count - len(menu_camaroes)
    dropped_noise_coco = menu_coco_raw_count - len(menu_coco)

    ACTIVE_ENTITY_LEXICON = {
        category: list(terms) for category, terms in ACTIVE_ENTITY_LEXICON.items()
    }
    if args.auto_expand_lexicon:
        ACTIVE_ENTITY_LEXICON, added_by_category = build_expanded_lexicon(
            menu_camaroes + menu_coco,
            min_term_freq=args.auto_min_freq,
        )
        total_added = sum(added_by_category.values())
        print("\n=== Lexico de Entidades ===")
        print(
            f"Expansao automatica ativada (freq minima={args.auto_min_freq}). Novos termos: {total_added}"
        )
        print(
            "Distribuicao: "
            f"INGREDIENTE={added_by_category['INGREDIENTE']}, "
            f"ACOMPANHAMENTO={added_by_category['ACOMPANHAMENTO']}, "
            f"MOLHO_TECNICA={added_by_category['MOLHO_TECNICA']}"
        )

    menu_camaroes_filtered, dropped_camaroes = filter_low_information_items(
        menu_camaroes, min_non_prato_entities=args.min_entities
    )
    menu_coco_filtered, dropped_coco = filter_low_information_items(
        menu_coco, min_non_prato_entities=args.min_entities
    )

    graph_camaroes = build_graph(
        menu_camaroes_filtered,
        include_prato_nodes=False,
        min_non_prato_entities=args.min_entities,
    )
    graph_coco = build_graph(
        menu_coco_filtered,
        include_prato_nodes=False,
        min_non_prato_entities=args.min_entities,
    )

    graph_camaroes_core = build_core_graph(
        graph_camaroes,
        min_node_count=args.core_node_count,
        min_edge_weight=args.core_edge_weight,
    )
    graph_coco_core = build_core_graph(
        graph_coco,
        min_node_count=args.core_node_count,
        min_edge_weight=args.core_edge_weight,
    )

    metrics_camaroes = graph_metrics(graph_camaroes)
    metrics_coco = graph_metrics(graph_coco)
    metrics_compare = compare_graphs(graph_camaroes, graph_coco)

    print_metrics("Camaroes", metrics_camaroes)
    print_metrics("Coco Bambu", metrics_coco)
    print("\n=== Qualidade da Base ===")
    print(
        f"Camaroes: {len(menu_camaroes_filtered)} pratos usados, {dropped_noise_camaroes + dropped_camaroes} descartados"
    )
    print(
        f"Coco Bambu: {len(menu_coco_filtered)} pratos usados, {dropped_noise_coco + dropped_coco} descartados"
    )
    print_graph_diagnostics(
        "Camaroes",
        graph_camaroes,
        dropped_noise=dropped_noise_camaroes,
        dropped_low_info=dropped_camaroes,
        top_k=20,
    )
    print_graph_diagnostics(
        "Coco Bambu",
        graph_coco,
        dropped_noise=dropped_noise_coco,
        dropped_low_info=dropped_coco,
        top_k=20,
    )

    print("\n=== Similaridade entre Grafos ===")
    print(f"Jaccard de nos: {metrics_compare['jaccard_nodes']:.4f}")
    print(f"Jaccard de arestas: {metrics_compare['jaccard_edges']:.4f}")
    print(
        f"Cosseno ponderado (arestas): {metrics_compare['cosine_weighted_edges']:.4f}"
    )
    print(f"Nos compartilhados: {int(metrics_compare['shared_nodes'])}")
    print(f"Arestas compartilhadas: {int(metrics_compare['shared_edges'])}")

    print("\n=== Pratos mais semelhantes ===")
    for prato_a, prato_b, score in compare_dishes(
        menu_camaroes_filtered,
        menu_coco_filtered,
        min_entities_per_dish=args.min_entities,
    ):
        print(f"{prato_a}  <->  {prato_b} | Jaccard: {score:.4f}")

    graph_camaroes_summary = build_summary_graph(
        graph_camaroes,
        top_nodes=args.summary_top_nodes,
        min_edge_weight=args.summary_min_edge_weight,
    )
    graph_coco_summary = build_summary_graph(
        graph_coco,
        top_nodes=args.summary_top_nodes,
        min_edge_weight=args.summary_min_edge_weight,
    )

    interactive_outputs: list[Path] = []
    if plot_graph_interactive(
        graph_camaroes_core,
        "Grafo Interativo (Nucleo) - Camaroes",
        args.output / "grafo_camaroes.html",
    ):
        interactive_outputs.append(args.output / "grafo_camaroes.html")
    if plot_graph_interactive(
        graph_coco_core,
        "Grafo Interativo (Nucleo) - Coco Bambu",
        args.output / "grafo_coco_bambu.html",
    ):
        interactive_outputs.append(args.output / "grafo_coco_bambu.html")
    if plot_graph_interactive(
        graph_camaroes_summary,
        "Grafo Interativo Resumo - Camaroes",
        args.output / "grafo_camaroes_resumo.html",
    ):
        interactive_outputs.append(args.output / "grafo_camaroes_resumo.html")
    if plot_graph_interactive(
        graph_coco_summary,
        "Grafo Interativo Resumo - Coco Bambu",
        args.output / "grafo_coco_bambu_resumo.html",
    ):
        interactive_outputs.append(args.output / "grafo_coco_bambu_resumo.html")

    print("\nArquivos de visualizacao gerados em:")
    if interactive_outputs:
        print("\nVisualizacoes interativas (PyVis) geradas em:")
        for path in interactive_outputs:
            print(f"- {path}")
    else:
        print(
            "\nPyVis nao encontrado no ambiente. As visualizacoes interativas nao foram geradas."
        )


if __name__ == "__main__":
    main()

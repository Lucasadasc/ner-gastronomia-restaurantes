# Trabalho 01 - Unidade 01 (Redes)

Analise comparativa estrutural entre cardapios de restaurantes usando:
- NER customizado para gastronomia
- Grafo de co-ocorrencia de entidades
- Metricas de Teoria de Grafos (NetworkX)

## Estrutura do projeto

- `app.py`: pipeline completo (carregamento, NER, grafos, metricas, comparacao e figuras)
- `assets/data/camaroes.json`: cardapio processado do Camaroes
- `assets/data/coco_bambu.json`: cardapio processado do Coco Bambu
- `src/clean_menu_data.py`: limpeza e deduplicacao dos cardapios extraidos
- `src/extracoes/`: scripts de extracao (PDF e LiveMenu)
- `outputs/`: figuras geradas automaticamente

## Formato esperado dos dados

Cada arquivo JSON deve conter uma lista de objetos com:

```json
[
  {
    "restaurante": "Camaroes",
    "prato": "Camarao Internacional",
    "descricao": "Camarao com arroz cremoso, ervilha, presunto e batata palha ao molho branco"
  }
]
```

## Como executar

1. Instale dependencias:

```bash
pip install -r requirements.txt
```

2. Rode a analise:

```bash
python app.py
```

3. (Opcional) Informe caminhos customizados:

```bash
python app.py --camaroes data/camaroes.json --coco data/coco_bambu.json --output outputs

python app.py --camaroes assets/data/camaroes.json --coco assets/data/coco_bambu.json --output outputs
```

## Extracao do cardapio LiveMenu (Coco Bambu)

1. Extrair dados brutos da URL publica:

```bash
python src/extracoes/extract_livemenu.py --url "https://beta.livemenu.app/pt/menu/611ec1ce0304be001207f64e?v=..." --venue-id "611ec1ce0304be001207f64e" --restaurante "Coco Bambu" --out assets/data/coco_bambu_extraido.json
```

2. Limpar os dados para analise (remove bebidas e duplicados):

```bash
python src/clean_menu_data.py --in assets/data/coco_bambu_extraido.json --out assets/data/coco_bambu.json
```

3. Rodar a analise com o arquivo limpo:

```bash
python app.py --coco assets/data/coco_bambu.json
```

## Extracao do cardapio em PDF (Camaroes)

1. Extrair dados brutos do PDF:

```bash
python src/extracoes/extract_pdf_menu.py --pdf assets/arquivos/CardapioMidway.pdf --restaurante Camaroes --out assets/data/camaroes_extraido.json
```

2. Limpar os dados para analise (remove bebidas e duplicados):

```bash
python src/clean_menu_data.py --in assets/data/camaroes_extraido.json --out assets/data/camaroes.json
```

3. Rodar a analise com os dois cardapios processados:

```bash
python app.py --camaroes assets/data/camaroes.json --coco assets/data/coco_bambu.json
```

## Saidas geradas

No terminal:
- Metricas de cada grafo: nos, arestas, densidade, clustering, componentes
- Similaridade entre grafos: Jaccard de nos, Jaccard de arestas, cosseno de arestas ponderadas
- Top pares de pratos mais semelhantes por Jaccard de entidades

Em arquivos:
- `outputs/grafo_camaroes.png`
- `outputs/grafo_coco_bambu.png`

## O que mostrar no video (10 min)

- Problema e objetivo do trabalho
- Como os dados foram coletados
- Como as entidades foram extraidas
- Como o grafo foi construido (nos, arestas, peso)
- Metricas comparativas e interpretacao
- Pratos mais semelhantes e justificativa
- Conclusoes e limitacoes

## Proximos passos para fortalecer o trabalho

- Expandir o dicionario de entidades (ingredientes regionais, tecnicas, molhos)
- Incluir pre-processamento por sinonimos (ex: "mussarela" vs "muçarela")
- Exportar arestas para Gephi (CSV/GEXF)
- Comparar versoes por sentenca vs descricao completa

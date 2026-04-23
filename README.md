# NER em Gastronomia e Grafos de Co-ocorrencia

Este repositório contém um pipeline completo para analisar cardápios de restaurantes com NER baseado em regras e Teoria de Grafos. O projeto constrói grafos de co-ocorrência de entidades gastronômicas e compara estruturalmente dois restaurantes.

## Integrantes do projeto

- Lucas Augusto da Silva Cardoso
- Pedro Henrique Ribeiro de Lima

## Objetivo do trabalho

Comparar a estrutura semântica de cardápios de restaurantes a partir de:

- extração de entidades (ingredientes, acompanhamentos e técnicas/molhos),
- construção de grafos ponderados de co-ocorrência,
- cálculo de métricas de rede,
- análise de similaridade entre grafos e entre pratos.

## Fontes de dados

- Cardápio do Camarões (JSON já extraído no projeto)
- Cardápio do Coco Bambu (LiveMenu)

Arquivos principais de entrada:

- `assets/data/camaroes_extraido.json`
- `assets/data/coco_bambu_extraido.json`

## Estrutura do projeto

- `app.py`: pipeline principal (carregamento, NER, grafos, métricas e comparação)
- `src/clean_menu_data.py`: limpeza e deduplicação de dados de cardápio
- `src/extracoes/extract_livemenu.py`: extração a partir de URL pública LiveMenu
- `src/constants/`: léxicos, stopwords e regras auxiliares
- `outputs/`: visualizações interativas em HTML

## Datasets e formato esperado

Os arquivos de cardápio seguem o formato JSON abaixo:

```json
[
  {
    "restaurante": "Camaroes",
    "prato": "Camarao Internacional",
    "descricao": "Camarao com arroz cremoso, ervilha, presunto e batata palha ao molho branco"
  }
]
```

Campos:

| Campo | Tipo | Descrição | Exemplo |
|---|---|---|---|
| restaurante | string | Nome do restaurante | "Camaroes" |
| prato | string | Nome do prato | "Camarao Internacional" |
| descricao | string | Descrição textual do prato | "...ao molho branco" |

## Atividades realizadas (descrição detalhada)

1. Coleta e organização dos cardápios
- Reunião de cardápios em JSON para os dois restaurantes.
- Padronização inicial dos campos textuais.

2. Limpeza e pré-processamento
- Remoção de itens de baixo valor analítico (ex.: ruídos e entradas não relevantes para o grafo).
- Deduplicação e normalização textual (case folding, remoção de acentuação e pontuação).

3. NER baseado em regras
- Uso de léxico ativo por categorias (`INGREDIENTE`, `ACOMPANHAMENTO`, `MOLHO_TECNICA`).
- Aplicação de regras de exclusão automática (stopwords, termos e keywords de ruído).
- Possibilidade de expansão semiautomática do léxico por frequência (`--auto-expand-lexicon`).

4. Construção dos grafos
- Criação de grafo não direcionado por restaurante.
- Nós: entidades gastronômicas extraídas.
- Arestas: co-ocorrência das entidades no mesmo prato.
- Peso da aresta: frequência de co-ocorrência.

5. Geração de subgrafos para análise
- Grafo núcleo: filtragem por frequência mínima de nó e peso mínimo de aresta.
- Grafo resumo: top nós por frequência e remoção de arestas fracas.

6. Métricas e comparação
- Métricas estruturais por grafo: número de nós, arestas, densidade, componentes e maior componente.
- Comparação entre grafos: Jaccard de nós, Jaccard de arestas e cosseno ponderado das arestas.
- Comparação entre pratos por similaridade de conjuntos de entidades (Jaccard).

7. Visualização dos resultados
- Geração de visualizações interativas em HTML com PyVis.

## Scripts

- `app.py`: executa toda a análise comparativa.
- `src/clean_menu_data.py`: prepara os dados para análise.
- `src/extracoes/extract_livemenu.py`: coleta dados do LiveMenu.

## Como gerar resultados

No ambiente local:

```bash
pip install -r requirements.txt
python app.py
```

Com caminhos customizados:

```bash
python app.py --camaroes assets/data/camaroes.json --coco assets/data/coco_bambu.json --output outputs
```

## Principais resultados obtidos

Resumo quantitativo da execução atual:

| Métrica | Camarões | Coco Bambu |
|---|---:|---:|
| Nós | 43 | 43 |
| Arestas | 496 | 342 |
| Densidade | 0.5493 | 0.3787 |
| Componentes conectados | 1 | 1 |
| Maior componente | 43 | 43 |

Comparação entre grafos:

- Jaccard de nós: 0.9111
- Jaccard de arestas: 0.4132
- Cosseno ponderado (arestas): 0.6477
- Nós compartilhados: 41
- Arestas compartilhadas: 245

## Imagens ilustrativas e visualizações

As visualizações geradas estão em:

- `outputs/grafo_camaroes.html`
- `'outputs/grafo_coco_bambu.html'`
- `outputs/grafo_camaroes_resumo.html`
- `outputs/grafo_coco_bambu_resumo.html`

Sugestão para o relatório/apresentação:

- Inserir capturas de tela dos HTMLs acima como figuras do documento.
- Destacar no mínimo: densidade relativa, comunidades visuais e nós mais frequentes.

## Análise e discussão dos achados

1. Similaridade de vocabulário é alta
- O valor de Jaccard de nós (0.9111) indica forte sobreposição de entidades entre os restaurantes.

2. Estrutura relacional difere de forma relevante
- Mesmo com vocabulário próximo, o Jaccard de arestas (0.4132) mostra que as combinações entre entidades mudam bastante.

3. Camarões apresentou maior conectividade
- Maior número de arestas e maior densidade sugerem combinações mais diversificadas de entidades nos pratos analisados.

4. Similaridade ponderada intermediária
- O cosseno ponderado (0.6477) indica padrão intermediário de proximidade estrutural considerando frequências das co-ocorrências.

5. Implicação metodológica
- Comparar apenas presença de termos não é suficiente; a estrutura do grafo captura diferenças de composição culinária entre cardápios.,

## Limitações e próximos passos

- Expandir e validar o léxico com especialistas de domínio.
- Tratar sinônimos e variações ortográficas de forma mais robusta.
- Incluir avaliação quantitativa da qualidade da extração de entidades.
- Exportar grafos em formatos adicionais (ex.: GEXF/GraphML).

# 📖 Guia de Ferramentas — Loterias Pro-Analyzer

Este guia descreve cada ferramenta do aplicativo, como usá-la e como interpretar os resultados. Para instalação e execução, veja o [README](README.md).

> ⚠️ **Leia primeiro — a matemática por trás de tudo:** os sorteios da Lotofácil são independentes e uniformes. Qualquer bilhete de 15 dezenas tem média teórica de **9 pontos**, faz 11+ pontos em ~10,6% dos concursos e 13+ em ~0,15% — não importa como foi escolhido. Nenhuma ferramenta deste app (nem de nenhum outro) altera essas probabilidades. O que as ferramentas fazem é: **medir** estratégias com rigor (Backtest), **moldar o perfil** dos jogos (Score & Rank), **diversificar a carteira** (cobertura) e **melhorar o rateio esperado** nos prêmios de 14/15 pontos (Anti-Popularidade).

---

## 🗺️ Fluxo de uso recomendado

1. **📥 Carga de Planilha** — importe o histórico uma única vez.
2. **🔄 Sincronizar p/ API** — traga os concursos novos antes de cada uso.
3. **📈 Análise Estatística** — observe tendências e aplique as sugestões de filtros.
4. **🔬 Backtest** — valide qualquer estratégia contra o histórico real ANTES de apostar com ela.
5. **🎲 Gerador Inteligente** — gere a carteira com o modo Score & Rank.

---

## 📊 Painel de Status

Mostra o total de sorteios registrados, o último concurso e os caminhos locais do banco SQLite e dos arquivos de configuração de filtros. Use para confirmar que a base está carregada e atualizada.

## 📥 Carga de Planilha

Importação inicial do histórico a partir das planilhas oficiais (`Lotofácil.xlsx` / `Mega-Sena.xlsx` na raiz do projeto, ou upload de arquivo próprio). Execute **uma vez** por loteria; para recarregar, marque "Sobrescrever dados existentes".

## 🔄 Sincronizar p/ API

Busca automaticamente todos os concursos posteriores ao último registrado, direto da API pública de loterias da Caixa. Rode antes de gerar jogos para que a análise use o concurso mais recente.

## 📈 Análise Estatística

Três abas, controladas pela **janela de análise** (quantos concursos recentes considerar — padrão 120):

- **Classificação & Tendências** — tabela de todas as dezenas ordenadas por frequência, com atraso atual e categoria (🔥 Quente / ⚡ Intermediária / ❄️ Fria); médias e modas de soma, pares, primos, Fibonacci, múltiplos de 3 e moldura; e o botão **"Aplicar Sugestões"**, que calibra os filtros do gerador com os valores da janela.
- **Mapa de Movimentação** — grade cronológica concurso × dezena para inspeção visual de padrões.
- **Volante e Ciclo** (Lotofácil) — estado do ciclo atual: um ciclo fecha quando todas as 25 dezenas saíram ao menos uma vez; as ausentes aparecem destacadas. Na Mega-Sena, mostra os quadrantes da cartela.

## 🎲 Gerador Inteligente

Gera bilhetes respeitando o pipeline de filtros (soma, par/ímpar, repetição do concurso anterior, primos, Fibonacci, múltiplos de 3, moldura, linhas/colunas do volante e consecutivos). Dois pontos de configuração antes de gerar:

- **Estratégia de Filtros**: usa os limites personalizados (salvos pela Análise) ou os padrões de fábrica. O expansor "Personalizar Filtros Manualmente" permite ajuste fino de qualquer limite.
- **Modo de Geração** (Lotofácil):

### 🏆 Score & Rank (recomendado)

Em vez de aceitar o primeiro jogo que passa nos filtros, o gerador:

1. Constrói um **pool** de milhares de candidatos únicos e estruturados;
2. **Pontua** cada um de 0 a 100;
3. Seleciona os top-N com **diversificação**: um jogo só entra na carteira se compartilhar no máximo N dezenas com os já escolhidos.

O score é a média ponderada de quatro componentes (cada um 0–100, exibidos na tabela de resultado):

| Componente | O que mede |
|---|---|
| **Aderência** | Proximidade de soma, pares, primos, Fibonacci, múltiplos de 3 e moldura às médias da janela recente |
| **Equilíbrio Freq.** | Punição a bilhetes carregados só de dezenas "quentes" ou só de "frias" |
| **Repetição** | Proximidade da repetição com o concurso anterior à média histórica (~9 dezenas) |
| **Anti-Pop** | Ausência de padrões populares: sequências longas, linhas/colunas cheias, excesso de dezenas ≤12 (aniversários), moldura completa, resultados já sorteados |

**Parâmetros do Score & Rank:**

- **Tamanho do pool** (500–20.000): quantos candidatos analisar. Maior = melhor seleção, mais lento. 3.000 é um bom equilíbrio.
- **Sobreposição máxima** (8–14): máximo de dezenas em comum entre dois bilhetes da carteira. Menor = carteira mais espalhada pelo volante.
- **Peso do Anti-Popularidade** (0–1): não muda a chance de acertar — muda quanto você recebe *se* acertar 14/15 (prêmios rateados; os de 11/12/13 são fixos). Não há desvantagem em usá-lo.
- **Modo estrito**: ligado, os filtros são eliminatórios; desligado, viram apenas influência no score (útil quando filtros apertados travam a geração).

O resultado exibe o score de cada bilhete decomposto por componente e a **sobreposição média da carteira**.

### 🎲 Clássico

O comportamento original: constrói candidatos estruturados e aprova o primeiro que passar em todos os filtros. Mantido para comparação.

## 🔬 Backtest de Estratégias (Lotofácil)

**A ferramenta mais importante do app.** Simula estratégias contra o histórico real: para cada concurso do período testado, a estratégia escolhe 15 dezenas vendo **apenas os concursos anteriores**, e o acerto é conferido contra o resultado que de fato saiu — exatamente como se você tivesse apostado.

**Como usar:** selecione as estratégias, o número de concursos recentes a testar (300–500 dá boa precisão; a estratégia Score & Rank é pesada, evite períodos enormes com ela) e clique em Rodar. A semente aleatória garante reprodutibilidade.

**Como interpretar:**

- A linha **📐 Teoria (acaso puro)** é a régua: média 9,000 | ≥11 pts: 10,59% | ≥13 pts: 0,149%.
- Estratégias dentro de ±0,05 da média teórica estão **empatadas com o acaso** — diferenças pequenas são ruído de amostra, não vantagem.
- Se alguma estratégia superar a teoria de forma consistente em amostras grandes (milhares de concursos), aí sim ela merece atenção. Até hoje, nenhuma superou — incluindo atrasadas, quentes, frias, ciclo e repetição, todas já testadas nesta base.

**Estratégias disponíveis:** Aleatório puro (baseline), 15 mais atrasadas, 15 mais quentes/frias (janela 20), Repete 9 do anterior, Ausentes do ciclo + atrasadas, Score & Rank.

**Para desenvolvedores** — adicionar uma estratégia nova é registrar uma função em `src/lotofacil/backtest.py`:

```python
def strat_minha_ideia(history: list[dict], rng: random.Random) -> list[int]:
    # history = concursos anteriores em ordem cronológica; retorne 15 dezenas
    ...

STRATEGIES["Minha ideia"] = strat_minha_ideia
```

Ela aparece automaticamente no seletor da interface.

## 🧐 Histórico e Resultados

Consulta de qualquer concurso registrado: busca individual com navegação anterior/próximo e tabela paginada completa.

---

## 🧩 Uso programático (módulos)

Para scripts próprios, os módulos da Lotofácil podem ser usados diretamente:

```python
from src.db import connect_db, get_all_draws
from src.lotofacil.filters import default_filter_config
from src.lotofacil.scoring import build_scoring_context, generate_ranked_games
from src.lotofacil.backtest import run_backtest

with connect_db(DB_PATH) as conn:
    draws = get_all_draws(conn, "lotofacil")

# Gerar 5 jogos com Score & Rank
ctx = build_scoring_context(draws, window=120)
resultado = generate_ranked_games(default_filter_config(), ctx, amount=5, pool_size=3000)

# Backtestar estratégias nos últimos 500 concursos
resultados = run_backtest(draws, ["Aleatório puro (baseline)", "Score & Rank (gerador do app)"], test_last_n=500)
```

---

## ❓ Perguntas frequentes

**O Score & Rank aumenta minha chance de acertar?**
Não — nada aumenta. Ele seleciona jogos com perfil estatístico típico, carteira diversificada e melhor rateio esperado. A média de pontos continuará ~9, como o Backtest demonstra.

**Fazer 7–8 pontos significa que a estratégia é ruim?**
Não. Qualquer bilhete faz 7–8 pontos em ~34% dos concursos — é o comportamento normal da distribuição.

**Vale a pena o Anti-Popularidade?**
Sempre. Ele não reduz nenhuma probabilidade; apenas evita dividir os prêmios de 14/15 pontos com multidões que jogam sequências, datas e resultados passados.

**Por que o Backtest só existe para a Lotofácil?**
Foi implementado primeiro para ela por ter mais concursos e prêmios em mais faixas. A estrutura do módulo permite estender para a Mega-Sena.

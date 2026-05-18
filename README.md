# Lotofacil Analyzer Pro

Aplicacao CLI local para manter o historico da Lotofacil em SQLite, analisar padroes e gerar palpites filtrados com uma interface de terminal rica.

## Requisitos

- Python 3.10+ (recomendado)
- Windows, macOS ou Linux

## Instalacao

Se o comando `pip` nao existir no Windows, use `py -m pip`.

```bash
py -m pip install -r requirements.txt
```

## Como iniciar

### Menu interativo (comando unico)

```bash
py main.py
```

### Interface Streamlit

```bash
py -m streamlit run streamlit_app.py
```

No menu, siga esta ordem:

1. Carga inicial pelo Excel (uma vez)
2. Atualizar com novos sorteios pela API
3. Analise dinamica (janela deslizante)
4. Gerar palpites com pipeline de filtros

## Arquivos gerados

- data/lotofacil_analyzer_pro.db: banco SQLite com sorteios e estatisticas.
- data/config_filtros.json: configuracoes persistidas dos filtros.

## Observacoes

- O Excel e usado apenas na carga inicial. Depois disso, o app atualiza via API.
- Nome padrao esperado do Excel: Lotofácil.xlsx (na raiz do projeto).
- A API e consultada concurso a concurso ate retornar 404.

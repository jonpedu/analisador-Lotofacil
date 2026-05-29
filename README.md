# Loterias Pro-Analyzer 🧠

Uma plataforma modular e avançada de análise estatística, rastreamento de tendências e geração inteligente de palpites matemáticos para as principais loterias da Caixa: **Lotofácil** e **Mega-Sena**. 

O sistema conta com um motor local de banco de dados SQLite de alta performance, atualizações automáticas via API de loterias e uma interface premium rica desenvolvida em Streamlit.

---

## 🚀 Principais Recursos

### 🍀 Módulo Lotofácil
* **Rastreador de Ciclos:** Identifica automaticamente o número do ciclo ativo e exibe exatamente quais dezenas estão ausentes (faltando para fechar o ciclo).
* **Gerador Inteligente Ponderado:** Substitui palpites aleatórios simples por bilhetes construídos matematicamente para repetir de 8 a 10 dezenas do concurso anterior, injetar dezenas ausentes do ciclo ativo e balancear números quentes, frios e intermediários.
* **Pipeline de Filtros:** Validações rigorosas de soma de dezenas, par/ímpar, primos, Fibonacci, múltiplos de 3, números da moldura e limite máximo de números consecutivos.

### 💰 Módulo Mega-Sena
* **Mapeamento de Quadrantes:** Divide a cartela fisicamente em 4 quadrantes (Top Left, Top Right, Bottom Left, Bottom Right) e assegura que as dezenas estejam distribuídas uniformemente, alinhando-se à física da maioria dos sorteios reais.
* **Gerador Otimizado por Pesos:** Cria palpites de 6 números equilibrados com base nos quadrantes, somas de dezenas recomendadas, quantidade de pares, primos e números de Fibonacci.

### 📊 Interface Pro (Comum a Ambas)
* **Tabela Única de Frequência Completa:** Exibe todos os números em ordem decrescente de aparições (do mais sorteado para o menos sorteado), contendo o atraso atual em concursos, a frequência percentual (%) e badges coloridos de categoria (**🔥 Quente**, **❄️ Fria**, **⚡ Intermediária**).
* **Consulta Rápida de Resultados:** Navegador individual de concursos com data e paginação dinâmica.
* **Personalização de Filtros:** Painéis integrados e amigáveis para calibração manual de parâmetros e salvamento automático.

---

## 🛠️ Requisitos e Instalação

* **Python 3.10+** (Recomendado)
* **Bibliotecas adicionais:** `pandas`, `streamlit`, `rich`, `questionary`, `requests`, `openpyxl` (especificadas em `requirements.txt`).

Para instalar todas as dependências no Windows (utilize `py -m pip` se o comando global `pip` não estiver mapeado):

```bash
py -m pip install -r requirements.txt
```

---

## 🕹️ Como Executar

### 🌟 Interface Streamlit (Recomendado)
Para iniciar o dashboard visual premium e interativo:

```bash
py -m streamlit run streamlit_app.py
```
*Ou simplesmente execute o arquivo automatizado **`Iniciar_App.bat`** na raiz do projeto.*

### 💻 Interface de Console (Terminal CLI)
Para executar ferramentas e utilitários via linha de comando interativa:

```bash
py src/main.py
```

---

## 📁 Estrutura do Banco de Dados e Configurações

* **`data/lotofacil_analyzer_pro.db`:** Banco SQLite central contendo tabelas unificadas e estatísticas pré-processadas:
  * `sorteios` e `estatisticas_sorteio` (Lotofácil)
  * `sorteios_megasena` and `estatisticas_megasena` (Mega-Sena)
* **`data/config_filtros_lotofacil.json`:** Parâmetros persistidos de filtros exclusivos da Lotofácil.
* **`data/config_filtros_megasena.json`:** Parâmetros persistidos de filtros exclusivos da Mega-Sena.
* **Planilhas de Carga Inicial:** `Lotofácil.xlsx` e `Mega-Sena.xlsx` (devem estar localizadas na raiz do projeto para o primeiro carregamento).

---

## 📝 Licença

Este projeto é distribuído sob a **Licença MIT**, permitindo o uso pessoal, modificação e distribuição sem restrições.

```text
Copyright (c) 2026 Loterias Pro-Analyzer Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

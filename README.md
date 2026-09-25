# F105 — Datamining e Webscraping

Comparação de preços de cinco itens da cesta básica (**arroz, feijão, açúcar, óleo e ovos**) em três supermercados online: **Carrefour**, **Pão de Açúcar** e **São Luiz**.

## Requisitos

- Python 3.10+
- Google Chrome (usado pelo Playwright para capturar o token do São Luiz)

## Instalação

```bash
# 1. Clone o repositório e entre na pasta
cd F105-Datamining-Webscraping

# 2. Crie e ative a venv
python -m venv venv
source venv/bin/activate        # Linux/macOS
# venv\Scripts\activate         # Windows

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Instale o navegador do Playwright (uma vez só)
playwright install chromium
```

## Como executar

```
python setup.py
```

Isso executa, em ordem: captura do token do São Luiz → coleta nos 3 mercados → tratamento dos dados → análise e geração dos gráficos.

Se uma etapa falhar, o pipeline para e mostra onde.

Se quiser executar em etapas:

```
python token/get_token_sao_luiz.py         # captura token → .env
python raspadores/coleta_sao_luiz.py       # coleta São Luiz
python raspadores/coleta_carrefour.py      # coleta Carrefour
python raspadores/coleta_pao_de_acucar.py  # coleta Pão de Açúcar
python tratamento.py                        # trata os dados
python analise.py                           # gera gráficos e insights
```

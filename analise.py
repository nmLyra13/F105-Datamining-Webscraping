"""
Mineracao e Visualizacao - F105 Datamining e Webscraping
Le dados_tratados.csv (saida do tratamento.py), calcula estatisticas
descritivas, identifica padroes e gera os graficos + o dashboard da atividade.

Gera:
  - estatisticas_descritivas.csv   (Fase D: media, min, max, mediana, contagem)
  - grafico1_preco_medio.png       (grafico 1/4)
  - grafico2_distribuicao_precos.png (grafico 2/4)
  - grafico3_menor_maior_preco.png (grafico 3/4 - responde a pergunta de negocio)
  - grafico4_preco_medio_por_fonte.png (grafico 4/4 - responde a pergunta de negocio com base nas fontes)
  - dashboard.png                  (Fase E: dashboard com 2+ graficos)
  - insights.txt                   (padroes identificados, para colar no relatorio)

Uso:
    python3 analise.py
"""

import matplotlib

matplotlib.use("Agg")  # backend seguro para headless

import matplotlib.pyplot as plt
import pandas as pd

# Fonte padrão que cobre acentos latinos em qualquer ambiente
plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["axes.unicode_minus"] = False

ARQUIVO_ENTRADA = "dados/dados_tratados.csv"
# Paleta categorica (fixa por item_basico, reaproveitada em todos os graficos
# para manter a mesma cor = mesma entidade em todo o trabalho).
CORES_ITEM = {
    "arroz": "#2a78d6",  # azul
    "feijao": "#eb6834",  # laranja
    "acucar": "#1baf7a",  # verde-agua
    "oleo": "#eda100",  # amarelo
    "ovos": "#e87ba4",  # magenta
}
ORDEM_ITENS = ["arroz", "feijao", "acucar", "oleo", "ovos"]
NOMES_BONITOS = {
    "arroz": "Arroz",
    "feijao": "Feijão",
    "acucar": "Açúcar",
    "oleo": "Óleo",
    "ovos": "Ovos",
}
COR_MENOR = "#2a78d6"  # azul - "menor preco" (polo "bom")
COR_MAIOR = "#e34948"  # vermelho - "maior preco" (polo "caro") - par divergente
CORES_FONTE = {
    "carrefour": "#2a78d6",  # azul
    "paodeacucar": "#eb6834",  # laranja
    "saoluiz": "#1baf7a",  # verde-água
}
NOMES_FONTE = {
    "carrefour": "Carrefour",
    "paodeacucar": "Pão de Açúcar",
    "saoluiz": "São Luiz",
}
ORDEM_FONTES = ["carrefour", "paodeacucar", "saoluiz"]
INK = "#0b0b0b"
INK_SECUNDARIA = "#52514e"
GRADE = "#e1e0d9"


def estilo_eixo(ax):
    """Aplica o acabamento padrao usado em todos os graficos deste trabalho:
    sem moldura em cima/direita, grade horizontal bem leve, eixos discretos."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#c3c2b7")
    ax.spines["bottom"].set_color("#c3c2b7")
    ax.yaxis.grid(True, color=GRADE, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(colors=INK_SECUNDARIA)


def carregar_dados():
    df = pd.read_csv(ARQUIVO_ENTRADA, encoding="utf-8-sig")
    df["item_basico"] = pd.Categorical(
        df["item_basico"], categories=ORDEM_ITENS, ordered=True
    )
    return df.sort_values("item_basico")


def calcular_estatisticas(df: pd.DataFrame) -> pd.DataFrame:
    stats = (
        df.groupby("item_basico", observed=True)["preco"]
        .agg(
            contagem="count",
            media="mean",
            mediana="median",
            minimo="min",
            maximo="max",
            desvio_padrao="std",
        )
        .round(2)
    )
    stats = stats.reindex(ORDEM_ITENS)
    stats.to_csv("dados/estatisticas_descritivas.csv", encoding="utf-8-sig")
    print("Estatísticas descritivas (também salvas em estatisticas_descritivas.csv):")
    print(stats.to_string())
    return stats


def calcular_estatisticas_por_fonte(df: pd.DataFrame) -> pd.DataFrame:
    """
    Média de preço por item_basico x fonte.
    Útil para ver qual mercado é sistematicamente mais barato em cada item.
    """
    tabela = (
        df.pivot_table(
            index="item_basico",
            columns="fonte",
            values="preco",
            aggfunc="mean",
            observed=True,
        )
        .round(2)
        .reindex(ORDEM_ITENS)
    )
    tabela.to_csv("dados/estatisticas_por_fonte.csv", encoding="utf-8-sig")
    print(
        "\nPreço médio por item x fonte (também salvo em estatisticas_por_fonte.csv):"
    )
    print(tabela.to_string())
    return tabela


def grafico1_preco_medio(stats: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(7, 4.5), dpi=150)
    itens = [NOMES_BONITOS[i] for i in stats.index]
    cores = [CORES_ITEM[i] for i in stats.index]
    barras = ax.bar(itens, stats["media"], color=cores, width=0.6, zorder=3)
    for barra, valor in zip(barras, stats["media"]):
        ax.annotate(
            f"R$ {valor:.2f}",
            (barra.get_x() + barra.get_width() / 2, valor),
            textcoords="offset points",
            xytext=(0, 5),
            ha="center",
            fontsize=9,
            color=INK,
        )
    ax.set_title(
        "Preço médio por item básico da cesta",
        fontsize=13,
        fontweight="bold",
        color=INK,
        pad=14,
    )
    ax.set_ylabel("Preço médio (R$)", color=INK_SECUNDARIA)
    ax.set_xlabel("Item básico", color=INK_SECUNDARIA)
    estilo_eixo(ax)
    fig.tight_layout()
    fig.savefig("graficos/grafico1_preco_medio.png")
    plt.close(fig)
    print("Salvo: grafico1_preco_medio.png")


def grafico2_distribuicao_precos(df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(7.5, 4.5), dpi=150)
    dados = [df.loc[df["item_basico"] == i, "preco"].values for i in ORDEM_ITENS]
    bp = ax.boxplot(
        dados,
        tick_labels=[NOMES_BONITOS[i] for i in ORDEM_ITENS],
        patch_artist=True,
        widths=0.55,
        medianprops=dict(color=INK, linewidth=1.5),
        whiskerprops=dict(color=INK_SECUNDARIA),
        capprops=dict(color=INK_SECUNDARIA),
        flierprops=dict(
            marker="o",
            markersize=4,
            markerfacecolor="none",
            markeredgecolor=INK_SECUNDARIA,
        ),
    )
    for patch, item in zip(bp["boxes"], ORDEM_ITENS):
        patch.set_facecolor(CORES_ITEM[item])
        patch.set_alpha(0.55)
        patch.set_edgecolor(CORES_ITEM[item])
    ax.set_title(
        "Distribuição de preços por item básico",
        fontsize=13,
        fontweight="bold",
        color=INK,
        pad=14,
    )
    ax.set_ylabel("Preço (R$)", color=INK_SECUNDARIA)
    ax.set_xlabel("Item básico", color=INK_SECUNDARIA)
    estilo_eixo(ax)
    fig.tight_layout()
    fig.savefig("graficos/grafico2_distribuicao_precos.png")
    plt.close(fig)
    print("Salvo: grafico2_distribuicao_precos.png")


def _linha_extremo(df, item, kind):
    sub = df[df["item_basico"] == item]
    row = (
        sub.loc[sub["preco"].idxmin()]
        if kind == "min"
        else sub.loc[sub["preco"].idxmax()]
    )
    return row["nome_produto"], row["preco"]


def grafico3_menor_maior_preco(df: pd.DataFrame) -> pd.DataFrame:
    """Responde diretamente a pergunta de negocio: menor e maior preco por
    item basico, com a marca/produto e a diferenca entre eles."""
    linhas = []
    for item in ORDEM_ITENS:
        nome_min, preco_min = _linha_extremo(df, item, "min")
        nome_max, preco_max = _linha_extremo(df, item, "max")
        linhas.append(
            {
                "item_basico": item,
                "produto_mais_barato": nome_min,
                "preco_min": preco_min,
                "produto_mais_caro": nome_max,
                "preco_max": preco_max,
                "diferenca_absoluta": round(preco_max - preco_min, 2),
                "diferenca_percentual": round(
                    (preco_max - preco_min) / preco_min * 100, 1
                ),
            }
        )
    resumo = pd.DataFrame(linhas)
    resumo.to_csv(
        "dados/resumo_menor_maior_preco.csv", index=False, encoding="utf-8-sig"
    )

    fig, ax = plt.subplots(figsize=(9, 5), dpi=150)
    y = range(len(ORDEM_ITENS))
    altura = 0.35
    ax.barh(
        [p + altura / 2 for p in y],
        resumo["preco_min"],
        height=altura,
        color=COR_MENOR,
        label="Menor preço",
        zorder=3,
    )
    ax.barh(
        [p - altura / 2 for p in y],
        resumo["preco_max"],
        height=altura,
        color=COR_MAIOR,
        label="Maior preço",
        zorder=3,
    )
    for p, (_, row) in zip(y, resumo.iterrows()):
        ax.annotate(
            f"R$ {row['preco_min']:.2f}",
            (row["preco_min"], p + altura / 2),
            textcoords="offset points",
            xytext=(6, 0),
            va="center",
            fontsize=8.5,
            color=INK,
        )
        ax.annotate(
            f"R$ {row['preco_max']:.2f}",
            (row["preco_max"], p - altura / 2),
            textcoords="offset points",
            xytext=(6, 0),
            va="center",
            fontsize=8.5,
            color=INK,
        )
    ax.set_yticks(list(y))
    ax.set_yticklabels([NOMES_BONITOS[i] for i in ORDEM_ITENS])
    ax.set_xlabel("Preço (R$)", color=INK_SECUNDARIA)
    ax.set_title(
        "Menor x maior preço por item básico",
        fontsize=13,
        fontweight="bold",
        color=INK,
        pad=14,
    )
    ax.legend(frameon=False, loc="upper right")
    estilo_eixo(ax)
    ax.xaxis.grid(False)
    fig.tight_layout()
    fig.savefig("graficos/grafico3_menor_maior_preco.png")
    plt.close(fig)
    print("Salvo: grafico3_menor_maior_preco.png")
    print(
        "\nResumo menor x maior preço (também salvo em resumo_menor_maior_preco.csv):"
    )
    print(resumo.to_string(index=False))
    return resumo


def grafico4_preco_medio_por_fonte(tabela_fonte: pd.DataFrame):
    """
    Barras agrupadas: para cada item básico, o preço médio em cada fonte.
    Fontes ausentes naquele item simplesmente não aparecem.
    """
    fig, ax = plt.subplots(figsize=(9.5, 5), dpi=150)

    itens = list(tabela_fonte.index)
    n_fontes = len(ORDEM_FONTES)
    largura = 0.8 / n_fontes
    x_base = range(len(itens))

    for i, fonte in enumerate(ORDEM_FONTES):
        if fonte not in tabela_fonte.columns:
            continue
        valores = tabela_fonte[fonte].reindex(itens).values
        posicoes = [x + (i - (n_fontes - 1) / 2) * largura for x in x_base]
        barras = ax.bar(
            posicoes,
            valores,
            width=largura,
            color=CORES_FONTE[fonte],
            label=NOMES_FONTE[fonte],
            zorder=3,
        )
        for barra, valor in zip(barras, valores):
            if pd.isna(valor):
                continue
            ax.annotate(
                f"R$ {valor:.2f}",
                (barra.get_x() + barra.get_width() / 2, valor),
                textcoords="offset points",
                xytext=(0, 4),
                ha="center",
                fontsize=7.5,
                color=INK,
            )

    ax.set_xticks(list(x_base))
    ax.set_xticklabels([NOMES_BONITOS[i] for i in itens])
    ax.set_ylabel("Preço médio (R$)", color=INK_SECUNDARIA)
    ax.set_xlabel("Item básico", color=INK_SECUNDARIA)
    ax.set_title(
        "Preço médio por item e por mercado",
        fontsize=13,
        fontweight="bold",
        color=INK,
        pad=14,
    )
    ax.legend(frameon=False, loc="upper right", title=None)
    estilo_eixo(ax)
    fig.tight_layout()
    fig.savefig("graficos/grafico4_preco_medio_por_fonte.png")
    plt.close(fig)
    print("Salvo: grafico4_preco_medio_por_fonte.png")


def montar_dashboard(stats: pd.DataFrame, resumo: pd.DataFrame):
    """Fase E: dashboard simples com >=2 graficos, em Python + Matplotlib."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5), dpi=150)

    itens = [NOMES_BONITOS[i] for i in stats.index]
    cores = [CORES_ITEM[i] for i in stats.index]
    barras = ax1.bar(itens, stats["media"], color=cores, width=0.6, zorder=3)
    for barra, valor in zip(barras, stats["media"]):
        ax1.annotate(
            f"R$ {valor:.2f}",
            (barra.get_x() + barra.get_width() / 2, valor),
            textcoords="offset points",
            xytext=(0, 5),
            ha="center",
            fontsize=8.5,
            color=INK,
        )
    ax1.set_title("Preço médio por item", fontsize=12, fontweight="bold", color=INK)
    ax1.set_ylabel("Preço médio (R$)", color=INK_SECUNDARIA)
    estilo_eixo(ax1)

    y = range(len(ORDEM_ITENS))
    altura = 0.35
    ax2.barh(
        [p + altura / 2 for p in y],
        resumo["preco_min"],
        height=altura,
        color=COR_MENOR,
        label="Menor preço",
        zorder=3,
    )
    ax2.barh(
        [p - altura / 2 for p in y],
        resumo["preco_max"],
        height=altura,
        color=COR_MAIOR,
        label="Maior preço",
        zorder=3,
    )
    ax2.set_yticks(list(y))
    ax2.set_yticklabels([NOMES_BONITOS[i] for i in ORDEM_ITENS])
    ax2.set_xlabel("Preço (R$)", color=INK_SECUNDARIA)
    ax2.set_title("Menor x maior preço", fontsize=12, fontweight="bold", color=INK)
    ax2.legend(frameon=False, loc="upper right", fontsize=9)
    estilo_eixo(ax2)
    ax2.xaxis.grid(False)

    fig.suptitle(
        "Dashboard — Cesta básica em 3 mercados (Carrefour, Pão de Açúcar e São Luiz)",
        fontsize=13,
        fontweight="bold",
        color=INK,
        y=1.02,
    )
    fig.tight_layout()
    fig.savefig("graficos/dashboard.png", bbox_inches="tight")
    plt.close(fig)
    print("Salvo: graficos/dashboard.png")


def resumo_mais_baratos_por_tipo(df: pd.DataFrame) -> pd.DataFrame:
    """
    Para cada item básico, encontra o produto de menor preço entre TODAS as
    fontes coletadas, e devolve nome, preço, fonte, url e código.
    """
    linhas = []
    for item in ORDEM_ITENS:
        sub = df[df["item_basico"] == item]
        if sub.empty:
            continue
        row = sub.loc[sub["preco"].idxmin()]
        linhas.append(
            {
                "item_basico": item,
                "nome_produto": row["nome_produto"],
                "preco": row["preco"],
                "fonte": row["fonte"],
                "url_produto": row["url_produto"],
                "codigo_produto": row["codigo_produto"],
            }
        )
    resumo = pd.DataFrame(linhas)
    resumo.to_csv("dados/mais_baratos_por_tipo.csv", index=False, encoding="utf-8-sig")
    return resumo


def adicionar_insight_mais_baratos(
    insights: list, resumo_baratos: pd.DataFrame
) -> None:
    """
    Acrescenta ao arquivo insights.txt uma linha por item básico informando
    nome, preço, fonte e link do produto mais barato encontrado.
    """
    bloco = ["5. Produto mais barato de cada tipo (considerando todas as fontes):"]
    for _, row in resumo_baratos.iterrows():
        bloco.append(
            f"   - {NOMES_BONITOS[row['item_basico']]}: "
            f'"{row["nome_produto"]}" — R$ {row["preco"]:.2f} '
            f"({NOMES_FONTE.get(row['fonte'], row['fonte'])}) — {row['url_produto']}"
        )
    insights.append("\n".join(bloco))


def identificar_insights(stats: pd.DataFrame, resumo: pd.DataFrame) -> list:
    insights = []

    mais_caro_medio = stats["media"].idxmax()
    mais_barato_medio = stats["media"].idxmin()
    insights.append(
        f"1. Em média, {NOMES_BONITOS[mais_caro_medio]} é o item mais caro da cesta "
        f"(R$ {stats.loc[mais_caro_medio, 'media']:.2f}) e {NOMES_BONITOS[mais_barato_medio]} "
        f"o mais barato (R$ {stats.loc[mais_barato_medio, 'media']:.2f})."
    )

    maior_variacao = resumo.loc[resumo["diferenca_percentual"].idxmax()]
    insights.append(
        f"2. {NOMES_BONITOS[maior_variacao['item_basico']]} é o item com maior variação de preço "
        f"entre marcas: {maior_variacao['diferenca_percentual']:.0f}% de diferença entre a opção "
        f'mais barata ("{maior_variacao["produto_mais_barato"]}", R$ {maior_variacao["preco_min"]:.2f}) '
        f'e a mais cara ("{maior_variacao["produto_mais_caro"]}", R$ {maior_variacao["preco_max"]:.2f}).'
    )

    menor_variacao = resumo.loc[resumo["diferenca_percentual"].idxmin()]
    insights.append(
        f"3. Já {NOMES_BONITOS[menor_variacao['item_basico']]} é o item com menor variação de preço "
        f"entre marcas ({menor_variacao['diferenca_percentual']:.0f}%), sugerindo um mercado mais "
        f"padronizado/menos diferenciado para esse produto nessa loja."
    )

    maior_desvio = stats["desvio_padrao"].idxmax()
    insights.append(
        f"4. {NOMES_BONITOS[maior_desvio]} também é o item com maior dispersão de preços "
        f"(desvio padrão de R$ {stats.loc[maior_desvio, 'desvio_padrao']:.2f}), coerente com ser "
        f"uma categoria com muitas marcas e variações de tipo/qualidade coletadas."
    )

    with open("insights.txt", "w", encoding="utf-8") as f:
        f.write("\n\n".join(insights) + "\n")
    print("\nInsights identificados (também salvos em insights.txt):")
    for i in insights:
        print(" -", i)
    return insights


if __name__ == "__main__":
    df = carregar_dados()

    stats = calcular_estatisticas(df)
    tabela_fonte = calcular_estatisticas_por_fonte(df)

    grafico1_preco_medio(stats)
    grafico2_distribuicao_precos(df)
    resumo = grafico3_menor_maior_preco(df)
    grafico4_preco_medio_por_fonte(tabela_fonte)

    montar_dashboard(stats, resumo)

    resumo_baratos = resumo_mais_baratos_por_tipo(df)
    print(
        "\nProduto mais barato de cada tipo (também salvo em mais_baratos_por_tipo.csv):"
    )
    print(resumo_baratos.to_string(index=False))

    insights = identificar_insights(stats, resumo)
    adicionar_insight_mais_baratos(insights, resumo_baratos)

    # Reescreve o insights.txt com o novo bloco incluído
    with open("insights.txt", "w", encoding="utf-8") as f:
        f.write("\n\n".join(insights) + "\n")

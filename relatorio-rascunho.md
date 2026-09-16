# Rascunho do relatório — F105 Datamining e Webscraping

> Este arquivo vai acumulando os trechos do relatório conforme avançamos nas fases.
> No final, é só formatar isso no Word/PDF seguindo a estrutura pedida (capa, problema,
> fonte dos dados, método de coleta, pré-processamento, análise, gráficos/dashboard,
> aspectos éticos, conclusão).

## 3. Fonte dos Dados

A fonte de dados escolhida foi a loja online do supermercado São Luiz
(mercadinhossaoluiz.com.br), especificamente a unidade identificada internamente
como `market_id = 355`. A categoria de análise definida foi **produtos de
supermercado**, restrita aos cinco itens que compõem a cesta básica considerada
neste trabalho: arroz, feijão, açúcar, óleo e ovos (o item leite foi substituído
por ovos após verificação de que a categoria de leite não estava disponível de
forma equivalente na fonte escolhida).

## 4. Método de Coleta

O site do São Luiz é implementado como uma aplicação de página única (SPA) em
React: o código-fonte HTML entregue pelo servidor não contém nenhuma informação
de produto ou preço, apenas uma `<div id="root">` vazia que é preenchida
dinamicamente pelo JavaScript no navegador do usuário. A verificação disso foi
feita inspecionando o código-fonte da página (Ctrl/Cmd+U) antes de decidir a
estratégia de coleta.

Diante disso, em vez de renderizar a página com uma ferramenta como o Selenium,
a equipe optou por investigar as requisições de rede feitas pelo próprio site
(DevTools do navegador, aba Network, filtro Fetch/XHR). Essa investigação
revelou que o frontend consome uma API JSON própria, hospedada em
`merconnect.mercadapp.com.br` (plataforma de e-commerce "mercadapp", utilizada
como white-label por diversos supermercados, entre eles o São Luiz), no formato:

```
GET https://merconnect.mercadapp.com.br/mapp/v3/markets/{market_id}/items
    ?page={page}&category_id={category_id}
```

**Justificativa da escolha (API em vez de scraping de HTML):** como essa API já
devolve os dados estruturados em JSON (nome, preço, preço original, código de
barras, estoque, categoria), sua utilização é tecnicamente mais robusta e
eficiente do que interpretar HTML renderizado via Selenium — não depende de
seletores CSS sujeitos a mudanças de layout, e não exige o custo computacional
de abrir um navegador automatizado. É importante registrar, no entanto, que
esta não é uma API pública documentada oficialmente pelo São Luiz ou pela
mercadapp: trata-se de uma interface interna, destinada ao consumo pelo próprio
site, descoberta por meio de engenharia reversa do tráfego de rede — uma
técnica legítima e amplamente usada em projetos de coleta de dados, mas que traz
implicações importantes discutidas na seção de Aspectos Éticos e Legais.

**Autenticação e paginação:** a API exige um cabeçalho `Authorization: Bearer
<token>`. Esse token é gerado do lado do cliente (navegador) e tem vida curta —
na prática, verificamos que um token deixa de ser aceito (erro HTTP 401) após
alguns minutos, exigindo nova captura via DevTools a cada execução manual do
script. A paginação é feita de forma simples, incrementando o parâmetro `page`
e consultando o campo `has_next_page` da resposta para saber quando parar.

**Limite de página por categoria:** por padrão, a API pode devolver centenas de
itens em algumas categorias (ex.: mais de 150 produtos na categoria de óleos).
Como a atividade exige um mínimo de 30 registros no total (e não por item), o
script foi ajustado para coletar no máximo 3 páginas por categoria — o
suficiente para ultrapassar o mínimo exigido somando as cinco categorias, sem
gerar volume de requisições desnecessário.

**Incidente observado durante os testes:** ao tentar coletar um número maior de
páginas em sequência rápida, a API retornou erro HTTP 403 (Forbidden), inclusive
em endpoints não relacionados à coleta (como um endpoint de avisos do próprio
site), sugerindo um bloqueio temporário por parte de um mecanismo de proteção
contra abuso (rate limiting / WAF) associado ao IP de origem das requisições.
Esse episódio reforçou, na prática, a necessidade dos cuidados discutidos na
seção seguinte.

## 5. Pré-processamento

**Tratamento de valores ausentes e duplicados.** Registros sem `nome_produto`
ou `preco` foram descartados (campos essenciais para a análise); quando
`preco_original` vinha vazio, foi preenchido com o próprio `preco` (significa
"sem desconto ativo", não um dado faltante de fato). Duplicatas foram
removidas por `codigo_barras` (chave mais confiável que o nome do produto,
que pode se repetir com pequenas variações de embalagem).

**Padronização.** Preços foram convertidos para `float` com 2 casas decimais
de forma tolerante a formato (aceita tanto o número já numérico salvo pelo
`coleta.py` quanto uma eventual string em formato BR, ex. "R$ 1.234,56").
Nomes de produto foram normalizados (espaços extras removidos).

**Filtro de relevância por item básico (achado importante).** Ao navegar
manualmente pela estrutura de categorias do site (inspecionando o estado
interno da aplicação React, não só a interface visível) confirmamos que:

- `arroz` (13758), `feijão` (13759) e `açúcar` (13760) são categorias de
  nível 2 dedicadas exclusivamente a cada item — praticamente sem ruído (foi
  encontrado 1 produto fora do escopo: "BISCOITO ARROZ NATURATTA INTEGRAL
  ZERO 60G" dentro da categoria de arroz).
- `oleo` (13799) na verdade corresponde à categoria "Temperos" — um balde
  amplo que mistura óleos com condimentos, molhos e maionese.
- `ovos` (13797) corresponde à categoria "Mercearia" — outro balde amplo,
  que mistura ovos com sopas instantâneas, enlatados e mistura para bolo.

O site não expõe, no nível usado pela API de coleta, uma categoria dedicada
só a "óleo de cozinha" ou só a "ovos" — essas são subdivisões de terceiro
nível, usadas apenas como filtro dentro da interface, sem um identificador
estável e documentado que pudéssemos usar diretamente na URL da API. Coletar
por essas categorias amplas foi, portanto, uma decisão consciente (é a
granularidade que a fonte de dados realmente oferece), mas exigiu um passo
adicional de limpeza: um filtro de relevância, aplicado por `item_basico`,
que mantém apenas produtos cujo nome começa com o padrão esperado (ex.: só
"ÓLEO DE {SOJA|MILHO|CANOLA|GIRASSOL|COCO|...}" para óleo — excluindo de
propósito azeite de oliva, por ser um produto de categoria de preço distinta,
e itens não alimentícios que aparecem na mesma prateleira do site, como óleo
de banho/reparo capilar).

Os itens removidos por esse filtro foram salvos separadamente em
`itens_excluidos_pelo_filtro.csv`, preservando rastreabilidade da limpeza
para fins de auditoria/relatório.

**Script:** `tratamento.py`, que lê `dados_brutos.csv` e gera
`dados_tratados.csv`.


## 6. Mineração de Dados, Análises e Visualizações

**Estatísticas descritivas** (calculadas em `analise.py`, salvas em
`estatisticas_descritivas.csv`):

| Item   | Contagem | Média (R$) | Mediana (R$) | Mínimo (R$) | Máximo (R$) | Desvio padrão |
|--------|---------:|-----------:|-------------:|------------:|------------:|---------------|
| Arroz  | 30       | 17,39      | 12,81        | 4,94        | 43,63       | 12,52         |
| Feijão | 18       | 12,27      | 10,15        | 6,58        | 32,41       | 6,29          |
| Açúcar | 14       | 8,85       | 7,13         | 3,67        | 23,25       | 5,09          |
| Óleo   | 4        | 19,66      | 20,95        | 9,46        | 27,26       | 7,42          |
| Ovos   | 13       | 15,37      | 16,83        | 9,67        | 25,63       | 5,79          |

**Gráficos gerados** (3 gráficos distintos, cada um com título, eixos e
legenda, exigência do critério 4):

1. `grafico1_preco_medio.png` — barras com o preço médio de cada item básico.
2. `grafico2_distribuicao_precos.png` — boxplot da distribuição de preços por
   item, evidenciando dispersão e outliers.
3. `grafico3_menor_maior_preco.png` — barras horizontais comparando o produto
   mais barato e o mais caro de cada item, respondendo diretamente à pergunta
   de negócio.

**Padrões identificados:**

1. Em média, Óleo é o item mais caro da cesta (R$ 19,66) e Açúcar o mais
   barato (R$ 8,85).
2. Arroz é o item com maior variação de preço entre produtos coletados
   (783% entre o mais barato e o mais caro) — mas esse número precisa de uma
   ressalva importante: o produto mais caro coletado não é um arroz comum, e
   sim um arroz especial ("ARROZ NEGRO LA PASTINA 500G", um arroz negro/integral
   de nicho), enquanto o mais barato é um arroz branco comum de 1kg. A
   diferença reflete, portanto, tipos de produto muito distintos dentro da
   mesma categoria, não apenas diferença de marca para um produto equivalente
   — um cuidado metodológico que vale registrar na conclusão.
3. Já Ovos é o item com menor variação percentual entre marcas (165%),
   sugerindo um mercado mais padronizado para esse produto nessa loja.
4. Arroz também é o item com maior dispersão de preços (desvio padrão de
   R$ 12,52), coerente com ser a categoria com mais produtos coletados (30) e
   maior variedade de tipos.

**Limitação de amostra registrada:** a categoria "óleo" ficou com apenas 4
produtos após o filtro de relevância (contra 13–30 dos demais itens), porque
ela corresponde, na fonte de dados, à categoria ampla "Temperos" (ver seção 5)
— dentro do limite de páginas coletadas, poucos itens eram efetivamente óleo
de cozinha. A equipe optou conscientemente por manter os 4 registros
disponíveis em vezavez de arriscar uma nova coleta (tokens de curta duração),
reconhecendo que a comparação de marcas para esse item específico tem uma
base amostral menor que a dos demais.

## 7. Pipeline e Dashboard

**Dashboard** (`dashboard.png`, Python + Matplotlib, critério 5): combina em
uma única figura o gráfico de preço médio por item e o gráfico de menor x
maior preço, dando uma visão consolidada da cesta em um único painel.

**Resposta à pergunta de negócio** ("Quais marcas de cada item básico têm o
menor e o maior preço no São Luiz, e qual a diferença entre elas?"), com base
em `resumo_menor_maior_preco.csv`:

| Item   | Mais barato                              | Preço | Mais caro                             | Preço  | Diferença |
|--------|-------------------------------------------|------:|-----------------------------------------|-------:|----------:|
| Arroz  | Arroz Ara Branco Longo Fino Tipo 1 1kg    | R$ 4,94 | Arroz Negro La Pastina 500g            | R$ 43,63 | +783% |
|:Feijão | Feijão de Corda Fibra Tipo 1 1kg          | R$ 6,58 | Feijão Verde Natan 1kg                  | R$ 32,41 | +393% |
| Açúcar | Açúcar Cristal Olho D'Água 1kg            | R$ 3,67 | Açúcar Mascavo União Pacote 1kg         | R$ 23,25 | +534% |
| Óleo   | Óleo de Soja Soya 900ml                   | R$ 9,46 | Óleo de Girassol Mazola 900ml           | R$ 27,26 | +188% |
| Ovos   | Ovo Branco Grande Cage-Free Avine (10un)  | R$ 9,67 | Ovo Branco Avine Extra (30un)           | R$ 25,63 | +165% |

Pipeline de automação proposto (agendamento diário): ver diagrama no
relatório final — em resumo, um agendador (cron/Task Scheduler ou um serviço
como Airflow) dispararia `coleta.py` diariamente, seguido de `tratamento.py`
e `analise.py` em sequência, com o token renovado a cada execução (via login
automatizado, se a empresa tivesse acordo formal de uso da API) e alertas em
caso de falha (401/403).


## 8. Aspectos Éticos e Legais

**Os dados coletados eram publicamente acessíveis?** Sim. As informações de
produto e preço estão disponíveis para qualquer visitante do site, sem
necessidade de login ou cadastro.

**Existia uma API que poderia ser utilizada como alternativa?** A própria fonte
de dados É consumida via uma API — porém não uma API pública e documentada,
oferecida oficialmente para desenvolvedores externos, e sim uma interface
interna do site, obtida por engenharia reversa do tráfego de rede (ver seção
Método de Coleta). Não foi identificada, no escopo desta atividade, uma API
pública oficial e documentada para os mesmos dados.

**Foram coletados dados pessoais?** Não. Os registros coletados contêm apenas
informações de produtos (nome, preço, código de barras, estoque, categoria);
nenhum dado de clientes, pedidos ou informações pessoais foi acessado ou
armazenado.

**A coleta poderia causar sobrecarga ao servidor?** Sim, caso feita sem
controle — e isso foi observado na prática: uma sequência de requisições em
ritmo elevado (mesmo com pausa de 1 segundo entre chamadas) foi suficiente para
que um mecanismo de proteção do servidor retornasse erro 403. Isso confirma que
o serviço monitora e limita o volume de requisições por origem.

**Que cuidados deveriam ser adotados caso esse processo fosse utilizado
continuamente por uma empresa?** Com base na experiência prática desta
atividade, recomenda-se: (1) limitar a frequência e o volume de requisições
(rate limiting no lado do cliente, com pausas e backoff progressivo em caso de
erro); (2) coletar apenas os dados estritamente necessários para a análise, em
vez de varrer o catálogo completo; (3) tratar o token de autenticação como uma
credencial sensível (nunca versionado em repositórios públicos, armazenado via
variável de ambiente); (4) monitorar respostas de erro (401/403/429) para
identificar bloqueios e ajustar o comportamento automaticamente; e (5) avaliar,
junto à empresa proprietária do site, a possibilidade de acordo formal de uso
de dados, já que se trata de uma API não documentada publicamente.

**Três boas práticas adotadas nesta coleta:**
1. Pausa de 1,5 segundo entre requisições consecutivas, para não sobrecarregar
   o servidor.
2. Limite de páginas por categoria, coletando apenas o volume necessário para
   a análise (não uma extração massiva do catálogo completo).
3. Token de autenticação mantido fora do código-fonte (variável de ambiente),
   evitando exposição de credenciais em caso de publicação do código.

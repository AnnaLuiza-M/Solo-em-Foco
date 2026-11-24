# Guia do código

## Acompanhe uma consulta

Use o botão **Testar em Juazeiro** como exemplo. A consulta começa em `consultarSolo()`, em [`frontend/app.js`](frontend/app.js), que envia latitude e longitude para `GET /api/consulta`. As coordenadas digitadas, a localização do navegador e os cliques no mapa chegam à mesma função.

1. Em [`backend/app.py`](backend/app.py), `consultar_solo()` recebe as coordenadas e chama `codigo_do_municipio()`.
2. Em [`backend/dados.py`](backend/dados.py), `carregar_base()` guarda em memória as estatísticas, os metadados e o índice espacial da malha do IBGE. `codigo_do_municipio()` usa esse índice para localizar o município. `consultar_rasters()` lê o valor de cada GeoTIFF no ponto e verifica se os três valores são válidos.
3. Em [`backend/interpretacao.py`](backend/interpretacao.py), `interpretar()` monta os textos de CE + PST, PST + pH e CE + pH. `comparar_com_estado()` posiciona cada valor em uma das faixas definidas pela mediana e pelo P95 da Bahia.
4. A API devolve o município, as estimativas e as interpretações em JSON. O JavaScript preenche os cartões com esses dados. Se a consulta falhar, `limparResultado()` apaga os valores e o marcador anteriores e exibe a mensagem de erro.

A API responde com HTTP 404 quando a coordenada fica fora da Bahia ou quando algum dos três mapas carece de um valor válido naquele ponto.

## De onde vêm os gráficos e as tabelas

A aba **Análise de dados** busca as medianas no CSV municipal por meio de `/api/analise/dispersao`. O gráfico muda os eixos conforme o par de indicadores selecionado. A rota `/api/analise` fornece as correlações armazenadas em `metadados.json` e as listas ordenadas a partir do CSV. A comparação usa os códigos IBGE dos dois municípios para buscar as respectivas linhas na mesma tabela.

O mapa usa `municipios_simplificados.geojson` para desenhar os limites municipais no navegador. A identificação do município no backend usa a malha do IBGE incluída em `data/municipios_bahia_ibge_2025.zip`.

## Reprocessar os dados

O script [`scripts/processar_bahia_ibge.py`](scripts/processar_bahia_ibge.py) verifica se os três GeoTIFFs usam a mesma grade. Depois seleciona os pixels com valores válidos nos três mapas e calcula as referências estaduais e as estatísticas por município. A correlação de Spearman usa as medianas municipais. Execute o comando abaixo na raiz do projeto quando precisar regenerar os arquivos.

```powershell
.\.venv\Scripts\python.exe scripts/processar_bahia_ibge.py
```

O script sobrescreve `data/municipios_estatisticas.csv`, `data/metadados.json` e `data/municipios_simplificados.geojson`. A aplicação lê esses arquivos prontos durante a execução.

## Conferir uma alteração

[Execute a suíte de testes e inicie o servidor](README.md#rodar-no-windows). Para conferir o resultado no navegador, use o exemplo de Juazeiro e depois consulte Salvador com latitude `-12.9722` e longitude `-38.5014`. Se a alteração envolver a aba **Análise de dados**, troque os pares no gráfico e compare dois municípios.

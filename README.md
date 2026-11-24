# Solo em Foco

O Solo em Foco é um protótipo de TCC em Engenharia de Software para consultar mapas de solo nos 417 municípios da Bahia. Por coordenadas, localização do navegador ou clique no mapa, o site identifica o município e mostra as estimativas de condutividade elétrica (CE), percentual de saturação por sódio (PST) e pH para aquele ponto.

A aba **Consultar meu solo** mostra os valores, explica os pares CE + PST, PST + pH e CE + pH e indica em que faixa da distribuição estadual cai cada valor. Na aba **Análise de dados**, é possível alternar entre três gráficos de dispersão, comparar dois municípios e baixar o CSV. A aba também lista os municípios com a maior CE mediana e os que têm a maior proporção de pixels com CE e PST acima dos respectivos P95 estaduais.

## Rodar no Windows

Use Python 3.11 ou 3.12 de 64 bits. Extraia o ZIP e abra a pasta que contém `requirements.txt`. Os mapas e as tabelas já estão em `data/`.

1. Execute `CONFIGURAR_WINDOWS.bat` para criar o ambiente virtual e instalar as dependências.
2. Execute `TESTAR_WINDOWS.bat`. A suíte desta versão tem 18 testes.
3. Execute `INICIAR_WINDOWS.bat` e deixe a janela aberta enquanto usar o site.
4. Abra [o site local](http://127.0.0.1:8000/) e clique em **Testar em Juazeiro**.

Para fazer os mesmos passos pelo PowerShell, execute os comandos abaixo na pasta do projeto.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

Com Python 3.11, use `py -3.11` no primeiro comando. Se a porta 8000 estiver ocupada, use `--port 8001` no último comando e abra [o site na porta 8001](http://127.0.0.1:8001/). Para encerrar o servidor, pressione **Ctrl+C**.

O Leaflet e as imagens de fundo do OpenStreetMap exigem conexão com a internet. Se o mapa estiver indisponível, use os campos de latitude e longitude.

## Como os dados foram preparados

Os três mapas preditivos da Embrapa cobrem a camada de 0 a 30 cm do solo, com resolução de cerca de 1 km. O recorte usa a malha do IBGE de 2025 e considera os centros dos pixels dentro dos limites municipais. Entraram no cálculo estadual 672.466 pixels com valores válidos para os três indicadores.

| Indicador | Mediana estadual | P95 estadual |
| --- | ---: | ---: |
| CE (dS/m) | 0,0133 | 1,016 |
| PST (%) | 0,1775 | 1,813 |
| pH | 5,52 | 6,87 |

A comparação do ponto com a Bahia usa faixas delimitadas pela mediana e pelo P95. O P95 descreve a distribuição dos valores no recorte e serve como referência estatística. Os pixels em EPSG:4326 foram contados sem ponderação pela área, e pixels próximos podem ter valores relacionados.

Cada ponto nos gráficos de dispersão representa um município. As correlações de Spearman entre as medianas municipais foram 0,6643 para CE e PST, 0,5423 para CE e pH e 0,3107 para PST e pH. Esses coeficientes descrevem associações. Nos gráficos, CE e PST usam a escala `log(1 + valor)` e os valores originais aparecem ao passar o cursor sobre os pontos.

Os mapas fornecem estimativas regionais. Laudos e decisões de manejo exigem amostras locais e avaliação técnica. O processamento encontrou zero pixels com CE de pelo menos 4 dS/m e um pixel com PST de pelo menos 15%. Essas contagens descrevem os mapas. O uso do limiar clássico de ECe para interpretar a CE estimada depende de validação metodológica. A base também carece de séries temporais e de dados sobre umidade, temperatura e qualidade da água, necessários para outros tipos de análise.

### Fontes

- [Embrapa GeoInfo — condutividade elétrica](https://geoinfo.dados.embrapa.br/datasets/bra_salinitymap030%3Ageonode%3Abra_salinitymap030/metadata_detail)
- [Embrapa GeoInfo — saturação por sódio](https://geoinfo.dados.embrapa.br/datasets/bra_espmap030%3Ageonode%3Abra_espmap030/metadata_detail)
- [Embrapa GeoInfo — pH](https://geoinfo.dados.embrapa.br/datasets/bra_phmap030%3Ageonode%3Abra_phmap030/metadata_detail)
- [IBGE — malha municipal da Bahia de 2025](https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2025/UFs/BA/)

Os mapas de CE, PST e pH são de Gustavo M. Vasques, Mauricio Rizzato Coelho, Ricardo de Oliveira Dart e Jesus F. Mansilla Baca, da Embrapa Solos. Os três GeoTIFFs deste projeto foram recortados para a Bahia a partir dos mapas nacionais, distribuídos sob a licença [CC BY-NC 3.0 BR](https://creativecommons.org/licenses/by-nc/3.0/br/), que exige atribuição e limita o uso a fins não comerciais. O GeoJSON da interface simplifica os limites da malha municipal do IBGE de 2025.

## API e código

Com o servidor rodando, consulte [a documentação da API](http://127.0.0.1:8000/docs). Estas são as rotas usadas pela interface e para checagem do servidor.

| Rota GET | Retorno |
| --- | --- |
| `/api/health` | Estado da API e total de municípios |
| `/api/consulta?lat=-9.513883&lon=-40.307956` | Município, estimativas e interpretação do ponto em Juazeiro |
| `/api/metadados` | Referências estaduais e dados de metodologia |
| `/api/municipios?limite=417` | Lista de municípios |
| `/api/municipios/{codigo}` | Estatísticas do município pelo código IBGE |
| `/api/municipios/geojson` | Limites municipais simplificados para o mapa |
| `/api/comparar?codigo1=2918407&codigo2=2907202` | Comparação entre Juazeiro e Casa Nova |
| `/api/analise` | Correlações e listas de municípios ordenadas por indicador |
| `/api/analise/dispersao` | Medianas municipais usadas nos gráficos |
| `/api/exportar/municipios.csv` | CSV com as estatísticas dos 417 municípios |

O [guia do código](GUIA_DO_CODIGO.md) acompanha uma consulta do navegador aos GeoTIFFs e descreve como regenerar as tabelas.

A execução é local. O arquivo `render.yaml` é um rascunho de configuração para uma futura publicação. Antes de publicar, a equipe precisa revisar HTTPS, registros de consultas com coordenadas, privacidade e o serviço que fornece as imagens do mapa.

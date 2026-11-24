from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

from .dados import (
    PASTA_DADOS,
    PASTA_SITE,
    carregar_base,
    codigo_do_municipio,
    consultar_rasters,
    preparar_json,
)
from .interpretacao import interpretar


app = FastAPI(
    title='Solo em Foco — Bahia',
    version='0.4.0',
    description='Consulta de CE, PST e pH estimados para os municípios da Bahia.'
)

# Mantemos estes nomes para os testes e para quem já usa o projeto.
store = carregar_base
interpret = interpretar


def buscar_municipio(codigo):
    municipio = carregar_base()['entries'].get(str(codigo))
    if municipio is None:
        raise HTTPException(status_code=404, detail='Município não encontrado na Bahia.')
    return municipio


@app.get('/')
def pagina_inicial():
    return FileResponse(PASTA_SITE / 'index.html')


@app.get('/app.css')
def arquivo_css():
    return FileResponse(PASTA_SITE / 'app.css', media_type='text/css')


@app.get('/app.js')
def arquivo_js():
    return FileResponse(PASTA_SITE / 'app.js', media_type='application/javascript')


@app.get('/api/health')
def verificar_api():
    base = carregar_base()
    return {
        'status': 'ok',
        'municipios': len(base['entries']),
        'recorte': base['meta']['recorte']
    }


@app.get('/api/metadados')
def consultar_metadados():
    return carregar_base()['meta']


@app.get('/api/municipios')
def listar_municipios(q: str = '', limite: int = Query(417, ge=1, le=417)):
    tabela = carregar_base()['df'].sort_values('municipio')
    if q:
        tabela = tabela[tabela['municipio'].str.contains(q, case=False, regex=False, na=False)]

    colunas = ['codigo_ibge', 'municipio', 'ce_mediana', 'pst_mediana',
               'ph_mediana', 'coincidencia_pct']
    return preparar_json(tabela.head(limite)[colunas].to_dict(orient='records'))


@app.get('/api/municipios/geojson')
def limites_municipais():
    return FileResponse(
        PASTA_DADOS / 'municipios_simplificados.geojson',
        media_type='application/geo+json'
    )


@app.get('/api/municipios/{codigo}')
def consultar_municipio(codigo: str):
    return buscar_municipio(codigo)


@app.get('/api/consulta')
def consultar_solo(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180)
):
    codigo = codigo_do_municipio(lat, lon)
    if codigo is None:
        raise HTTPException(status_code=404, detail='O ponto informado está fora da Bahia.')

    valores = consultar_rasters(lat, lon)
    if valores is None:
        raise HTTPException(status_code=404, detail='Não há dados válidos para este ponto.')

    cidade = buscar_municipio(codigo)
    metadados = carregar_base()['meta']
    return {
        'localizacao': {
            'latitude': lat,
            'longitude': lon,
            'municipio': cidade['municipio'],
            'codigo_ibge': codigo
        },
        'estimativas': valores,
        'interpretacao': interpretar(valores, metadados),
        'referencia': {
            'nome': 'Bahia — 417 municípios (IBGE 2025)',
            'p95': metadados['percentil95_referencia'],
            'mediana': metadados['mediana_referencia']
        }
    }


@app.get('/api/comparar')
def comparar_municipios(codigo1: str, codigo2: str):
    primeiro = buscar_municipio(codigo1)
    segundo = buscar_municipio(codigo2)
    indicadores = [
        'ce_mediana', 'pst_mediana', 'ph_mediana', 'ce_acima_p95_pct',
        'pst_acima_p95_pct', 'coincidencia_pct'
    ]

    diferencas = {}
    for indicador in indicadores:
        diferencas[indicador] = float(primeiro[indicador]) - float(segundo[indicador])

    return preparar_json({
        'regiao_a': primeiro,
        'regiao_b': segundo,
        'diferencas_a_menos_b': diferencas,
        'nota': 'Comparação exploratória entre municípios. O P95 não é limite agronômico.'
    })


@app.get('/api/analise')
def resumo_analise():
    base = carregar_base()
    tabela = base['df']
    metadados = base['meta']
    identificacao = ['codigo_ibge', 'municipio']

    ranking_ce = tabela.nlargest(10, 'ce_mediana')
    ranking_conjunto = tabela.nlargest(10, 'coincidencia_pct')

    return preparar_json({
        'referencia': metadados['referencia_percentis'],
        'p95': metadados['percentil95_referencia'],
        'correlacoes_spearman_medianas_municipais': metadados['correlacao_spearman_medianas_municipais'],
        'total_municipios': len(tabela),
        'top_ce_mediana': ranking_ce[identificacao + ['ce_mediana']].to_dict(orient='records'),
        'top_coincidencia': ranking_conjunto[identificacao + ['coincidencia_pct']].to_dict(orient='records'),
        'observacao': ('As correlações comparam medianas municipais estimadas. '
                       'Não mostram relação de causa e efeito.')
    })


@app.get('/api/analise/dispersao')
def dados_dispersao():
    colunas = ['codigo_ibge', 'municipio', 'ce_mediana', 'pst_mediana', 'ph_mediana']
    tabela = carregar_base()['df']

    return preparar_json({
        'pontos': tabela[colunas].to_dict(orient='records'),
        'observacao': 'Cada ponto representa um município, não uma amostra de solo.'
    })


@app.get('/api/exportar/municipios.csv')
def baixar_estatisticas():
    return FileResponse(
        PASTA_DADOS / 'municipios_estatisticas.csv',
        filename='estatisticas_417_municipios_bahia.csv',
        media_type='text/csv'
    )

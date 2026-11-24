import numpy as np
from fastapi.testclient import TestClient

from backend.app import app, interpret, store
from backend.dados import preparar_json


cliente = TestClient(app)


def test_api_ativa():
    resposta = cliente.get('/api/health')

    assert resposta.status_code == 200
    assert resposta.json()['municipios'] == 417
    assert '417' in resposta.json()['recorte']


def test_metadados_do_estado():
    resposta = cliente.get('/api/metadados')
    dados = resposta.json()

    assert resposta.status_code == 200
    assert dados['total_municipios'] == 417
    assert dados['total_pixels_validos'] == 672466
    assert 1 < dados['percentil95_referencia']['ce'] < 1.1
    assert 1.8 < dados['percentil95_referencia']['pst'] < 1.9


def test_lista_dos_municipios():
    resposta = cliente.get('/api/municipios?limite=417')
    municipios = resposta.json()

    assert resposta.status_code == 200
    assert len(municipios) == 417
    assert len({cidade['codigo_ibge'] for cidade in municipios}) == 417


def test_busca_de_municipio_por_nome():
    resposta = cliente.get('/api/municipios?q=juazeiro')

    assert resposta.status_code == 200
    assert len(resposta.json()) == 1
    assert resposta.json()[0]['municipio'] == 'Juazeiro'


def test_consulta_em_juazeiro():
    resposta = cliente.get('/api/consulta?lat=-9.513883&lon=-40.307956')
    dados = resposta.json()

    assert resposta.status_code == 200
    assert dados['localizacao']['municipio'] == 'Juazeiro'
    assert set(dados['estimativas']) == {'ce', 'pst', 'ph'}
    assert dados['referencia']['nome'].startswith('Bahia')

    interpretacao = dados['interpretacao']
    relacoes = {item['id'] for item in interpretacao['relacoes_conjuntas']}
    assert relacoes == {'ce_pst', 'pst_ph', 'ce_ph'}
    assert set(interpretacao['comparacao_bahia']) == {'ce', 'pst', 'ph'}

    for indicador in interpretacao['comparacao_bahia'].values():
        assert 'mediana' in indicador
        assert 'p95' in indicador
        assert 'posicao' in indicador


def test_consulta_em_salvador():
    resposta = cliente.get('/api/consulta?lat=-12.9722&lon=-38.5014')

    assert resposta.status_code == 200
    assert resposta.json()['localizacao']['municipio'] == 'Salvador'


def test_consulta_fora_da_bahia():
    resposta = cliente.get('/api/consulta?lat=-23.55&lon=-46.63')
    assert resposta.status_code == 404


def test_comparacao_de_municipios():
    resposta = cliente.get('/api/comparar?codigo1=2918407&codigo2=2907202')
    dados = resposta.json()

    assert resposta.status_code == 200
    assert dados['regiao_a']['municipio'] == 'Juazeiro'
    assert dados['regiao_b']['municipio'] == 'Casa Nova'
    assert 'ce_mediana' in dados['diferencas_a_menos_b']


def test_codigo_ibge_inexistente():
    resposta = cliente.get('/api/municipios/9999999')
    assert resposta.status_code == 404


def test_correlacoes_municipais():
    resposta = cliente.get('/api/analise')
    dados = resposta.json()
    corr = dados['correlacoes_spearman_medianas_municipais']

    assert resposta.status_code == 200
    assert dados['total_municipios'] == 417
    assert len(dados['top_ce_mediana']) == 10
    assert abs(corr['ce_mediana']['pst_mediana'] - 0.6643) < 0.001
    assert abs(corr['ce_mediana']['ph_mediana'] - 0.5423) < 0.001
    assert abs(corr['pst_mediana']['ph_mediana'] - 0.3107) < 0.001


def test_pontos_para_grafico():
    resposta = cliente.get('/api/analise/dispersao')
    pontos = resposta.json()['pontos']

    assert resposta.status_code == 200
    assert len(pontos) == 417
    assert {'ce_mediana', 'pst_mediana', 'ph_mediana'}.issubset(pontos[0])


def test_geojson_dos_municipios():
    resposta = cliente.get('/api/municipios/geojson')

    assert resposta.status_code == 200
    assert len(resposta.json()['features']) == 417


def test_download_csv():
    resposta = cliente.get('/api/exportar/municipios.csv')

    assert resposta.status_code == 200
    assert b'ce_mediana' in resposta.content


def test_arquivos_da_interface():
    for caminho in ['/', '/app.css', '/app.js']:
        assert cliente.get(caminho).status_code == 200

    html = cliente.get('/').text
    assert 'relacoesConjuntas' in html
    assert 'comparacaoEstadual' in html
    assert 'scatterPlot' in html


def test_interpretacao_com_limites_classicos():
    metadados = store()['meta']
    casos = [
        (0.3, 0.2, 'sem destaque'),
        (4.1, 0.2, 'CE acima'),
        (0.3, 16, 'PST acima'),
        (4.2, 16, 'dois limites')
    ]

    for ce, pst, texto_esperado in casos:
        resultado = interpret({'ce': ce, 'pst': pst, 'ph': 7.8}, metadados)
        titulo = resultado['titulo']

        if texto_esperado == 'sem destaque':
            assert 'PST' in resultado['relacoes_conjuntas'][0]['leitura']
        else:
            assert texto_esperado in titulo

        assert len(resultado['relacoes_conjuntas']) == 3
        assert 'não' in resultado['nota'].lower()


def test_comparacao_estadual_nao_e_diagnostico():
    metadados = store()['meta']
    valores = {'ce': 0.8, 'pst': 1.0, 'ph': 6.5}
    resultado = interpret(valores, metadados)

    for indicador in ['ce', 'pst', 'ph']:
        assert resultado['comparacao_bahia'][indicador]['faixa'] == 'entre_mediana_p95'

    assert 'estatístico' in resultado['comparacao_bahia']['ce']['explicacao']


def test_valores_nan_no_json():
    resultado = preparar_json({'valor': np.nan, 'quantidade': np.int64(3)})

    assert resultado['valor'] is None
    assert resultado['quantidade'] == 3


def test_consulta_deve_ter_coordenadas_validas():
    resposta = cliente.get('/api/consulta?lat=-100&lon=-40')
    assert resposta.status_code == 422

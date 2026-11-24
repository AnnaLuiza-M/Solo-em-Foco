import json
import math
from functools import lru_cache
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from shapely.geometry import Point
from shapely.strtree import STRtree


RAIZ = Path(__file__).resolve().parent.parent
PASTA_DADOS = RAIZ / 'data'
PASTA_SITE = RAIZ / 'frontend'


# Converte valores vazios do pandas/numpy para tipos aceitos pelo JSON.
def preparar_json(valor):
    if isinstance(valor, dict):
        return {chave: preparar_json(item) for chave, item in valor.items()}

    if isinstance(valor, (list, tuple)):
        return [preparar_json(item) for item in valor]

    if isinstance(valor, (float, np.floating)) and not math.isfinite(float(valor)):
        return None

    if isinstance(valor, np.integer):
        return int(valor)

    return valor


@lru_cache(maxsize=1)
def carregar_base():
    caminho_meta = PASTA_DADOS / 'metadados.json'
    with caminho_meta.open(encoding='utf-8') as arquivo:
        metadados = json.load(arquivo)

    tabela = pd.read_csv(
        PASTA_DADOS / 'municipios_estatisticas.csv',
        dtype={'codigo_ibge': str}
    )
    tabela['codigo_ibge'] = tabela['codigo_ibge'].str.zfill(7)

    por_codigo = {}
    for linha in tabela.to_dict(orient='records'):
        por_codigo[linha['codigo_ibge']] = preparar_json(linha)

    arquivo_ibge = PASTA_DADOS / 'municipios_bahia_ibge_2025.zip'
    municipios = gpd.read_file(f'zip://{arquivo_ibge}').to_crs('EPSG:4326')
    municipios['CD_MUN'] = municipios['CD_MUN'].astype(str).str.zfill(7)

    poligonos = list(municipios.geometry)
    return {
        'meta': metadados,
        'df': tabela,
        'entries': por_codigo,
        'tree': STRtree(poligonos),
        'codes': municipios['CD_MUN'].tolist()
    }


def codigo_do_municipio(latitude, longitude):
    base = carregar_base()
    ponto = Point(longitude, latitude)
    encontrados = base['tree'].query(ponto, predicate='intersects')

    if len(encontrados) == 0:
        return None

    indice = int(encontrados[0])
    return base['codes'][indice]


def consultar_rasters(latitude, longitude):
    valores = {}

    for indicador in ('ce', 'pst', 'ph'):
        caminho = PASTA_DADOS / f'{indicador}_bahia.tif'
        with rasterio.open(caminho) as mapa:
            limites = mapa.bounds
            if not (limites.left <= longitude < limites.right):
                return None
            if not (limites.bottom < latitude <= limites.top):
                return None

            amostra = next(mapa.sample([(longitude, latitude)], masked=True))[0]
            if np.ma.is_masked(amostra):
                return None

            numero = float(amostra)
            if not math.isfinite(numero) or numero == mapa.nodata:
                return None

            valores[indicador] = numero

    return valores

"""Gera as tabelas municipais a partir da malha do IBGE e dos mapas da Embrapa."""

import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import geometry_mask, geometry_window
from shapely.geometry import mapping


RAIZ = Path(__file__).resolve().parents[1]
DADOS = RAIZ / 'data'


def abrir_municipios():
    caminho = DADOS / 'municipios_bahia_ibge_2025.zip'
    municipios = gpd.read_file(f'zip://{caminho}')

    if len(municipios) != 417:
        raise ValueError('A malha do IBGE não tem os 417 municípios esperados.')
    if municipios['CD_MUN'].nunique() != 417:
        raise ValueError('Existem códigos municipais repetidos.')
    if not municipios.geometry.is_valid.all():
        raise ValueError('A malha tem geometrias inválidas.')

    municipios['codigo_ibge'] = municipios['CD_MUN'].astype(str).str.zfill(7)
    municipios = municipios.to_crs('EPSG:4326')
    return municipios.sort_values(['NM_MUN', 'codigo_ibge']).reset_index(drop=True)


def verificar_mapas(mapa_ce, mapa_pst, mapa_ph):
    outros = [mapa_pst, mapa_ph]
    for mapa in outros:
        if mapa.crs != mapa_ce.crs or mapa.transform != mapa_ce.transform:
            raise ValueError('Os GeoTIFFs não usam a mesma grade espacial.')
        if mapa.shape != mapa_ce.shape:
            raise ValueError('Os GeoTIFFs têm tamanhos diferentes.')


def selecionar_pixels(bandas, dentro_do_municipio):
    # Um pixel só entra na análise quando os três indicadores são válidos.
    validos = dentro_do_municipio.copy()
    for banda in bandas.values():
        validos &= ~np.ma.getmaskarray(banda)
        validos &= np.isfinite(banda.data)
        validos &= banda.data != -9999
    return validos


def estatisticas_municipio(municipio, mapas, p95_estadual):
    poligono = [mapping(municipio.geometry)]
    janela = geometry_window(mapas['ce'], poligono)
    formato = (int(janela.height), int(janela.width))
    mascara = geometry_mask(
        poligono,
        out_shape=formato,
        transform=mapas['ce'].window_transform(janela),
        invert=True,
        all_touched=False
    )

    bandas = {}
    for nome, mapa in mapas.items():
        bandas[nome] = mapa.read(1, window=janela, masked=True)

    validos = selecionar_pixels(bandas, mascara)
    quantidade = int(validos.sum())
    if quantidade == 0:
        raise ValueError(f'Sem dados nos mapas para {municipio.NM_MUN}.')

    valores = {}
    for nome, banda in bandas.items():
        valores[nome] = banda.data[validos].astype('float64')

    linha = {
        'codigo_ibge': municipio.codigo_ibge,
        'municipio': municipio.NM_MUN,
        'area_ibge_km2': float(municipio.AREA_KM2),
        'pixels_validos': quantidade
    }

    for nome, numeros in valores.items():
        linha[f'{nome}_mediana'] = float(np.median(numeros))
        linha[f'{nome}_media'] = float(np.mean(numeros))
        linha[f'{nome}_min'] = float(np.min(numeros))
        linha[f'{nome}_max'] = float(np.max(numeros))
        linha[f'{nome}_p95'] = float(np.percentile(numeros, 95))

    ce_maior = valores['ce'] > p95_estadual['ce']
    pst_maior = valores['pst'] > p95_estadual['pst']
    os_dois = ce_maior & pst_maior
    quantidade_juntos = int(os_dois.sum())

    linha['ce_acima_p95_n'] = int(ce_maior.sum())
    linha['pst_acima_p95_n'] = int(pst_maior.sum())
    linha['coincidencia_n'] = quantidade_juntos
    linha['ce_acima_p95_pct'] = float(ce_maior.mean() * 100)
    linha['pst_acima_p95_pct'] = float(pst_maior.mean() * 100)
    linha['coincidencia_pct'] = float(os_dois.mean() * 100)
    linha['ph_mediana_coincidencia'] = (
        float(np.median(valores['ph'][os_dois])) if quantidade_juntos else np.nan
    )
    linha['ce_ge4_n'] = int((valores['ce'] >= 4).sum())
    linha['pst_ge15_n'] = int((valores['pst'] >= 15).sum())
    linha['ce_ge4_pst_ge15_n'] = int(((valores['ce'] >= 4) & (valores['pst'] >= 15)).sum())
    return linha


def calcular_referencia(municipios, mapas):
    mapa_ce = mapas['ce']
    poligonos = [mapping(geometria) for geometria in municipios.geometry]
    mascara_bahia = geometry_mask(
        poligonos,
        out_shape=mapa_ce.shape,
        transform=mapa_ce.transform,
        invert=True,
        all_touched=False
    )
    bandas = {nome: mapa.read(1, masked=True) for nome, mapa in mapas.items()}
    validos = selecionar_pixels(bandas, mascara_bahia)

    valores_bahia = {}
    for nome, banda in bandas.items():
        valores_bahia[nome] = banda.data[validos].astype('float64')

    p95 = {nome: float(np.percentile(numeros, 95)) for nome, numeros in valores_bahia.items()}
    mediana = {nome: float(np.median(numeros)) for nome, numeros in valores_bahia.items()}
    p25 = {nome: float(np.percentile(numeros, 25)) for nome, numeros in valores_bahia.items()}
    p75 = {nome: float(np.percentile(numeros, 75)) for nome, numeros in valores_bahia.items()}

    return int(validos.sum()), p95, mediana, p25, p75


def montar_metadados(total_pixels, p95, mediana, p25, p75, correlacoes):
    return {
        'recorte': 'Estado da Bahia — todos os 417 municípios (IBGE 2025)',
        'total_municipios': 417,
        'total_pixels_validos': total_pixels,
        'referencia_percentis': 'Todos os pixels com CE, PST e pH válidos dentro dos 417 municípios da Bahia (IBGE 2025)',
        'percentil95_referencia': p95,
        'mediana_referencia': mediana,
        'percentil25_referencia': p25,
        'percentil75_referencia': p75,
        'correlacao_spearman_medianas_municipais': correlacoes,
        'metodologia': ('Centros dos pixels dentro dos municípios do IBGE 2025; mapas preditivos, '
                        '~1 km, 0–30 cm. P95 estadual não é limite de risco. '
                        'Pixels em EPSG:4326 não foram ponderados por área e possuem dependência espacial.'),
        'malha': 'IBGE 2025 — BA_Municipios_2025.zip',
        'fonte_ibge': 'https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2025/UFs/BA/',
        'fonte_embrapa': 'https://geoinfo.dados.embrapa.br/',
        'limites_classicos_apenas_informativos': {'ce_ds_m': 4, 'pst_pct': 15},
        'resolucao': 'aproximadamente 1 km',
        'profundidade_cm': '0–30',
        'versao': '0.4.0',
        'arquivos_fonte': {
            'ce': 'Embrapa CE 0–30 cm',
            'pst': 'Embrapa saturação por sódio 0–30 cm',
            'ph': 'Embrapa pH 0–30 cm'
        },
        'referencia': 'Bahia — 417 municípios (IBGE 2025)',
        'aviso_cientifico': ('Os mapas são estimativas. Não substituem amostras de solo '
                             'nem permitem recomendar irrigação ou corretivos.')
    }


def main():
    municipios = abrir_municipios()

    with rasterio.open(DADOS / 'ce_bahia.tif') as mapa_ce, \
         rasterio.open(DADOS / 'pst_bahia.tif') as mapa_pst, \
         rasterio.open(DADOS / 'ph_bahia.tif') as mapa_ph:

        verificar_mapas(mapa_ce, mapa_pst, mapa_ph)
        mapas = {'ce': mapa_ce, 'pst': mapa_pst, 'ph': mapa_ph}
        total_pixels, p95, mediana, p25, p75 = calcular_referencia(municipios, mapas)

        linhas = []
        for indice, municipio in municipios.iterrows():
            linhas.append(estatisticas_municipio(municipio, mapas, p95))
            if (indice + 1) % 100 == 0:
                print(f'{indice + 1} municípios processados')

    tabela = pd.DataFrame(linhas)
    if int(tabela['pixels_validos'].sum()) != total_pixels:
        raise ValueError('A contagem municipal de pixels é diferente da contagem estadual.')

    tabela.to_csv(DADOS / 'municipios_estatisticas.csv', index=False, encoding='utf-8-sig')

    correlacoes = (
        tabela[['ce_mediana', 'pst_mediana', 'ph_mediana']]
        .corr(method='spearman')
        .round(4)
        .to_dict()
    )

    mapa_municipios = municipios[['codigo_ibge', 'NM_MUN', 'geometry']].copy()
    mapa_municipios = mapa_municipios.rename(columns={'NM_MUN': 'municipio'})
    mapa_municipios['geometry'] = mapa_municipios.geometry.simplify(0.009, preserve_topology=True)
    mapa_municipios.to_file(DADOS / 'municipios_simplificados.geojson', driver='GeoJSON')

    metadados = montar_metadados(total_pixels, p95, mediana, p25, p75, correlacoes)
    with (DADOS / 'metadados.json').open('w', encoding='utf-8') as arquivo:
        json.dump(metadados, arquivo, indent=2, ensure_ascii=False)

    print(f'Concluído: {len(tabela)} municípios, {total_pixels} pixels válidos')
    print('P95 CE:', round(p95['ce'], 3), 'P95 PST:', round(p95['pst'], 3))


if __name__ == '__main__':
    main()

from .dados import preparar_json


NOMES = {
    'ce': 'Condutividade elétrica',
    'pst': 'Sódio trocável (PST)',
    'ph': 'pH'
}


def comparar_com_estado(valores, metadados):
    resultado = {}

    for indicador, valor in valores.items():
        mediana = float(metadados['mediana_referencia'][indicador])
        p95 = float(metadados['percentil95_referencia'][indicador])

        if valor > p95:
            faixa = 'acima_p95'
            posicao = 'acima do P95 estadual'
        elif valor < mediana:
            faixa = 'abaixo_mediana'
            posicao = 'abaixo da mediana estadual'
        else:
            faixa = 'entre_mediana_p95'
            posicao = 'entre a mediana e o P95 estadual'

        if indicador == 'ph':
            explicacao = 'A posição do pH não indica, sozinha, se o solo é adequado para uma cultura.'
        elif faixa == 'acima_p95':
            explicacao = 'O valor está entre os mais altos da Bahia, mas isso não comprova risco agronômico.'
        else:
            explicacao = 'Esse posicionamento é apenas estatístico, não um diagnóstico do solo.'

        resultado[indicador] = {
            'nome': NOMES[indicador],
            'valor': valor,
            'mediana': mediana,
            'p95': p95,
            'faixa': faixa,
            'posicao': posicao,
            'explicacao': explicacao
        }

    return resultado


def interpretar(valores, metadados):
    ce = float(valores['ce'])
    pst = float(valores['pst'])
    ph = float(valores['ph'])

    ce_acima_limite = ce >= 4
    pst_acima_limite = pst >= 15
    ce_acima_p95 = ce > metadados['percentil95_referencia']['ce']
    pst_acima_p95 = pst > metadados['percentil95_referencia']['pst']

    # Esses limites são referências clássicas, não um laudo do ponto consultado.
    if ce_acima_limite and pst_acima_limite:
        titulo = 'CE e PST ultrapassam os dois limites de referência'
        explicacao = ('Os dois indicadores superam os limites clássicos. '
                      'Precisamos de amostras locais para confirmar a condição do solo.')
        leitura_ce_pst = 'CE e PST estão acima dos limites informativos de 4 dS/m e 15%.'
    elif ce_acima_limite:
        titulo = 'CE acima do limite clássico informativo'
        explicacao = ('A CE estimada ultrapassa 4 dS/m, mas a PST está abaixo de 15%. '
                      'O resultado precisa de confirmação local.')
        leitura_ce_pst = 'A CE está acima de 4 dS/m, enquanto a PST não ultrapassa 15%.'
    elif pst_acima_limite:
        titulo = 'PST acima do limite clássico informativo'
        explicacao = ('A PST estimada ultrapassa 15%, mas a CE está abaixo de 4 dS/m. '
                      'O resultado precisa de confirmação local.')
        leitura_ce_pst = 'A PST está acima de 15%, enquanto a CE não ultrapassa 4 dS/m.'
    elif ce_acima_p95 and pst_acima_p95:
        titulo = 'CE e PST relativamente maiores na Bahia'
        explicacao = ('Os dois indicadores superam o P95 estadual, mas não os limites clássicos. '
                      'É um destaque estatístico, não um diagnóstico.')
        leitura_ce_pst = 'CE e PST estão entre os valores mais altos da Bahia, mas abaixo dos limites clássicos.'
    elif ce_acima_p95:
        titulo = 'CE relativamente maior na Bahia'
        explicacao = 'A CE supera o P95 estadual, mas não 4 dS/m. Isso não comprova salinidade.'
        leitura_ce_pst = 'A CE se destaca em relação à Bahia; a PST não ultrapassa 15%.'
    elif pst_acima_p95:
        titulo = 'PST relativamente maior na Bahia'
        explicacao = 'A PST supera o P95 estadual, mas não 15%. Isso não comprova sodicidade.'
        leitura_ce_pst = 'A PST se destaca em relação à Bahia; a CE não ultrapassa 4 dS/m.'
    else:
        titulo = 'CE e PST sem destaque extremo estadual'
        explicacao = ('CE e PST estão abaixo dos limites clássicos e do P95 da Bahia. '
                      'Isso não descarta situações diferentes no terreno.')
        leitura_ce_pst = 'CE e PST não ultrapassam os limites clássicos nem o P95 estadual.'

    if ph < 7:
        faixa_ph = 'ácido'
    elif ph > 7:
        faixa_ph = 'alcalino'
    else:
        faixa_ph = 'neutro'

    if pst_acima_limite:
        leitura_pst_ph = (f'O pH estimado é {faixa_ph} e a PST ultrapassa 15%. '
                          'A condição de sodicidade precisa ser verificada em campo.')
    else:
        leitura_pst_ph = (f'O pH estimado é {faixa_ph} e a PST está abaixo de 15%. '
                          'Essa estimativa não exclui diferenças locais.')

    if ce_acima_limite:
        leitura_ce_ph = (f'A CE ultrapassa 4 dS/m e o pH estimado é {faixa_ph}. '
                         'Os dois indicadores avaliam características diferentes do solo.')
    else:
        leitura_ce_ph = (f'A CE não ultrapassa 4 dS/m e o pH estimado é {faixa_ph}. '
                         'A acidez deve ser analisada conforme a cultura e outros nutrientes.')

    relacoes = [
        {
            'id': 'ce_pst',
            'titulo': 'Sais e sódio no solo — CE + PST',
            'leitura': leitura_ce_pst,
            'importancia': ('O acúmulo de sais pode dificultar a absorção de água. '
                           'O excesso de sódio trocável pode prejudicar a infiltração. '
                           'Os dois problemas não são iguais.')
        },
        {
            'id': 'pst_ph',
            'titulo': 'Sódio e alcalinidade — PST + pH',
            'leitura': leitura_pst_ph,
            'importancia': ('A PST indica a proporção estimada de sódio trocável. '
                           'O pH ajuda a interpretar acidez e alcalinidade, mas não confirma sodicidade sozinho.')
        },
        {
            'id': 'ce_ph',
            'titulo': 'Sais e acidez — CE + pH',
            'leitura': leitura_ce_ph,
            'importancia': ('A CE está relacionada aos sais solúveis, enquanto o pH indica acidez ou alcalinidade. '
                           'O pH também influencia a disponibilidade de nutrientes.')
        }
    ]

    resposta = {
        'titulo': titulo,
        'explicacao': explicacao,
        'contexto_ph': f'O pH estimado é {faixa_ph} (comparado a pH 7).',
        'ce_acima_p95': ce_acima_p95,
        'pst_acima_p95': pst_acima_p95,
        'relacoes_conjuntas': relacoes,
        'comparacao_bahia': comparar_com_estado(valores, metadados),
        'sugestao': ('Antes de decidir sobre irrigação, adubação, corretivos ou culturas, '
                    'procure orientação técnica e faça uma análise de solo no local.'),
        'nota': ('Mapas estimados da Embrapa, resolução aproximada de 1 km e profundidade de 0–30 cm. '
                 'P95 não é limite de risco; os limites clássicos dependem de confirmação metodológica. '
                 'O resultado não substitui uma análise laboratorial.')
    }
    return preparar_json(resposta)

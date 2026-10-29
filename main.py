import os
import re
from zipfile import BadZipFile

from dotenv import load_dotenv
from flask import Flask, abort, make_response, render_template, request, send_file, url_for

load_dotenv()

from fotos import buscar_foto, normalizar_nome, binomio, otimizar_foto
from i18n import contexto_idioma, idioma_atual, traduzir
from ocorrencias import carregar_appendix, caminho_appendix, coordenadas_validas

app = Flask(__name__)
app.json.ensure_ascii = False
app.json.sort_keys = False
app.context_processor(contexto_idioma)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FOTOS_DIR = os.path.join(BASE_DIR, 'static', 'fotos')
FOTOS_LOCAIS = {
    normalizar_nome(os.path.splitext(arquivo)[0].replace('_', ' ')): arquivo
    for arquivo in os.listdir(FOTOS_DIR)
    if arquivo.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')) and arquivo != 'sem_foto.jpg'
}
FOTOS_LOCAIS_BINOMIO = {}
for nome, arquivo in FOTOS_LOCAIS.items():
    if binomio(nome):
        FOTOS_LOCAIS_BINOMIO.setdefault(binomio(nome), arquivo)


@app.after_request
def cache_arquivos_estaticos(resposta):
    if request.endpoint == 'static' and resposta.status_code == 200:
        resposta.cache_control.public = True
        resposta.cache_control.max_age = 604800 if '/catalogo/' in request.path else 3600
    return resposta


def extrair_bibliografia(texto_bruto):
    referencias = []
    for linha in str(texto_bruto or '').splitlines():
        linha = linha.strip()
        if len(linha) < 5:
            continue
        match = re.search(r'https?://[^\s]+|www\.[^\s]+', linha)
        url = match.group(0).rstrip('.,;') if match else ''
        if url.startswith('www.'):
            url = 'https://' + url
        referencias.append({'titulo': linha, 'url': url})
    return referencias


def montar_foto(nome_cientifico, nomes_originais=()):
    nomes = list(dict.fromkeys([nome_cientifico, *nomes_originais]))
    for nome in nomes:
        foto = buscar_foto(nome)
        if foto:
            return foto
    for nome in nomes:
        arquivo = FOTOS_LOCAIS.get(normalizar_nome(nome))
        if not arquivo and binomio(nome):
            arquivo = FOTOS_LOCAIS_BINOMIO.get(binomio(nome))
        if arquivo:
            url = url_for('static', filename='fotos/' + arquivo)
            return otimizar_foto({'url': url, 'url_media': url, 'autor': '', 'licenca': '', 'fonte': ''})
    url = url_for('static', filename='fotos/sem_foto.jpg')
    return {'url': url, 'url_media': url, 'autor': '', 'licenca': '', 'fonte': ''}


def preparar_planta(planta, idioma, detalhes=True):
    planta['nome_popular'] = (planta['nomes_populares'] or [planta['nome_cientifico']])[0]
    planta['origem'] = '\n'.join(planta['habitats']) or traduzir('Não informado', idioma)
    planta['importancia'] = '; '.join(planta['tags']) or traduzir('Uso não documentado', idioma)
    if detalhes:
        planta['bibliografia'] = extrair_bibliografia('\n'.join(planta['referencias']))
    planta['foto'] = montar_foto(planta['nome_cientifico'],
                               [o['nome_original'] for o in planta['ocorrencias']])
    return planta


@app.route('/')
def index():
    idioma = idioma_atual()
    try:
        plantas, stats, filtros = carregar_appendix(idioma)
    except (OSError, ValueError, KeyError, BadZipFile):
        app.logger.exception('Falha na leitura do Appendix S1')
        return render_template('erro.html'), 503
    for planta in plantas:
        preparar_planta(planta, idioma, detalhes=False)
    catalogo = []
    for indice, p in enumerate(plantas, 1):
        busca = list(dict.fromkeys([
            *p['nomes_populares'], p['nome_cientifico'], p['familia'], p['origem'],
            p['importancia'], *p['tags'], *p['partes_tags'],
            *[o['id'] for o in p['ocorrencias']], *[o['nome_original'] for o in p['ocorrencias']],
        ]))
        catalogo.append({
            'id': indice, 'nome_popular': p['nome_popular'], 'nome_cientifico': p['nome_cientifico'],
            'familia': p['familia'], 'tags': p['tags'], 'partes': p['partes_tags'],
            'busca': ' '.join(busca), 'imagem': p['foto']['url_media'], 'alternativa': p['foto']['url'],
        })
    plantas_mapa = [{
        **{chave: p[chave] for chave in ('nome_popular', 'nome_cientifico', 'familia', 'tags')},
        'pontos_gps': [ponto for ponto in p['pontos_gps'] if ponto['nivel'] == 'occurrence'],
    } for p in plantas]
    resposta = make_response(render_template(
        'home.html', catalogo=catalogo, plantas_mapa=plantas_mapa, stats=stats, filtros=filtros,
    ))
    resposta.set_cookie('munguba_lang', idioma, max_age=31536000, samesite='Lax', httponly=True)
    resposta.headers['Cache-Control'] = 'private, no-cache'
    return resposta


@app.route('/taxon/<int:indice>')
def detalhe_taxon(indice):
    idioma = idioma_atual()
    try:
        plantas, _, _ = carregar_appendix(idioma)
    except (OSError, ValueError, KeyError, BadZipFile):
        app.logger.exception('Falha na leitura do Appendix S1')
        return render_template('erro.html'), 503
    if indice < 1 or indice > len(plantas):
        abort(404)
    planta = preparar_planta(plantas[indice - 1], idioma)
    return render_template('detalhe.html', p=planta, indice=indice)


@app.route('/exportar-dados')
def baixar_planilha():
    caminho = caminho_appendix(idioma_atual())
    try:
        return send_file(caminho, as_attachment=True, download_name=caminho.name)
    except FileNotFoundError:
        return render_template('erro.html'), 404


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)

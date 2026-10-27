import os
import re
from zipfile import BadZipFile

from dotenv import load_dotenv
from flask import Flask, abort, make_response, render_template, send_file, url_for

load_dotenv()

from fotos import buscar_foto, normalizar_nome, binomio
from i18n import contexto_idioma, idioma_atual, traduzir
from ocorrencias import carregar_appendix, caminho_appendix, coordenadas_validas

app = Flask(__name__)
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


def montar_foto(nome_cientifico):
    arquivo = FOTOS_LOCAIS.get(normalizar_nome(nome_cientifico))
    if not arquivo and binomio(nome_cientifico):
        arquivo = FOTOS_LOCAIS_BINOMIO.get(binomio(nome_cientifico))
    if arquivo:
        url = url_for('static', filename='fotos/' + arquivo)
        return {'url': url, 'url_media': url, 'autor': '', 'licenca': '', 'fonte': ''}
    foto = buscar_foto(nome_cientifico)
    if foto:
        return foto
    url = url_for('static', filename='fotos/sem_foto.jpg')
    return {'url': url, 'url_media': url, 'autor': '', 'licenca': '', 'fonte': ''}


def preparar_planta(planta, idioma):
    planta['nome_popular'] = (planta['nomes_populares'] or [planta['nome_cientifico']])[0]
    planta['origem'] = '\n'.join(planta['habitats']) or traduzir('Não informado', idioma)
    planta['importancia'] = '; '.join(planta['tags']) or traduzir('Uso não documentado', idioma)
    planta['bibliografia'] = extrair_bibliografia('\n'.join(planta['referencias']))
    planta['foto'] = montar_foto(planta['nome_cientifico'])
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
        preparar_planta(planta, idioma)
    plantas_mapa = [{chave: p[chave] for chave in (
        'nome_popular', 'nome_cientifico', 'familia', 'tags', 'pontos_gps'
    )} for p in plantas]
    resposta = make_response(render_template(
        'home.html', plantas=plantas, plantas_mapa=plantas_mapa, stats=stats, filtros=filtros,
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

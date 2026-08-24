from flask import render_template, send_file
import os
import re

from models import app, db, Taxon, Bioeconomico, Occurrence

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DADOS_DIR = os.path.join(BASE_DIR, "dados")

CATEGORIAS_MAP = {
    "Alimentação e Nutrição": [
        "alimenta", "alimento", "alinet", "nuri", "nurti", "nutra", "nutri", "animal", "gado", "ração", "pasto"
    ],
    "Artesanato e Cultura": [
        "artesan", "cultura"
    ],
    "Construção, Madeira e Indústria": [
        "constru", "madeir", "industr", "indústr", "energia", "enérgia", "agroindustrial", "móveis", "estaca", "viga",
        "resina"
    ],
    "Cosméticos e Higiene": [
        "cosmetic", "cosmétic", "higiene", "hiegiene", "aromática", "beleza", "perfume", "sabonete", "oleo"
    ],
    "Medicinal e Farmacológico": [
        "medicin", "madicin", "farmaco", "famacol", "terapeutico", "fitoterapico", "inseticida"
    ],
    "Ornamental e Paisagismo": [
        "ornamental", "paisag", "paisaf", "jardim", "flor"
    ],
    "Serviços Ambientais": [
        "ambient", "serviço", "srviço", "restaura", "recupera", "sombra", "solo", "reflorestamento", "nascente"
    ]
}

PARTES_MAP = {
    "Planta": ["planta"], "Fruto e Polpa": ["fruto", "polpa"], "Folha": ["folha"],
    "Semente": ["semente"], "Caule": ["tronco", "madeira"], "Raiz": ["raiz"],
    "Flor": ["flor"], "Exsudato": ["latex", "resina"], "Casca": ["casca"], "Palmito": ["palmito"]
}


def classificar_tags(texto, mapa):
    tags = set()
    if not texto: return []
    t_lower = str(texto).lower()
    for cat, termos in mapa.items():
        if any(termo in t_lower for termo in termos): tags.add(cat)
    return list(tags)


def extrair_bibliografia(texto_bruto):
    lista_bibliografia = []
    if not texto_bruto or str(texto_bruto).lower() == 'nan':
        return lista_bibliografia

    linhas = str(texto_bruto).replace('\r\n', '\n').replace('\r', '\n').split('\n')
    for linha in linhas:
        linha = linha.strip().replace('"', '').replace("'", "")
        if len(linha) < 5: continue

        titulo, url = "", ""
        if '|' in linha:
            partes = linha.split('|', 1)
            titulo = partes[0].strip()
            url_cand = partes[1].strip()
            if 'http' in url_cand or 'www' in url_cand:
                url = url_cand if url_cand.startswith('http') else "https://" + url_cand
            else:
                titulo = linha
        else:
            match_link = re.search(r'(https?://[^\s]+)|(www\.[^\s]+)', linha)
            if match_link:
                url_encontrada = match_link.group(0)
                texto_sem_link = linha.replace(url_encontrada, "").strip()
                titulo = texto_sem_link.rstrip(' .:,;-') if len(texto_sem_link) > 3 else "Acessar Fonte / Artigo"
                url = url_encontrada if url_encontrada.startswith('http') else "https://" + url_encontrada
            else:
                titulo = linha

        lista_bibliografia.append({'titulo': titulo, 'url': url})
    return lista_bibliografia


@app.route("/")
def index():
    print("📡 BUSCANDO DADOS NO MYSQL...")

    # 1. Faz a busca no banco de dados juntando TAXON e BIOECONOMICO
    resultados_db = db.session.query(Taxon, Bioeconomico).join(Bioeconomico,
                                                               Taxon.id_taxon == Bioeconomico.id_taxon).all()

    plantas_processadas = []
    plantas_vistas = set()  # <--- Nossa "memória" focada no NOME da planta

    total_geo = 0
    stats_categorias = {cat: 0 for cat in CATEGORIAS_MAP.keys()}
    stats_categorias["Outros"] = 0

    for taxon, bio in resultados_db:
        nome_cientifico = taxon.scientificNameAccepted or "Sp."

        # O SEGREDO ESTÁ AQUI: Validar pelo nome, ignorando maiúsculas e espaços extras!
        nome_chave = nome_cientifico.strip().lower()

        # Se o nome da planta já estiver na memória, pula a contagem!
        if nome_chave in plantas_vistas:
            continue

        # Marca a planta como "já vista" adicionando o nome na memória
        plantas_vistas.add(nome_chave)

        # 2. Busca as ocorrências (coordenadas GPS)
        ocorrencias = Occurrence.query.filter_by(id_taxon=taxon.id_taxon).all()
        pontos_gps = []
        for occ in ocorrencias:
            if occ.decimalLatitude and occ.decimalLongitude:
                pontos_gps.append({'lat': occ.decimalLatitude, 'lng': occ.decimalLongitude})

        if pontos_gps:
            total_geo += 1

        # 3. Classifica as tags baseadas no texto salvo no banco
        tags = classificar_tags(bio.potencial_bioeconomico, CATEGORIAS_MAP) or ["Outros"]
        for t in tags:
            if t in stats_categorias:
                stats_categorias[t] += 1
            else:
                stats_categorias["Outros"] += 1

        tags_partes = classificar_tags(bio.partes_planta, PARTES_MAP)

        # 4. Formata os links da bibliografia
        lista_bibliografia = extrair_bibliografia(bio.referencias_bibliograficas)

        # 5. Monta o dicionário que o HTML espera
        planta = {
            "nome_popular": bio.nome_popular or taxon.scientificNameAccepted,
            "nome_cientifico": nome_cientifico,
            "familia": taxon.familia or "-",
            "tags": tags,
            "partes_tags": tags_partes,
            "origem": bio.origem_habitat or "-",
            "importancia": bio.importancia or "Sem descrição.",
            "pontos_gps": pontos_gps,
            "bibliografia": lista_bibliografia
        }
        plantas_processadas.append(planta)

    stats = {
        "total_especies": len(plantas_processadas),
        "total_geo": total_geo,
        "por_categoria": stats_categorias
    }

    return render_template("home.html", plantas=plantas_processadas, stats=stats,
                           filtros={"categorias": list(CATEGORIAS_MAP.keys()), "partes": list(PARTES_MAP.keys())})


@app.route('/exportar-dados')
def baixar_planilha():
    caminho_do_arquivo = os.path.join(DADOS_DIR, 'BancoDados_munguba_Darwin_core.xlsx')
    try:
        return send_file(caminho_do_arquivo, as_attachment=True, download_name='BancodeDados_MungubaDWC.xlsx')
    except FileNotFoundError:
        return "Erro: O arquivo ainda não foi colocado na pasta.", 404


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
from flask import Flask, render_template, request, redirect, url_for
import gspread
from google.oauth2.service_account import Credentials
import os
import json
import unicodedata
import re
from pygbif import occurrences

app = Flask(__name__)

# --- CONFIGURAÇÕES ---
BASE_DIR = os.path.dirname(__file__)
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
DATA_FILE = os.path.join(BACKEND_DIR, "dados_processados.json")

# --- MAPAS ---
CATEGORIAS_MAP = {
    "Medicinal e Farmacológico": ["medicinal", "farmaco", "terapeutico", "fitoterapico"],
    "Alimentação e Nutrição": ["alimento", "nutrição", "comestível", "panc", "fruto", "azeite", "mel"],
    "Cosméticos e Higiene": ["cosmético", "higiene", "beleza", "perfume", "sabonete", "oleo"],
    "Madeira e Construção": ["madeira", "construção", "móveis", "estaca", "viga"],
    "Serviços Ambientais": ["sombra", "solo", "reflorestamento", "nascente", "serviço", "ambiental"],
    "Ornamental e Paisagismo": ["ornamental", "jardim", "flor"],
    "Artesanato e Cultura": ["artesanato", "artefato", "biojoia", "fibra", "palha"],
    "Indústria e Energia": ["indústria", "energia", "biocombustível", "resina"],
    "Nutrição Animal": ["animal", "gado", "ração", "pasto"]
}

PARTES_MAP = {
    "Planta": ["planta", "toda a planta"],
    "Fruto e Polpa": ["fruto", "polpa"],
    "Folha": ["folha", "folhagem"],
    "Semente e Castanha": ["semente", "amêndoa"],
    "Caule e Madeira": ["tronco", "madeira"],
    "Raiz e Rizoma": ["raiz", "rizoma"],
    "Flor": ["flor", "inflorescência"],
    "Exsudato (Látex/Resina)": ["látex", "resina"],
    "Casca": ["casca"],
    "Palmito": ["palmito"]
}


# --- FUNÇÕES ---
def normalizar_texto(texto):
    if not isinstance(texto, str): return str(texto)
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').lower()


def buscar_valor_inteligente(linha, chaves_possiveis):
    chaves_linha_norm = {normalizar_texto(k): k for k in linha.keys()}
    for chave in chaves_possiveis:
        chave_norm = normalizar_texto(chave)
        for k_norm, k_original in chaves_linha_norm.items():
            if chave_norm in k_norm: return linha[k_original]
    return ""


def classificar_tags(texto, mapa):
    tags = set()
    texto_lower = str(texto).lower()
    for cat, termos in mapa.items():
        if any(termo in texto_lower for termo in termos): tags.add(cat)
    return list(tags)


def limpar_gps(valor_raw):
    """Limpa e formata qualquer coordenada para lat,long com ponto."""
    if not valor_raw or len(str(valor_raw)) < 5: return None
    # Regex pega numeros como -1.45 ou -1,45
    numeros = re.findall(r'-?\d+[.,]\d+', str(valor_raw))
    if len(numeros) >= 2:
        return f"{numeros[0].replace(',', '.')},{numeros[1].replace(',', '.')}"
    return None


def buscar_referencias_ia(nome_cientifico):
    return [{"titulo": f"Pesquisa: {nome_cientifico}", "url": "#"}]


# --- SINCRONIZAÇÃO ---
def sincronizar_dados():
    print("📡 Sincronizando...")
    try:
        caminho_creds = os.path.join(BACKEND_DIR, "credentials.json")
        creds = Credentials.from_service_account_file(caminho_creds,
                                                      scopes=["https://www.googleapis.com/auth/spreadsheets",
                                                              "https://www.googleapis.com/auth/drive"])
        client = gspread.authorize(creds)
        raw_data = client.open("TESTEBASE").sheet1.get_all_records()
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

    plantas_processadas = []
    total_geo = 0
    stats_categorias = {cat: 0 for cat in CATEGORIAS_MAP.keys()}
    stats_categorias["Outros"] = 0

    for row in raw_data:
        nome_c = buscar_valor_inteligente(row, ["nome cientifico", "especie"])

        # 1. LEITURA ROBUSTA (Mais nomes de colunas)
        gps_raw = buscar_valor_inteligente(row, ["coordenadas", "gps", "lat", "latitude", "location", "geo"])
        gps_final = limpar_gps(gps_raw)

        # 2. VALIDAÇÃO GBIF (Sem bloquear!)
        # Se a planilha tem coordenada, a gente ACEITA. O GBIF só valida o nome.
        if gps_final:
            total_geo += 1
            try:
                # Busca rápida só para ver se o nome está correto na base científica
                res = occurrences.search(scientificName=nome_c, limit=1)
                if res['results']:
                    nome_c = res['results'][0].get('scientificName', nome_c)
            except:
                pass

        # Foto
        url_foto = buscar_valor_inteligente(row, ["foto", "imagem", "link", "url"])
        if not url_foto or "http" not in str(url_foto):
            url_foto = "https://images.unsplash.com/photo-1518531933037-91b2f5f229cc?w=800&q=80"

        # Tags
        tags = classificar_tags(buscar_valor_inteligente(row, ["potencial", "uso"]), CATEGORIAS_MAP) or ["Outros"]
        for t in tags:
            if t in stats_categorias:
                stats_categorias[t] += 1
            else:
                stats_categorias["Outros"] += 1

        link_biblio = buscar_valor_inteligente(row, ["bibliografia de potencial bioeconomico", "artigo"])
        artigos = [{"titulo": "Artigo de Referência", "url": str(link_biblio)}] if "http" in str(
            link_biblio) else buscar_referencias_ia(nome_c)

        planta = {
            "nome_popular": buscar_valor_inteligente(row, ["nome popular"]) or "Sem Nome",
            "nome_cientifico": nome_c or "Sp.",
            "familia": buscar_valor_inteligente(row, ["familia"]) or "-",
            "foto": url_foto,
            "tags": tags,
            "partes_tags": classificar_tags(buscar_valor_inteligente(row, ["parte"]), PARTES_MAP),
            "origem": buscar_valor_inteligente(row, ["origem"]) or "-",
            "importancia": buscar_valor_inteligente(row, ["importancia"]) or "Sem descrição.",
            "coordenadas": gps_final,
            "artigos": artigos
        }
        plantas_processadas.append(planta)

    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump({"plantas": plantas_processadas,
                   "stats": {"total_especies": len(plantas_processadas), "total_geo": total_geo,
                             "por_categoria": stats_categorias}}, f, ensure_ascii=False, indent=4)

    return True


@app.route("/")
def index():
    if not os.path.exists(DATA_FILE): sincronizar_dados()
    with open(DATA_FILE, 'r', encoding='utf-8') as f: dados = json.load(f)
    return render_template("home.html", plantas=dados['plantas'], stats=dados['stats'],
                           filtros={"categorias": list(CATEGORIAS_MAP.keys()), "partes": list(PARTES_MAP.keys())})


@app.route("/sync")
def forcar_sync():
    sincronizar_dados()
    return redirect(url_for('index'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
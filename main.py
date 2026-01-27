from flask import Flask, render_template, redirect, url_for
import gspread
from google.oauth2.service_account import Credentials
import os
import unicodedata

app = Flask(__name__)

# --- 1. MAPA DE CATEGORIAS (POTENCIAL) ---
CATEGORIAS_MAP = {
    "Medicinal e Farmacológico": [
        "medicinal", "medicina", "farmaco", "terapeutico", "fitoterapico", "antiveneno",
        "xarope", "chá", "infusão", "bioativo", "extrato"
    ],
    "Alimentação e Nutrição": [
        "alimento", "alimentação", "nutrição", "comestível", "panc", "condimento",
        "tempero", "sabor", "geleia", "doce", "vinho", "bebida"
    ],
    "Cosméticos e Higiene": [
        "cosmético", "higiene", "beleza", "perfume", "aroma", "sabonete", "shampoo",
        "hidratante", "tintura", "essência", "banho"
    ],
    "Madeira e Construção": [
        "madeira", "construção", "móveis", "marcenaria", "carpintaria", "naval",
        "barco", "cerca", "estaca", "tábua", "viga"
    ],
    "Serviços Ambientais": [
        "restauração", "recuperação", "reflorestamento", "sombra", "solo", "erosão",
        "nascente", "biodiversidade", "carbono", "adubo", "paisagismo"
    ],
    "Ornamental e Paisagismo": [
        "ornamental", "paisagismo", "jardim", "flor", "decorativa", "arborização", "vaso"
    ],
    "Artesanato e Cultura": [
        "artesanato", "artefato", "biojoia", "cesta", "cestaria", "fibra", "palha",
        "utensílio", "cultura", "indígena", "ritual"
    ],
    "Indústria e Energia": [
        "indústria", "energia", "biocombustível", "carvão", "lenha", "biomassa",
        "papel", "têxtil", "látex", "borracha", "resina", "tanino"
    ],
    "Nutrição Animal": [
        "animal", "gado", "peixe", "piscicultura", "ração", "forragem", "pasto",
        "apicultura", "mel"
    ]
}

# --- 2. MAPA DE PARTES DA PLANTA ---
PARTES_MAP = {
    "Fruto e Polpa": ["fruto", "fruta", "polpa", "mesocarpo", "epicarpo", "baga", "cacho"],
    "Folha": ["folha", "folhagem", "brotos"],
    "Semente e Castanha": ["semente", "amêndoa", "castanha", "caroço", "noze"],
    "Caule e Madeira": ["caule", "tronco", "madeira", "lenho", "estipe", "cipó", "talo"],
    "Raiz e Rizoma": ["raiz", "rizoma", "tubérculo", "batata"],
    "Flor": ["flor", "inflorescência", "botão"],
    "Exsudato (Látex/Resina)": ["látex", "resina", "seiva", "goma", "oleoresina", "óleo-resina", "leite"],
    "Casca": ["casca", "entrecasca"],
    "Palmito": ["palmito"]
}


def normalizar_texto(texto):
    if not isinstance(texto, str): return str(texto)
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').lower()


def buscar_valor_inteligente(linha, chaves_possiveis):
    chaves_linha_normalizadas = {normalizar_texto(k): k for k in linha.keys()}
    for chave in chaves_possiveis:
        chave_norm = normalizar_texto(chave)
        for k_norm, k_original in chaves_linha_normalizadas.items():
            if chave_norm in k_norm:
                return linha[k_original]
    return ""


def classificar_tags(texto, mapa_referencia):
    tags = set()
    texto_lower = str(texto).lower()
    for cat_oficial, termos in mapa_referencia.items():
        for termo in termos:
            if termo in texto_lower:
                tags.add(cat_oficial)
                break
    return list(tags)


def conectar_google():
    try:
        caminho = os.path.join(os.path.dirname(__file__), "backend", "credentials.json")
        creds = Credentials.from_service_account_file(caminho, scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ])
        client = gspread.authorize(creds)
        sheet = client.open("TESTEBASE").sheet1
        return sheet.get_all_records()
    except Exception as e:
        print(f"❌ ERRO CRÍTICO NO GOOGLE: {e}")
        return []


@app.route("/")
def index():
    raw_data = conectar_google()
    plantas_limpas = []

    # --- CORREÇÃO DO ERRO AQUI ---
    # Inicializa o contador para todas as categorias + Outros
    stats_categorias = {cat: 0 for cat in CATEGORIAS_MAP.keys()}
    stats_categorias["Outros"] = 0

    # Chaves de Busca
    chaves_potencial = ["potencial", "uso", "aplicacao", "bioeconomia"]
    chaves_parte = ["parte", "usada", "estrutura"]
    chaves_coords = ["coordenadas", "gps", "lat", "gbif"]
    chaves_registro = ["registro", "id"]
    chaves_familia = ["familia", "family"]
    chaves_popular = ["nome popular", "popular"]
    chaves_cientifico = ["nome cientifico", "especie"]
    chaves_origem = ["origem", "habitat"]
    chaves_importancia = ["importancia", "resumo"]

    for row in raw_data:
        # 1. Pega valores brutos
        potencial_txt = buscar_valor_inteligente(row, chaves_potencial)
        parte_txt = buscar_valor_inteligente(row, chaves_parte)

        # 2. Classifica usando os mapas
        tags_categoria = classificar_tags(potencial_txt, CATEGORIAS_MAP)
        if not tags_categoria:
            tags_categoria = ["Outros"]

        tags_partes = classificar_tags(parte_txt, PARTES_MAP)

        # 3. Estatísticas (Incrementa o contador)
        for t in tags_categoria:
            if t in stats_categorias:
                stats_categorias[t] += 1
            else:
                # Segurança caso venha algo estranho, joga no Outros
                stats_categorias["Outros"] += 1

        planta = {
            "registro": buscar_valor_inteligente(row, chaves_registro) or "s/n",
            "familia": buscar_valor_inteligente(row, chaves_familia) or "-",
            "nome_popular": buscar_valor_inteligente(row, chaves_popular) or "Sem Nome",
            "nome_cientifico": buscar_valor_inteligente(row, chaves_cientifico) or "Sp. desconhecida",
            "potencial_texto": potencial_txt,
            "tags": tags_categoria,
            "partes_tags": tags_partes,
            "origem": buscar_valor_inteligente(row, chaves_origem) or "-",
            "parte_planta_texto": parte_txt,
            "importancia": buscar_valor_inteligente(row, chaves_importancia) or "Sem descrição.",
            "coordenadas": buscar_valor_inteligente(row, chaves_coords)
        }
        plantas_limpas.append(planta)

    stats = {
        "total_especies": len(plantas_limpas),
        "total_geo": sum(1 for p in plantas_limpas if p['coordenadas'] and ',' in str(p['coordenadas'])),
        "por_categoria": stats_categorias
    }

    filtros = {
        "categorias": list(CATEGORIAS_MAP.keys()) + ["Outros"],
        "partes": list(PARTES_MAP.keys())
    }

    return render_template("home.html", plantas=plantas_limpas, stats=stats, filtros=filtros)


@app.route("/catalogo")
def r1(): return redirect(url_for("index"))


@app.route("/mapa")
def r2(): return redirect(url_for("index") + "#mapa-area")


if __name__ == "__main__":
    app.run(debug=True)
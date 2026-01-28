from flask import Flask, render_template, redirect, url_for
import gspread
from google.oauth2.service_account import Credentials
import os
import unicodedata
from pygbif import occurrences  # <--- NOVA IMPORTAÇÃO

app = Flask(__name__)

# --- CACHE SIMPLES EM MEMÓRIA (Para não travar o site) ---
# O site vai "lembrar" das buscas do GBIF enquanto estiver rodando
GBIF_CACHE = {}

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


# --- FUNÇÕES UTILITÁRIAS ---

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
        # Ajuste o caminho conforme sua estrutura de pastas
        caminho = os.path.join(os.path.dirname(__file__), "backend", "credentials.json")
        # Se o arquivo estiver na raiz, use apenas: "credentials.json"

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


# --- NOVA FUNÇÃO: BUSCA NO GBIF ---
def buscar_coordenadas_gbif(nome_cientifico):
    # 1. Limpeza básica
    if not nome_cientifico or len(nome_cientifico) < 3:
        return None

    # 2. Verifica se já buscamos isso antes (Cache)
    if nome_cientifico in GBIF_CACHE:
        return GBIF_CACHE[nome_cientifico]

    print(f"🌍 Buscando GBIF para: {nome_cientifico}...")
    try:
        # 3. Busca na API do GBIF
        # hasCoordinate=True -> Só quero se tiver GPS
        # limit=1 -> Só preciso do primeiro registro confiável
        res = occurrences.search(scientificName=nome_cientifico, hasCoordinate=True, limit=1)

        if res['results']:
            rec = res['results'][0]
            lat = rec['decimalLatitude']
            lon = rec['decimalLongitude']
            coord_formatada = f"{lat}, {lon}"

            # Salva no cache e retorna
            GBIF_CACHE[nome_cientifico] = coord_formatada
            return coord_formatada
    except Exception as e:
        print(f"⚠️ Erro ao conectar GBIF: {e}")

    # Se der erro ou não achar, salva None no cache para não tentar de novo à toa
    GBIF_CACHE[nome_cientifico] = None
    return None


# --- PROCESSAMENTO PRINCIPAL ---
def processar_dados_munguba():
    raw_data = conectar_google()
    plantas_limpas = []

    stats_categorias = {cat: 0 for cat in CATEGORIAS_MAP.keys()}
    stats_categorias["Outros"] = 0

    # Chaves de busca na planilha
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
        # Extração básica
        potencial_txt = buscar_valor_inteligente(row, chaves_potencial)
        parte_txt = buscar_valor_inteligente(row, chaves_parte)
        nome_cientifico = buscar_valor_inteligente(row, chaves_cientifico)

        # Classificação de Tags
        tags_categoria = classificar_tags(potencial_txt, CATEGORIAS_MAP)
        if not tags_categoria: tags_categoria = ["Outros"]
        tags_partes = classificar_tags(parte_txt, PARTES_MAP)

        # Estatísticas
        for t in tags_categoria:
            if t in stats_categorias:
                stats_categorias[t] += 1
            else:
                stats_categorias["Outros"] += 1

        # --- LÓGICA DE COORDENADAS (GBIF) ---
        coordenadas = buscar_valor_inteligente(row, chaves_coords)

        # Se a planilha estiver vazia, tenta o GBIF
        if not coordenadas or len(str(coordenadas).strip()) < 5:
            gbif_result = buscar_coordenadas_gbif(nome_cientifico)
            if gbif_result:
                coordenadas = gbif_result

        # Montagem do Objeto Planta
        planta = {
            "registro": buscar_valor_inteligente(row, chaves_registro) or "s/n",
            "familia": buscar_valor_inteligente(row, chaves_familia) or "-",
            "nome_popular": buscar_valor_inteligente(row, chaves_popular) or "Sem Nome",
            "nome_cientifico": nome_cientifico or "Sp. desconhecida",
            "potencial_texto": potencial_txt,
            "tags": tags_categoria,
            "partes_tags": tags_partes,
            "origem": buscar_valor_inteligente(row, chaves_origem) or "-",
            "parte_planta_texto": parte_txt,
            "importancia": buscar_valor_inteligente(row, chaves_importancia) or "Sem descrição.",
            "coordenadas": coordenadas
        }
        plantas_limpas.append(planta)

    # Stats Finais
    stats = {
        "total_especies": len(plantas_limpas),
        "total_geo": sum(1 for p in plantas_limpas if p['coordenadas'] and ',' in str(p['coordenadas'])),
        "por_categoria": stats_categorias
    }

    filtros = {
        "categorias": list(CATEGORIAS_MAP.keys()) + ["Outros"],
        "partes": list(PARTES_MAP.keys())
    }

    return plantas_limpas, stats, filtros


# --- ROTAS ---

@app.route("/")
def index():
    plantas, stats, filtros = processar_dados_munguba()
    return render_template("home.html", plantas=plantas, stats=stats, filtros=filtros)


@app.route("/mapa")
def mapa_dashboard():
    plantas, stats, _ = processar_dados_munguba()
    return render_template("mapa.html", plantas=plantas, stats=stats)


@app.route("/catalogo")
def catalogo_redirect():
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
from flask import Flask, render_template, request, redirect, url_for
import gspread
from google.oauth2.service_account import Credentials
import os
import unicodedata
import json  # <--- Importante para o Deploy

app = Flask(__name__)

# --- CONFIGURAÇÕES ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Caminho absoluto para evitar erros no Linux
BACKEND_DIR = os.path.join(BASE_DIR, "backend")

# --- MEMÓRIA RAM ---
CACHE_DADOS = {
    "plantas": [],
    "stats": {},
    "carregado": False
}

# --- SEU GABARITO OFICIAL ---
GPS_FIXO = {
    'Adenocalymma magnificum': [-1.503333, -48.446667],
    'Adiantum tomentosum': [-1.497500, -48.429167],
    'Aechmea mertensii': [-1.416667, -48.416667],
    'Alternanthera ficoidea': [-1.488889, -48.429167],
    'Ampelocera edentula': [-1.416667, -48.416667],
    'Anthurium pentaphyllum': [-1.503333, -48.446944],
    'Astrocaryum murumuru': [-0.641389, -47.531667],
    'Attalea phalerata': [-1.416667, -48.416667],
    'Byttneria coriácea': [-1.499232, -48.453742],
    'Byttneria coriacea': [-1.499232, -48.453742],
    'Caladium bicolor': [-1.501389, -48.446944],
    'Casimirella ampla': [-1.500000, -48.450000],
    'Cecropia palmata': [-1.416667, -48.416667],
    'Cedrela odorata': [-1.416667, -48.416667],
    'Ceiba pentandra': [-1.416667, -48.416667],
    'Dianthera comata': [-1.490000, -48.463056],
    'Dichaea panamensis': [-1.498511, -48.460903],
    'Heliconia acuminata': [-1.503333, -48.446944],
    'Heliconia bihai': [-1.504080, -48.447998],
    'Hernandia guianensis': [-1.503056, -48.446944],
    'Inga nobilis': [-1.500106, -48.461310],
    'Justicia pseudoamazonica': [-1.498511, -48.460903],
    'Sapium marmieri': [-1.490352, -48.452798],
    'Toulicia guianensis': [-1.506944, -48.462222]
}

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
    "Planta": ["planta"], "Fruto e Polpa": ["fruto", "polpa"], "Folha": ["folha"],
    "Semente": ["semente"], "Caule": ["tronco", "madeira"], "Raiz": ["raiz"],
    "Flor": ["flor"], "Exsudato": ["latex", "resina"], "Casca": ["casca"], "Palmito": ["palmito"]
}


# --- FUNÇÕES AUXILIARES ---

def normalizar_texto(texto):
    if not isinstance(texto, str): return str(texto)
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').lower().strip()


def buscar_valor_inteligente(linha, chaves_possiveis):
    chaves_linha_norm = {normalizar_texto(k): k for k in linha.keys()}
    for chave in chaves_possiveis:
        chave_norm = normalizar_texto(chave)
        for k_norm, k_original in chaves_linha_norm.items():
            if chave_norm in k_norm: return linha[k_original]
    return ""


def classificar_tags(texto, mapa):
    tags = set()
    t_lower = str(texto).lower()
    for cat, termos in mapa.items():
        if any(termo in t_lower for termo in termos): tags.add(cat)
    return list(tags)


def encontrar_no_gabarito(nome_na_planilha):
    if not nome_na_planilha: return None
    busca = normalizar_texto(nome_na_planilha)
    for nome_chave, coords in GPS_FIXO.items():
        chave_norm = normalizar_texto(nome_chave)
        if chave_norm in busca or busca in chave_norm:
            return [{'lat': coords[0], 'lng': coords[1]}]
    return None


# --- NOVA FUNÇÃO DE CONEXÃO SEGURA (LOCAL E RENDER) ---
def conectar_google():
    """Conecta ao Google Sheets usando Env Var (Render) ou Arquivo (Local)"""
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

    try:
        # 1. Tenta pegar do "Cofre" do Render (Variável de Ambiente)
        if os.environ.get("GOOGLE_CREDENTIALS_JSON"):
            print("☁️ Conectando via Variável de Ambiente (Render)...")
            creds_dict = json.loads(os.environ.get("GOOGLE_CREDENTIALS_JSON"))
            creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)

        # 2. Se não achar, tenta pegar o arquivo local (Seu PC)
        else:
            caminho_local = os.path.join(BACKEND_DIR, "credentials.json")
            if os.path.exists(caminho_local):
                print("💻 Conectando via Arquivo Local...")
                creds = Credentials.from_service_account_file(caminho_local, scopes=SCOPES)
            else:
                print("❌ ERRO: Nenhuma credencial encontrada!")
                return None

        client = gspread.authorize(creds)
        return client.open("TESTEBASE").sheet1.get_all_records()

    except Exception as e:
        print(f"❌ Erro na Conexão: {e}")
        return None


# --- CARREGAMENTO ---

def carregar_dados_aovivo():
    print("\n" + "=" * 50)
    print("📡 SINCRONIZANDO DADOS...")
    print("=" * 50)

    # Usa a nova função de conexão
    raw_data = conectar_google()

    if not raw_data:
        return False

    plantas_processadas = []
    total_geo = 0
    stats_categorias = {cat: 0 for cat in CATEGORIAS_MAP.keys()}
    stats_categorias["Outros"] = 0

    print(f"📋 Processando {len(raw_data)} plantas...")

    for row in raw_data:
        nome_c = buscar_valor_inteligente(row, ["especie", "nome cientifico", "nome"])
        pontos_gps = encontrar_no_gabarito(nome_c)

        if pontos_gps:
            total_geo += 1
        else:
            if nome_c and len(nome_c) > 3:
                print(f"   ⚠️ NOME NÃO BATENDO: Planilha diz '{nome_c}' -> Não achei no Gabarito.")

        url_foto = buscar_valor_inteligente(row, ["foto", "imagem"])
        if not url_foto or "http" not in str(url_foto):
            url_foto = "https://images.unsplash.com/photo-1518531933037-91b2f5f229cc?w=800&q=80"

        tags = classificar_tags(buscar_valor_inteligente(row, ["potencial bioeconomico", "potencial", "uso"]),
                                CATEGORIAS_MAP) or ["Outros"]
        for t in tags:
            if t in stats_categorias:
                stats_categorias[t] += 1
            else:
                stats_categorias["Outros"] += 1

        tags_partes = classificar_tags(buscar_valor_inteligente(row, ["parte da planta", "parte"]), PARTES_MAP)
        link_biblio = buscar_valor_inteligente(row, ["bibliografia de potencial", "bibliografia"])
        nome_pop_original = buscar_valor_inteligente(row, ["nome popular"])

        # Se tiver nome popular, usa ele. Se não tiver, usa o nome científico (nome_c)
        nome_exibicao = nome_pop_original if nome_pop_original else nome_c

        planta = {
            "nome_popular": nome_exibicao,  # Agora nunca será "Sem Nome"
            "nome_cientifico": nome_c or "Sp.",
            "familia": buscar_valor_inteligente(row, ["familia"]) or "-",
            "foto": url_foto,
            "tags": tags,
            "partes_tags": tags_partes,
            "origem": buscar_valor_inteligente(row, ["origem", "habitat"]) or "-",
            "importancia": buscar_valor_inteligente(row, ["importancia", "aproveitamento"]) or "Sem descrição.",
            "pontos_gps": pontos_gps or [],
            "artigos": [{"titulo": "Referência", "url": str(link_biblio)}] if "http" in str(link_biblio) else []
        }
        plantas_processadas.append(planta)

    CACHE_DADOS["plantas"] = plantas_processadas
    CACHE_DADOS["stats"] = {"total_especies": len(plantas_processadas), "total_geo": total_geo,
                            "por_categoria": stats_categorias}
    CACHE_DADOS["carregado"] = True

    print("-" * 50)
    print(f"🏁 MAPA ATUALIZADO: {total_geo} plantas com coordenadas confirmadas.")
    return True


@app.route("/")
def index():
    if not CACHE_DADOS["carregado"]:
        carregar_dados_aovivo()
    return render_template("home.html", plantas=CACHE_DADOS['plantas'], stats=CACHE_DADOS['stats'],
                           filtros={"categorias": list(CATEGORIAS_MAP.keys()), "partes": list(PARTES_MAP.keys())})


@app.route("/sync")
def forcar_sync():
    carregar_dados_aovivo()
    return redirect(url_for('index'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
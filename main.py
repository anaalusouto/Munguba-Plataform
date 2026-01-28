from flask import Flask, render_template, request, redirect, url_for
import gspread
from google.oauth2.service_account import Credentials
import os
import unicodedata

app = Flask(__name__)

# --- CONFIGURAÇÕES ---
BASE_DIR = os.path.dirname(__file__)
BACKEND_DIR = os.path.join(BASE_DIR, "backend")

# --- MEMÓRIA RAM ---
CACHE_DADOS = {
    "plantas": [],
    "stats": {},
    "carregado": False
}

# --- SEU GABARITO OFICIAL (Copiado do seu dados_mapa) ---
GPS_FIXO = {
    'Adenocalymma magnificum': [-1.503333, -48.446667],
    'Adiantum tomentosum': [-1.497500, -48.429167],
    'Aechmea mertensii': [-1.416667, -48.416667],
    'Alternanthera ficoidea': [-1.488889, -48.429167],
    'Ampelocera edentula': [-1.416667, -48.416667],
    'Anthurium pentaphyllum': [-1.503333, -48.446944],
    'Astrocaryum murumuru': [-0.641389, -47.531667],
    'Attalea phalerata': [-1.416667, -48.416667],
    'Byttneria coriácea': [-1.499232, -48.453742],  # Com acento (como você mandou)
    'Byttneria coriacea': [-1.499232, -48.453742],  # Sem acento (por garantia)
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


# --- FUNÇÕES ---

def normalizar_texto(texto):
    if not isinstance(texto, str): return str(texto)
    # Remove acentos, espaços nas pontas e joga tudo para minúsculo
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
    """
    Compara o nome da planilha com o gabarito.
    Ex: Planilha "Inga nobilis Willd." bate com Gabarito "Inga nobilis"
    """
    if not nome_na_planilha: return None

    # Normaliza o nome que veio da planilha (ex: "inga nobilis willd.")
    busca = normalizar_texto(nome_na_planilha)

    # Varre as chaves do seu gabarito
    for nome_chave, coords in GPS_FIXO.items():
        chave_norm = normalizar_texto(nome_chave)

        # VERIFICAÇÃO DUPLA:
        # 1. Se a chave do gabarito está DENTRO do nome da planilha (ex: "inga nobilis" in "inga nobilis willd.")
        # 2. OU se o nome da planilha está DENTRO da chave (ex: "inga nobilis" in "inga nobilis (mart.)")
        if chave_norm in busca or busca in chave_norm:
            return [{'lat': coords[0], 'lng': coords[1]}]

    return None


# --- CARREGAMENTO ---

def carregar_dados_aovivo():
    print("\n" + "=" * 50)
    print("📡 SINCRONIZANDO: BUSCA POR NOME DA ESPÉCIE")
    print("=" * 50)
    try:
        caminho_creds = os.path.join(BACKEND_DIR, "credentials.json")
        creds = Credentials.from_service_account_file(caminho_creds,
                                                      scopes=["https://www.googleapis.com/auth/spreadsheets",
                                                              "https://www.googleapis.com/auth/drive"])
        client = gspread.authorize(creds)
        raw_data = client.open("TESTEBASE").sheet1.get_all_records()
    except Exception as e:
        print(f"❌ Erro Conexão: {e}")
        return False

    plantas_processadas = []
    total_geo = 0
    stats_categorias = {cat: 0 for cat in CATEGORIAS_MAP.keys()}
    stats_categorias["Outros"] = 0

    print(f"📋 Processando {len(raw_data)} plantas...")

    for row in raw_data:
        # 1. PEGA O NOME NA PLANILHA
        # Prioriza "ESPECIE", depois "Nome Cientifico"
        nome_c = buscar_valor_inteligente(row, ["especie", "nome cientifico", "nome"])

        # 2. TENTA ENCONTRAR NO GABARITO (PELO NOME DA ESPÉCIE)
        pontos_gps = encontrar_no_gabarito(nome_c)

        if pontos_gps:
            total_geo += 1
            # print(f"   ✅ Achei: {nome_c}")
        else:
            # Mostra o que falhou para você corrigir
            if nome_c and len(nome_c) > 3:
                print(f"   ⚠️ NOME NÃO BATENDO: Planilha diz '{nome_c}' -> Não achei no Gabarito.")

        # Resto dos dados...
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

        planta = {
            "nome_popular": buscar_valor_inteligente(row, ["nome popular"]) or "Sem Nome",
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
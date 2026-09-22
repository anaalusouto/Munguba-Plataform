import csv
import io
import os
import re
import time
import urllib.request

# Planilha pública com as fotos (exportada como CSV pelo próprio Google Sheets)
FOTOS_PLANILHA_ID = os.environ.get("FOTOS_PLANILHA_ID", "1nvX6uISakRKveiDBx6kjxi1OcRsw9BcXY4uzqHEoIR8")
FOTOS_CSV_URL = f"https://docs.google.com/spreadsheets/d/{FOTOS_PLANILHA_ID}/export?format=csv"
CACHE_SEGUNDOS = 60 * 60  # recarrega a planilha no máximo 1x por hora

# Epítetos que não identificam uma espécie (ex: "Inga sp. 1") -> não usar o binômio para casar
EPITETOS_INDEFINIDOS = {"sp", "sp.", "spp", "spp.", "cf", "cf.", "aff", "aff."}

_cache = {"fotos": None, "binomios": None, "carregado_em": 0}


def normalizar_nome(nome):
    return re.sub(r"\s+", " ", str(nome or "")).strip().lower()


def binomio(nome):
    """Gênero + epíteto, sem autoria. Retorna None se o nome não tiver um epíteto válido."""
    partes = normalizar_nome(nome).split(" ")
    if len(partes) < 2 or partes[1] in EPITETOS_INDEFINIDOS or not partes[1].isalpha():
        return None
    return f"{partes[0]} {partes[1]}"


def _link_de_imagem(url):
    # Links .dzi (Deep Zoom) não são imagens que o navegador consegue exibir
    url = (url or "").strip()
    if not url.startswith("http") or ".dzi" in url.lower():
        return ""
    return url.replace("http://", "https://", 1)


def _carregar_planilha():
    with urllib.request.urlopen(FOTOS_CSV_URL, timeout=10) as resp:
        texto = resp.read().decode("utf-8")

    fotos, binomios = {}, {}
    for linha in csv.DictReader(io.StringIO(texto)):
        nome = linha.get("Nome científico (catálogo)", "")
        url_alta = _link_de_imagem(linha.get("Link da foto (alta resolução)"))
        if not nome.strip() or not url_alta:
            continue

        foto = {
            "url": url_alta,
            "url_media": _link_de_imagem(linha.get("Link da foto (tamanho médio)")) or url_alta,
            "autor": (linha.get("Autor/direitos") or "").strip(),
            "licenca": (linha.get("Licença") or "").strip(),
            "fonte": (linha.get("Página de referência") or "").strip(),
        }
        fotos.setdefault(normalizar_nome(nome), foto)
        chave_binomio = binomio(nome)
        if chave_binomio:
            binomios.setdefault(chave_binomio, foto)
    return fotos, binomios


def _garantir_cache():
    agora = time.time()
    if _cache["fotos"] is not None and agora - _cache["carregado_em"] < CACHE_SEGUNDOS:
        return
    try:
        _cache["fotos"], _cache["binomios"] = _carregar_planilha()
        print(f"🖼️ {len(_cache['fotos'])} fotos carregadas da planilha.")
    except Exception as e:
        # Se o Google estiver fora, mantém o cache antigo (ou vazio) e o site segue com a foto padrão
        print(f"⚠️ Não foi possível carregar a planilha de fotos: {e}")
        if _cache["fotos"] is None:
            _cache["fotos"], _cache["binomios"] = {}, {}
    _cache["carregado_em"] = agora


def buscar_foto(nome_cientifico):
    """Procura a foto pelo nome científico exato; se não achar, tenta pelo binômio (ignora a autoria)."""
    _garantir_cache()
    foto = _cache["fotos"].get(normalizar_nome(nome_cientifico))
    if not foto:
        chave_binomio = binomio(nome_cientifico)
        foto = _cache["binomios"].get(chave_binomio) if chave_binomio else None
    return foto

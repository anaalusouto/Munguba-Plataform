"""Enriquece o catálogo com fotos documentadas no GBIF e gera WebP locais.

Executar com o Python do ambiente, que precisa de Pillow. Nenhuma consulta é
feita durante a navegação do visitante. A planilha original não é modificada.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sys
import time
from urllib.parse import unquote, urlencode
from urllib.request import Request, urlopen

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import main
from fotos import binomio, normalizar_nome
from ocorrencias import carregar_appendix

MANIFESTO = ROOT / 'dados' / 'fotos_complementares.json'
MINIATURAS = ROOT / 'dados' / 'fotos_miniaturas.json'
DESTINO = ROOT / 'static' / 'fotos' / 'catalogo'
RELATORIO = ROOT / 'artifacts' / 'busca-fotos.json'
AGENTE = 'MungubaCatalog/1.0 (botanical education; photo attribution preserved)'


def ler_json(caminho):
    return json.loads(caminho.read_text(encoding='utf-8')) if caminho.exists() else {}


def salvar_json(caminho, dados):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_suffix('.tmp')
    temporario.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding='utf-8')
    temporario.replace(caminho)


def requisitar(url, imagem=False):
    req = Request(url, headers={'User-Agent': AGENTE, 'Accept': 'image/*,*/*;q=0.8' if imagem else 'application/json'})
    for tentativa in range(1 if imagem else 2):
        try:
            with urlopen(req, timeout=15) as resposta:
                dados = resposta.read(20_000_001)
                if len(dados) > 20_000_000:
                    raise ValueError('Resposta maior que 20 MB')
                return dados if imagem else json.loads(dados)
        except Exception as erro:
            if imagem or tentativa == 1:
                raise RuntimeError(f'{url}: {erro}') from erro
            time.sleep(0.5)


def combinar_nome(nome, familia):
    """Nunca atribuir uma foto a partir de correspondência de gênero ou fuzzy."""
    if not binomio(nome):
        return None
    infraespecifico = any(marcador in nome.lower().split() for marcador in ('var.', 'subsp.', 'ssp.', 'f.'))
    consultas = [nome] if infraespecifico else [nome, binomio(nome)]
    for consulta in dict.fromkeys(consultas):
        params = urlencode({'name': consulta, 'kingdom': 'Plantae', 'family': familia, 'strict': 'true'})
        match = requisitar('https://api.gbif.org/v1/species/match?' + params)
        if (match.get('matchType') == 'EXACT' and match.get('confidence', 0) >= 95
                and match.get('rank') in ('SPECIES', 'SUBSPECIES', 'VARIETY', 'FORM')
                and match.get('kingdom') == 'Plantae'
                and (familia == '-' or match.get('family', '').casefold() == familia.casefold())):
            # Ao remover a autoria, exigir o mesmo binômio para não perder a identidade.
            if consulta == nome or binomio(match.get('canonicalName', '')) == binomio(nome):
                return match
    return None


def candidatos(match):
    chave = match.get('acceptedUsageKey') or match['usageKey']
    base = {'taxonKey': chave, 'mediaType': 'StillImage', 'limit': 50, 'occurrenceStatus': 'PRESENT'}
    params = urlencode({**base, 'basisOfRecord': 'HUMAN_OBSERVATION', 'limit': 30})
    registros = requisitar('https://api.gbif.org/v1/occurrence/search?' + params).get('results', [])
    fotos = _extrair_candidatos(registros, chave, match)
    if fotos:
        return fotos
    registros = requisitar('https://api.gbif.org/v1/occurrence/search?' + urlencode(base)).get('results', [])
    return _extrair_candidatos(registros, chave, match)


def _extrair_candidatos(registros, chave, match):
    fotos = []
    for r in registros:
        # O filtro do GBIF pode incluir descendentes; não aceitar outros táxons.
        if str(chave) not in {str(r.get(k)) for k in ('taxonKey', 'acceptedTaxonKey', 'speciesKey')}:
            continue
        for media in r.get('media', []):
            url = media.get('identifier', '')
            licenca = media.get('license', '')
            if (not url.startswith(('http://', 'https://')) or '.dzi' in url.lower()
                    or not any(s in licenca.lower() for s in ('creativecommons.org/licenses/by/',
                            'creativecommons.org/licenses/by-sa/', 'creativecommons.org/licenses/by-nc/',
                            'creativecommons.org/licenses/by-nc-sa/', 'creativecommons.org/publicdomain/'))):
                continue
            url = url.replace('http://', 'https://', 1)
            autor = media.get('creator') or media.get('rightsHolder') or r.get('rightsHolder')
            if not autor:
                continue
            foto = {'url': url, 'url_media': url, 'autor': autor, 'licenca': licenca,
                    'fonte': f"https://www.gbif.org/occurrence/{r['key']}",
                    'nome_identificado': r.get('scientificName'), 'taxon_gbif': chave,
                    'consulta_nome': match.get('scientificName'),
                    'consultado_em': datetime.now(timezone.utc).isoformat()}
            prioridade = 0 if 'inaturalist' in url else 1 if r.get('basisOfRecord') != 'PRESERVED_SPECIMEN' else 2
            fotos.append((prioridade, foto))
    return [f for _, f in sorted(fotos, key=lambda par: par[0])]


def otimizar(foto):
    original = foto['url']
    identificador = hashlib.sha256(original.encode()).hexdigest()[:20]
    destino = DESTINO / (identificador + '.webp')
    miniatura = DESTINO / (identificador + '-thumb.webp')
    if not destino.exists() or not miniatura.exists():
        if original.startswith('/static/'):
            conteudo = (ROOT / unquote(original).lstrip('/')).read_bytes()
        else:
            # O iNaturalist oferece uma versão de 1024px, suficiente para a ficha.
            url = original.replace('/original.', '/large.') if 'inaturalist' in original else foto.get('url_media', original)
            conteudo = requisitar(url, imagem=True)
        with Image.open(io.BytesIO(conteudo)) as imagem:
            imagem = ImageOps.exif_transpose(imagem).convert('RGB')
            if min(imagem.size) < 100:
                raise ValueError('Imagem pequena demais')
            DESTINO.mkdir(parents=True, exist_ok=True)
            imagem.thumbnail((1200, 1200))
            imagem.save(destino, 'WEBP', quality=80, method=4)
            imagem.thumbnail((480, 480))
            imagem.save(miniatura, 'WEBP', quality=74, method=4)
    return {'url': '/static/fotos/catalogo/' + destino.name,
            'url_media': '/static/fotos/catalogo/' + miniatura.name, 'url_original': original}


def buscar(planta):
    nomes = list(dict.fromkeys([planta['nome_cientifico']] + [o['nome_original'] for o in planta['ocorrencias']]))
    erros = []
    for nome in nomes:
        match = combinar_nome(nome, planta['familia'])
        if not match:
            continue
        for foto in candidatos(match)[:6]:
            try:
                local = otimizar(foto)
                return {**foto, **local}, None
            except Exception as erro:
                erros.append(str(erro))
        # Nomes originais ainda podem ter registros fotográficos próprios.
    return None, '; '.join(erros[-2:]) or 'Nenhuma imagem licenciada com correspondência exata'


def executar():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--workers', type=int, default=6)
    parser.add_argument('--existentes', action='store_true', help='Também gerar miniaturas das fotos já associadas')
    parser.add_argument('--reparar-links', action='store_true', help='Buscar alternativas para fotos remotas ainda sem cópia local')
    parser.add_argument('--somente-erros', action='store_true', help='Repetir apenas consultas que falharam por erro de acesso')
    args = parser.parse_args()
    manifesto, miniaturas = ler_json(MANIFESTO), ler_json(MINIATURAS)
    relatorio = ler_json(RELATORIO)
    plantas, _, _ = carregar_appendix('pt')
    faltantes, existentes = [], {}
    with main.app.test_request_context('/'):
        for planta in plantas:
            foto = main.montar_foto(planta['nome_cientifico'], [o['nome_original'] for o in planta['ocorrencias']])
            if foto['url'].endswith('/sem_foto.jpg') or (args.reparar_links and not foto['url'].startswith('/static/')):
                if normalizar_nome(planta['nome_cientifico']) not in manifesto:
                    anterior = relatorio.get(planta['nome_cientifico'], {})
                    if not args.somente_erros or (anterior.get('motivo') and anterior['motivo'] != 'Nenhuma imagem licenciada com correspondência exata'):
                        faltantes.append(planta)
            elif not foto['url'].startswith('/static/fotos/catalogo/'):
                existentes[foto['url']] = foto
    if args.limit:
        faltantes = faltantes[:args.limit]
    inicio = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        tarefas = {pool.submit(buscar, p): p['nome_cientifico'] for p in faltantes}
        for indice, tarefa in enumerate(as_completed(tarefas), 1):
            nome = tarefas[tarefa]
            try:
                foto, erro = tarefa.result()
                if foto:
                    manifesto[normalizar_nome(nome)] = foto
                    salvar_json(MANIFESTO, manifesto)
                relatorio[nome] = {'encontrada': bool(foto), 'motivo': erro,
                                  'fonte': foto['fonte'] if foto else None}
            except Exception as erro:
                relatorio[nome] = {'encontrada': False, 'motivo': str(erro)}
            salvar_json(RELATORIO, relatorio)
            print(f"Busca {indice}/{len(tarefas)}: {nome} | {'OK' if relatorio[nome]['encontrada'] else relatorio[nome]['motivo']}", flush=True)
        if args.existentes:
            tarefas = {pool.submit(otimizar, foto): url for url, foto in existentes.items() if url not in miniaturas}
            for indice, tarefa in enumerate(as_completed(tarefas), 1):
                url = tarefas[tarefa]
                try:
                    miniaturas[url] = tarefa.result()
                    salvar_json(MINIATURAS, miniaturas)
                except Exception as erro:
                    print(f"Miniatura indisponível: {url}: {erro}", flush=True)
                if indice % 20 == 0:
                    print(f"Miniaturas: {indice}/{len(tarefas)}", flush=True)
    print(f"Concluído em {time.perf_counter()-inicio:.1f}s: {len(manifesto)} fotos novas; {len(miniaturas)} fotos existentes otimizadas.", flush=True)


if __name__ == '__main__':
    executar()

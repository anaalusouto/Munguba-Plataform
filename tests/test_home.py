"""Regressões do Appendix S1 e da navegação PT/EN, sem acesso ao MySQL."""
import copy
import json
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main
from ocorrencias import carregar_appendix, caminho_appendix, coordenadas_validas


class AppendixTest(unittest.TestCase):
    def test_integridade_das_duas_versoes(self):
        ids_por_idioma = []
        for idioma in ('pt', 'en'):
            plantas, stats, filtros = carregar_appendix(idioma)
            self.assertEqual(stats['total_ocorrencias'], 1183)
            self.assertEqual(stats['total_especies'], 523)
            self.assertEqual(stats['total_ocorrencia_geo'], 260)
            self.assertEqual(stats['total_area_geo'], 923)
            self.assertEqual(stats['total_pontos'], 1183)
            self.assertEqual(len(filtros['categorias']), 9)
            ids = {o['id'] for p in plantas for o in p['ocorrencias']}
            self.assertEqual(len(ids), 1183)
            self.assertTrue(all(set(p['tags']).issubset(filtros['categorias']) for p in plantas))
            ids_por_idioma.append(ids)
        self.assertEqual(*ids_por_idioma)

    def test_dados_traduzidos_e_nomes_preservados(self):
        pt, _, _ = carregar_appendix('pt')
        en, _, _ = carregar_appendix('en')
        self.assertEqual([p['nome_cientifico'] for p in pt], [p['nome_cientifico'] for p in en])
        for a, b in zip(pt, en):
            self.assertEqual(a['nomes_populares'], b['nomes_populares'])
        self.assertTrue(any('Food and nutrition' in p['tags'] for p in en))
        self.assertTrue(any('Alimentação e nutrição' in p['tags'] for p in pt))

    def test_cache_nao_contamina_requisicoes(self):
        plantas, _, _ = carregar_appendix('pt')
        plantas[0]['tags'].append('teste')
        outras, _, _ = carregar_appendix('pt')
        self.assertNotIn('teste', outras[0]['tags'])

    def test_coordenadas(self):
        for lat, lng in [(0, 0), ('-1.49', '-48.45'), (-90, 180)]:
            self.assertTrue(coordenadas_validas(lat, lng))
        for lat, lng in [(None, 1), (1, None), (91, 0), (0, -181), (float('nan'), 0), (0, float('inf')), ('errado', 1)]:
            self.assertFalse(coordenadas_validas(lat, lng))


class HomeTest(unittest.TestCase):
    def setUp(self):
        self.client = main.app.test_client()
        self.fotos = patch.object(main, 'buscar_foto', return_value=None)
        self.fotos.start()
        self.addCleanup(self.fotos.stop)

    def test_home_bilingue_e_persistencia(self):
        for idioma, html_lang, titulo in [('pt', 'pt-BR', 'Registros de ocorrência'), ('en', 'en', 'Occurrence records')]:
            resposta = self.client.get('/?lang=' + idioma)
            self.assertEqual(resposta.status_code, 200)
            html = resposta.get_data(as_text=True)
            self.assertIn('lang="' + html_lang + '"', html)
            self.assertIn(titulo, html)
            self.assertIn('>1183<', html)
            self.assertIn('>523<', html)
            self.assertIn('>9<', html)
            self.assertLess(len(resposta.data), 800_000)
            self.assertNotIn('id="modal-detalhe-1"', html)
            dados = json.loads(re.search(r'const plantasMapa = (.*);', html).group(1))
            self.assertEqual(sum(len(p['pontos_gps']) for p in dados), 260)
            self.assertTrue(all(o['nivel'] == 'occurrence' for p in dados for o in p['pontos_gps']))
            catalogo = json.loads(re.search(r'const plantasCatalogo = (.*);', html).group(1))
            self.assertEqual(len(catalogo), 523)
            self.assertEqual([p['id'] for p in catalogo], list(range(1, 524)))
            self.assertTrue(all(p['busca'] and p['imagem'] for p in catalogo))
            self.assertNotIn('data-search=', html)
            self.assertIn('https://tile.openstreetmap.org/', html)
            self.assertNotIn('basemaps.cartocdn.com', html)
        self.assertIn('Occurrence records', self.client.get('/').get_data(as_text=True))
        self.assertIn('Registros de ocorrência', self.client.get('/?lang=invalido').get_data(as_text=True))

    def test_exportacao_respeita_idioma(self):
        for idioma in ('pt', 'en'):
            resposta = self.client.get('/exportar-dados?lang=' + idioma)
            self.assertEqual(resposta.status_code, 200)
            self.assertIn(caminho_appendix(idioma).name, resposta.headers['Content-Disposition'])
            self.assertEqual(resposta.data, caminho_appendix(idioma).read_bytes())
            resposta.close()

    def test_ficha_com_ocorrencias_nos_dois_idiomas(self):
        for idioma, rotulo in [('pt', 'Registros deste táxon'), ('en', 'Records for this taxon')]:
            plantas, _, _ = carregar_appendix(idioma)
            indice = next(i + 1 for i, p in enumerate(plantas)
                          if any(o['id'] == 'COMBU_0001' for o in p['ocorrencias']))
            resposta = self.client.get(f'/taxon/{indice}?lang={idioma}')
            self.assertEqual(resposta.status_code, 200)
            html = resposta.get_data(as_text=True)
            self.assertIn('COMBU_0001', html)
            self.assertIn(rotulo, html)
            self.assertIn('3416', html)
        self.assertEqual(self.client.get('/taxon/0').status_code, 404)
        self.assertEqual(self.client.get('/taxon/99999').status_code, 404)

    def test_nome_nao_pode_encerrar_script(self):
        plantas, stats, filtros = carregar_appendix('pt')
        plantas = copy.deepcopy(plantas[:1])
        nome = 'Açaí ` ${teste} </script>'
        plantas[0]['nomes_populares'] = [nome]
        with patch.object(main, 'carregar_appendix', return_value=(plantas, stats, filtros)):
            html = self.client.get('/').get_data(as_text=True)
        dados = json.loads(re.search(r'const plantasMapa = (.*);', html).group(1))
        self.assertEqual(dados[0]['nome_popular'], nome)
        self.assertNotIn(nome, html)

    def test_arquivo_ausente_retorna_erro_localizado(self):
        with patch.object(main, 'carregar_appendix', side_effect=FileNotFoundError):
            with self.assertLogs(main.app.logger, level='ERROR'):
                resposta = self.client.get('/?lang=en')
        self.assertEqual(resposta.status_code, 503)
        self.assertIn('Appendix S1 could not be loaded.', resposta.get_data(as_text=True))


if __name__ == '__main__':
    if '--preview' in sys.argv:
        main.buscar_foto = lambda nome: None
        main.app.run(host='127.0.0.1', port=5051, debug=False, use_reloader=False)
    else:
        unittest.main()

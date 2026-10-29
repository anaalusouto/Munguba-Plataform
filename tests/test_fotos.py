"""Regressões do consumo da planilha de fotos, sem depender da rede."""
import csv
import io
import json
import unittest
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory

from openpyxl import Workbook

import fotos
import main


class FotosTest(unittest.TestCase):
    def test_todas_as_linhas_com_imagem_utilizavel(self):
        csv_texto = io.StringIO()
        writer = csv.writer(csv_texto)
        writer.writerow(['Nome científico (catálogo)', 'Link da foto (alta resolução)',
                         'Link da foto (tamanho médio)', 'Autor/direitos', 'Licença',
                         'Página de referência'])
        writer.writerows([
            ['Inga alba (Sw.) Willd.', 'https://example.org/alba.jpg', '', 'Autor',
             'CC BY', 'https://example.org/fonte'],
            ['Inga edulis Mart.', '', 'https://example.org/edulis.jpg', '', '', ''],
            ['Inga vera Willd.', 'https://example.org/vera.dzi',
             'https://example.org/vera.jpg', '', '', ''],
            ['Inga sp. 1', '', '', '', '', ''],
        ])
        resposta = io.BytesIO(('\ufeff' + csv_texto.getvalue()).encode('utf-8'))
        with patch.object(fotos.urllib.request, 'urlopen', return_value=resposta) as abrir:
            imagens, binomios = fotos._carregar_planilha()
        self.assertEqual(len(imagens), 3)
        self.assertEqual(len(binomios), 3)
        self.assertEqual(binomios['inga vera']['url'], 'https://example.org/vera.jpg')
        self.assertEqual(binomios['inga edulis']['url'], 'https://example.org/edulis.jpg')
        self.assertEqual(binomios['inga alba']['autor'], 'Autor')
        self.assertIn('gid=1140076266', abrir.call_args.args[0])

    def test_aba_invalida_nao_substitui_cache(self):
        with patch.object(fotos.urllib.request, 'urlopen',
                          return_value=io.BytesIO(b'<html>Login</html>')):
            with self.assertRaises(ValueError):
                fotos._carregar_planilha()

    def test_foto_pelo_nome_original_do_registro(self):
        foto = {'url': 'https://example.org/foto.jpg'}
        with main.app.test_request_context('/'), patch.object(
                main, 'buscar_foto', side_effect=[None, foto]) as buscar:
            resultado = main.montar_foto('Nome aceito', ['Nome original', 'Nome original'])
        self.assertEqual(resultado, foto)
        self.assertEqual([c.args[0] for c in buscar.call_args_list],
                         ['Nome aceito', 'Nome original'])

    def test_falha_temporaria_preserva_fotos_e_tenta_em_um_minuto(self):
        cache = {'fotos': {'inga alba': {'url': 'foto'}}, 'binomios': {}, 'carregado_em': 0}
        with patch.object(fotos.FOTOS_ARQUIVO.__class__, 'is_file', return_value=False), \
                patch.object(fotos, '_cache', cache), patch.object(fotos.time, 'time', return_value=10000), \
                patch.object(fotos, '_carregar_planilha', side_effect=OSError('offline')), \
                self.assertLogs(fotos.logger, level='WARNING'):
            fotos._garantir_cache()
        self.assertIn('inga alba', cache['fotos'])
        self.assertEqual(cache['carregado_em'] + fotos.CACHE_SEGUNDOS, 10060)

    def test_arquivo_local_sem_acesso_ao_google(self):
        cache = {'fotos': None, 'binomios': None, 'carregado_em': 0}
        with patch.object(fotos, '_cache', cache), \
                patch.object(fotos.urllib.request, 'urlopen', side_effect=AssertionError('Rede desnecessária')):
            foto = fotos.buscar_foto('Aspasia variegata')
        self.assertIn('/376017265/', foto.get('url_original', foto['url']))
        self.assertEqual(foto['autor'], 'audreyenguyane')
        self.assertTrue(foto['licenca'])
        self.assertEqual(len(cache['fotos']), 237)

    def test_servico_fsi_raster_e_dzi_bruto(self):
        raster = 'http://jbrj-public.s3.amazonaws.com/fsi/server?type=image&source=DZI/exemplo.dzi'
        self.assertEqual(fotos._link_de_imagem(raster), raster.replace('http:', 'https:'))
        self.assertEqual(fotos._link_de_imagem('https://example.org/exemplo.dzi'), '')

    def test_arquivo_com_aba_inicial_de_instrucoes_e_linhas_vazias(self):
        with TemporaryDirectory() as pasta:
            caminho = Path(pasta) / 'fotos.xlsx'
            workbook = Workbook()
            workbook.active.append(['Instruções'])
            aba = workbook.create_sheet('Fotos')
            aba.append(['Nome científico (catálogo)', 'Link da foto (tamanho médio)'])
            aba.append([None, None])
            aba.append(['Inga alba', 'https://example.org/alba.jpg'])
            workbook.save(caminho)
            workbook.close()
            with patch.object(fotos, 'FOTOS_ARQUIVO', caminho):
                imagens, _ = fotos._carregar_arquivo()
        self.assertEqual(imagens['inga alba']['url'], 'https://example.org/alba.jpg')

    def test_manifestos_publicados_apontam_para_arquivos_existentes(self):
        raiz = Path(main.BASE_DIR)
        for manifesto in (fotos.FOTOS_COMPLEMENTARES, fotos.FOTOS_MINIATURAS):
            dados = json.loads(manifesto.read_text(encoding='utf-8'))
            self.assertTrue(dados)
            for chave, foto in dados.items():
                for campo in ('url', 'url_media'):
                    caminho = foto[campo]
                    self.assertTrue(caminho.startswith('/static/fotos/catalogo/'), chave)
                    self.assertTrue((raiz / caminho.lstrip('/')).is_file(), chave)
                if manifesto == fotos.FOTOS_COMPLEMENTARES:
                    self.assertTrue(all(foto.get(k) for k in ('autor', 'licenca', 'fonte', 'taxon_gbif')), chave)

    def test_cache_http_das_miniaturas(self):
        dados = json.loads(fotos.FOTOS_MINIATURAS.read_text(encoding='utf-8'))
        caminho = next(iter(dados.values()))['url_media']
        with main.app.test_client() as client:
            resposta = client.get(caminho)
            self.assertEqual(resposta.status_code, 200)
            self.assertEqual(resposta.mimetype, 'image/webp')
            self.assertIn('max-age=604800', resposta.headers['Cache-Control'])
            resposta.close()


if __name__ == '__main__':
    unittest.main()

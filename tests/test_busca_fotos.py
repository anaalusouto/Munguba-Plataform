"""Não atribuir fotos de táxons diferentes ou sem licença de imagem."""
import unittest
from unittest.mock import patch

from scripts import buscar_fotos
from fotos import binomio


class BuscaFotosTest(unittest.TestCase):
    def test_especie_com_hifen_e_identificacao_incompleta(self):
        self.assertEqual(binomio('Hibiscus rosa-sinensis L.'), 'hibiscus rosa-sinensis')
        for nome in ('Inga sp. 1', 'Inga cf. alba', 'Inga', 'Inga spp.'):
            self.assertIsNone(binomio(nome))

    def test_nao_aceita_match_apenas_no_genero_ou_familia_diferente(self):
        base = {'matchType': 'EXACT', 'confidence': 100, 'rank': 'SPECIES',
                'kingdom': 'Plantae', 'family': 'Fabaceae', 'usageKey': 123}
        for alteracao in ({'rank': 'GENUS'}, {'matchType': 'FUZZY'},
                          {'family': 'Rubiaceae'}, {'confidence': 80}):
            with patch.object(buscar_fotos, 'requisitar', return_value={**base, **alteracao}):
                self.assertIsNone(buscar_fotos.combinar_nome('Inga alba', 'Fabaceae'))
        with patch.object(buscar_fotos, 'requisitar', return_value=base):
            self.assertEqual(buscar_fotos.combinar_nome('Inga alba', 'Fabaceae')['usageKey'], 123)

    def test_nao_usa_licenca_do_registro_como_licenca_da_foto(self):
        registro = {'key': 456, 'speciesKey': 123, 'basisOfRecord': 'HUMAN_OBSERVATION',
                    'scientificName': 'Inga alba', 'license': 'https://creativecommons.org/licenses/by/4.0/',
                    'media': [{'identifier': 'https://example.org/foto.jpg', 'creator': 'Autora'}]}
        with patch.object(buscar_fotos, 'requisitar', return_value={'results': [registro]}):
            self.assertEqual(buscar_fotos.candidatos({'usageKey': 123}), [])
        registro['media'][0]['license'] = 'https://creativecommons.org/licenses/by/4.0/'
        with patch.object(buscar_fotos, 'requisitar', return_value={'results': [registro]}):
            self.assertEqual(buscar_fotos.candidatos({'usageKey': 123})[0]['autor'], 'Autora')
        registro['speciesKey'] = 999
        with patch.object(buscar_fotos, 'requisitar', return_value={'results': [registro]}):
            self.assertEqual(buscar_fotos.candidatos({'usageKey': 123}), [])

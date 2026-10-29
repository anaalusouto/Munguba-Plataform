"""Textos da interface. Os dados científicos vêm dos respectivos Appendix S1."""
from flask import request, url_for

EN = {
    'Pontos com localização incerta': 'Points with uncertain locations',
    'Plantas com localização incerta': 'Plants with uncertain locations',
    'Coordenada aproximada compartilhada por estas plantas.': 'Approximate coordinate shared by these plants.',
    'Buscar planta neste ponto...': 'Find a plant at this point...',
    'plantas com referência neste ponto': 'plants referenced at this point',
    'Carregando pontos de referência...': 'Loading reference points...',
    'Não foi possível carregar os pontos de referência. Desative e ative a opção para tentar novamente.': 'Reference points could not be loaded. Turn the option off and on to try again.',
    'Pontos: ocorrências registradas': 'Points: recorded occurrences',
    'Áreas: localizações incertas': 'Areas: uncertain locations',
    'Localização de referência': 'Reference location',
    'Área aproximada; não indica o ponto exato de cada planta.': 'Approximate area; it does not indicate the exact location of each plant.',
    'Incerteza informada (m)': 'Reported uncertainty (m)',
    'Buscar planta nesta área...': 'Find a plant in this area...',
    'plantas com referência nesta área': 'plants referenced in this area',
    'plantas com localização de referência': 'plants with a reference location',
    'Fonte da localização': 'Location source',
    'Carregando áreas de referência...': 'Loading reference areas...',
    'Não foi possível carregar as áreas de referência.': 'Reference areas could not be loaded.',
    'Não foi possível carregar as áreas de referência. Desative e ative a opção para tentar novamente.': 'Reference areas could not be loaded. Turn the option off and on to try again.',
    'Mostrar mais espécies': 'Show more taxa', 'Exibindo': 'Showing', 'de': 'of',
    'Plataforma Munguba': 'Munguba Platform',
    'Acessar Catálogo': 'Browse Catalogue', 'Acessar Mapa': 'Explore Map',
    'Exportar Dados': 'Download Data', 'Catálogo': 'Catalogue', 'Mapa': 'Map', 'Exportar': 'Download',
    'Navegação principal no celular': 'Mobile navigation',
    'MUNGUBA • Plataforma de lista de espécies florísticas': 'MUNGUBA • Floristic records platform',
    'de uso Bioeconômico': 'Bioeconomic uses', 'da Ilha do Combu': 'of Combu Island',
    'Busque por termo...': 'Search by term...', 'Pesquisar': 'Search',
    'Espécies': 'Species', 'Táxons': 'Taxa', 'Registros de ocorrência': 'Occurrence records',
    'Ocorrências com coordenadas válidas': 'Occurrences with valid coordinates',
    'Categorias de Uso': 'Use Categories', 'Destaques no Mapa': 'Map Highlights',
    'Mostrar Tudo': 'Show All', 'Filtros': 'Filters', 'Limpar': 'Clear', 'Todas': 'All',
    'Por Parte:': 'By Plant Part:', 'Pesquise por nome, família, uso...': 'Search by name, family, use...',
    'Pesquisar espécies': 'Search taxa', 'Categoria': 'Category', 'Limpar Filtro': 'Clear Filter',
    'Fechar catálogo': 'Close catalogue', 'Fechar Janela': 'Close Window', 'Fechar ficha': 'Close record',
    'Ficha Técnica': 'Taxon Details', 'Família': 'Family', 'Nome Popular': 'Vernacular Name',
    'Nome Científico': 'Scientific Name', 'Habitat': 'Habitat', 'Uso Bioeconômico': 'Bioeconomic Use',
    'Partes Utilizadas': 'Plant Parts Used', 'Localização': 'Location', 'Abrir Mapa': 'Open Map',
    'Referências': 'References', 'Sem referências cadastradas.': 'No references recorded.',
    'Sem descrição.': 'No description recorded.', 'Não informado': 'Not recorded',
    'Foto de': 'Photo of', 'Ver Ficha': 'View Record',
    'Nenhuma espécie encontrada. Tente outro termo ou limpe os filtros.': 'No taxa found. Try another term or clear the filters.',
    'Não foi possível carregar o mapa. Recarregue a página para tentar novamente.': 'The map could not be loaded. Reload the page to try again.',
    'Não foi possível carregar parte do mapa. Confira sua conexão e recarregue a página.': 'Part of the map could not be loaded. Check your connection and reload the page.',
    'Nenhuma ocorrência com coordenadas válidas para esta seleção.': 'No occurrence-level coordinates are available for this selection.',
    'Dados: Appendix S1 • Licença CC BY 4.0': 'Data: Appendix S1 • CC BY 4.0 licence',
    'Ocorrências georreferenciadas': 'Georeferenced occurrences',
    'Referências de área': 'Area references',
    'Incluir referências de área no mapa': 'Include area references on the map',
    'As referências de área representam uma localidade, não o ponto exato da espécie.': 'Area references represent a locality, not the exact location of a taxon.',
    'Os nomes científicos, nomes populares e citações são preservados como na fonte.': 'Scientific names, vernacular names and citations are preserved as recorded in the source.',
    'Registros deste táxon': 'Records for this taxon', 'Fonte': 'Source', 'Data': 'Date',
    'Georreferência': 'Georeference', 'Ocorrência': 'Occurrence', 'Área de referência': 'Area reference',
    'Incerteza (m)': 'Uncertainty (m)', 'Nome na fonte': 'Name in source',
    'Detalhes da georreferência': 'Georeferencing details', 'Forma de vida': 'Life Form',
    'Uso não documentado': 'Use not documented', 'Acessar Fonte / Artigo': 'View Source / Article',
    'Baixar Appendix S1': 'Download Appendix S1',
    'Não foi possível carregar o Appendix S1.': 'Appendix S1 could not be loaded.',
    'Tente novamente mais tarde.': 'Please try again later.',
    'Carregando ficha...': 'Loading record...',
    'Verificação da georreferência': 'Georeference verification',
    'Requer verificação': 'Requires verification',
    'Aproximar': 'Zoom in', 'Afastar': 'Zoom out', 'Fechar popup': 'Close popup',
    'Não foi possível carregar a ficha. Tente novamente.': 'The record could not be loaded. Please try again.',
}


def idioma_atual():
    idioma = request.args.get('lang', request.cookies.get('munguba_lang', 'pt')).lower()
    return idioma if idioma in ('pt', 'en') else 'pt'


def traduzir(texto, idioma):
    return EN.get(texto, texto) if idioma == 'en' else texto


def contexto_idioma():
    idioma = idioma_atual()
    return {
        'idioma': idioma, 't': lambda texto: traduzir(texto, idioma),
        'url_idioma': lambda codigo: url_for('index', lang=codigo),
    }

"""Guarda a versão do Leaflet já usada pelo site para dispensar o CDN."""
from pathlib import Path
from urllib.request import urlopen

destino = Path(__file__).resolve().parents[1] / 'static' / 'vendor' / 'leaflet'
for arquivo in ('leaflet.js', 'leaflet.css', 'images/layers.png', 'images/layers-2x.png',
                'images/marker-icon.png', 'images/marker-icon-2x.png', 'images/marker-shadow.png'):
    alvo = destino / arquivo
    alvo.parent.mkdir(parents=True, exist_ok=True)
    with urlopen('https://unpkg.com/leaflet@1.9.4/dist/' + arquivo, timeout=25) as resposta:
        alvo.write_bytes(resposta.read())
with urlopen('https://unpkg.com/leaflet@1.9.4/LICENSE', timeout=25) as resposta:
    (destino / 'LICENSE').write_bytes(resposta.read())
print('Leaflet local preparado.')

"""Guarda os ícones existentes no projeto para dispensar o CDN em produção."""
from pathlib import Path
import re
from urllib.request import urlopen

destino = Path(__file__).resolve().parents[1] / 'static' / 'vendor' / 'remixicon'
destino.mkdir(parents=True, exist_ok=True)
base = 'https://cdn.jsdelivr.net/npm/remixicon@3.5.0/fonts/'
with urlopen(base + 'remixicon.css', timeout=25) as resposta:
    css = resposta.read().decode('utf-8')
with urlopen(base + 'remixicon.woff2', timeout=25) as resposta:
    (destino / 'remixicon.woff2').write_bytes(resposta.read())
css = re.sub(r'@font-face\s*\{.*?\}',
             '@font-face{font-family:"remixicon";src:url("remixicon.woff2") format("woff2");font-display:swap;}',
             css, count=1, flags=re.S)
(destino / 'remixicon.css').write_text(css, encoding='utf-8')
with urlopen('https://cdn.jsdelivr.net/npm/remixicon@3.5.0/License', timeout=25) as resposta:
    (destino / 'LICENSE').write_bytes(resposta.read())
print('Ícones locais preparados.')

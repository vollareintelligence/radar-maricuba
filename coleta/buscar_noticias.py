"""Coleta notícias sobre Maricá e o prefeito a partir de feeds RSS públicos.

Fonte: Google News RSS (sem chave, sem custo). Serviço não oficial: pode mudar
ou sair do ar sem aviso. Por isso o script falha de forma explícita e não
publica nada incompleto.

Saída: dados/consolidado/noticias.json
  - cada item tem título, link, data, veículo (domínio do editor) e os temas
    (ids de promessa) que a consulta cobriu
  - só entra notícia com data e com "Maricá" ou "Quaquá" no título
  - deduplicado por título normalizado
"""
import hashlib
import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / 'dados' / 'consolidado' / 'noticias.json'
JANELA_DIAS = 730
TIMEOUT = 20
TENTATIVAS = 3
PAUSA_ENTRE_CONSULTAS = 3.0   # segundos; evita bloqueio por excesso de pedidos
VEICULOS_BLOQUEADOS = {'lrcadefenseconsulting.com'}  # fonte sem credibilidade editorial
USER_AGENT = 'Mozilla/5.0 (compatible; LupaMarica/1.0; +https://lupamarica.com/)'

# Cada consulta serve a UMA promessa de dados/consolidado/promessas.json: o 'tema' é o id dela.
# Não há tema genérico (ex.: 'Prefeito'): notícia sem promessa correspondente não entra.
CONSULTAS = [
    # (tema, consulta no Google News, palavras que o título precisa ter para contar como esse tema)
    ('foguetes', 'Maricá foguete OR lançamento Ilhas Maricás', ['foguet', 'lancamento', 'espacial', 'ilhas maricas']),
    ('aviões', 'Maricá Embraer OR fábrica aviões', ['embraer', 'aviao', 'aeronave', 'fabrica de avi']),
    ('braco', 'Maricá braço de pedra Itaipuaçu', ['braco de pedra', 'enrocamento', 'molhe']),
    ('hoteis', 'Maricá hotel público Quaquá', [r'\bhotel(es)?\b', 'maraey']),
    ('piscina', 'Maricá piscina água salgada', ['piscina']),
    ('catamara', 'Maricá catamarã Santos Dumont', ['catamar']),
    ('aeroporto', 'Maricá aeroporto pista', ['aeroporto', 'pista']),
    ('roda', 'Maricá roda-gigante', ['roda-gigante', 'roda gigante']),
    ('vlt', 'Maricá VLT OR teleférico OR bonde', [r'\bvlt\b', 'telefer', 'trilho']),
    ('asfalto', 'Maricá asfalto ruas pavimentação', ['asfalt', 'pavimenta']),
    ('esgoto', 'Maricá esgoto saneamento Quaquá', ['esgoto', 'saneamento']),
]


def normalizar(texto):
    sem_acento = unicodedata.normalize('NFKD', texto or '')
    sem_acento = ''.join(c for c in sem_acento if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', sem_acento).strip().lower()


def url_feed(consulta):
    params = urllib.parse.urlencode({'q': consulta, 'hl': 'pt-BR', 'gl': 'BR', 'ceid': 'BR:pt-419'})
    return f'https://news.google.com/rss/search?{params}'


def baixar(url):
    """Baixa com nova tentativa e espera crescente. Erro final sobe: nunca vira 'sem notícia'."""
    ultimo = None
    for n in range(TENTATIVAS):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return r.read()
        except Exception as e:
            ultimo = e
            time.sleep(5 * (n + 1))
    raise ultimo


def ler_feed(xml_bytes, tema):
    raiz = ET.fromstring(xml_bytes)
    itens = []
    for it in raiz.iter('item'):
        titulo = (it.findtext('title') or '').strip()
        link = (it.findtext('link') or '').strip()
        pub = it.findtext('pubDate')
        fonte_el = it.find('source')
        veiculo = (fonte_el.text or '').strip() if fonte_el is not None else ''
        dominio = fonte_el.get('url', '') if fonte_el is not None else ''
        try:
            data = parsedate_to_datetime(pub).astimezone(timezone.utc)
        except (TypeError, ValueError):
            continue  # sem data, não entra
        itens.append({'titulo': titulo, 'link': link, 'data': data, 'veiculo': veiculo,
                      'dominioVeiculo': dominio, 'tema': tema})
    return itens


def relevante(item, limite, palavras):
    if item['data'] < limite:
        return False
    host = re.sub(r'^https?://(www\.)?', '', item.get('dominioVeiculo', '')).split('/')[0]
    if host in VEICULOS_BLOQUEADOS:
        return False
    # o veículo vem no fim do título ("... - Maricá Info"): tira antes de testar
    t = normalizar(sem_veiculo(item['titulo'], item['veiculo']))
    if not ('maric' in t or 'quaqua' in t):
        return False
    return any(re.search(p, t) for p in palavras)


def id_noticia(titulo, veiculo):
    base = normalizar(sem_veiculo(titulo, veiculo))
    return hashlib.sha1(base.encode('utf-8')).hexdigest()[:10]


def link_original(link):
    """Tenta trocar o redirecionamento do Google News pelo endereço da matéria.
    Melhor esforço: se o Google mudar o formato ou bloquear, devolve None e o link
    do Google News é mantido (marcado como não original)."""
    try:
        m = re.search(r'/articles/([^?/]+)', link)
        if not m:
            return None
        art = m.group(1)
        html = baixar_uma_vez(f'https://news.google.com/rss/articles/{art}').decode('utf-8', 'ignore')
        sg = re.search(r'data-n-a-sg="([^"]+)"', html)
        ts = re.search(r'data-n-a-ts="([^"]+)"', html)
        if not (sg and ts):
            return None
        req = ['Fbv4je', json.dumps(['garturlreq', [['X', 'X', ['X', 'X'], None, None, 1, 1, 'BR:pt-419', None, 1, None, None, None, None, None, 0, 1], 'X', 'X', 1, [1, 1, 1], 1, 1, None, 0, 0, None, 0], art, int(ts.group(1)), sg.group(1)])]
        corpo = urllib.parse.urlencode({'f.req': json.dumps([[req]])}).encode()
        r = urllib.request.Request('https://news.google.com/_/DotsSplashUi/data/batchexecute', data=corpo,
                                   headers={'User-Agent': USER_AGENT, 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'})
        with urllib.request.urlopen(r, timeout=TIMEOUT) as resp:
            txt = resp.read().decode('utf-8', 'ignore')
        u = re.search(r'garturlres\\",\\"(https?:[^"\\]+)', txt)
        return u.group(1) if u else None
    except Exception:
        return None


def baixar_uma_vez(url):
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read()


def sem_veiculo(titulo, veiculo):
    """Google News põe ' - Veículo' no fim do título. Tira para deduplicar."""
    if veiculo and titulo.endswith(' - ' + veiculo):
        return titulo[: -len(veiculo) - 3]
    return titulo


def coletar():
    limite = datetime.now(timezone.utc) - timedelta(days=JANELA_DIAS)
    vistos = {}
    falhas = []
    for n, (tema, consulta, palavras) in enumerate(CONSULTAS):
        if n:
            time.sleep(PAUSA_ENTRE_CONSULTAS)
        try:
            itens = ler_feed(baixar(url_feed(consulta)), tema)
        except Exception as e:  # rede, XML ou bloqueio
            falhas.append(f'{tema}: {type(e).__name__}')
            continue
        for it in itens:
            if not relevante(it, limite, palavras):
                continue
            chave = normalizar(sem_veiculo(it['titulo'], it['veiculo']))
            if chave in vistos:
                vistos[chave]['temas'] = sorted(set(vistos[chave]['temas']) | {tema})
                continue
            vistos[chave] = {**it, 'temas': [tema]}
            del vistos[chave]['tema']
    return sorted(vistos.values(), key=lambda x: x['data'], reverse=True), falhas


def main():
    itens, falhas = coletar()
    if falhas:  # busca incompleta não pode virar "sem notícia": mantém o arquivo anterior e falha
        print('ERRO: consultas sem resposta (' + '; '.join(falhas) + '). Nada foi gravado.', file=sys.stderr)
        sys.exit(1)
    saida = {
        'coletadoEm': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'janelaDias': JANELA_DIAS,
        'fonte': 'Google News RSS (não oficial)',
        'consultas': len(CONSULTAS),
        'falhas': falhas,
        'total': len(itens),
        'itens': [
            {'id': id_noticia(i['titulo'], i['veiculo']), 'titulo': i['titulo'], 'link': i['link'], 'linkOriginal': i.get('linkOriginal'), 'data': i['data'].strftime('%Y-%m-%d'),
             'veiculo': i['veiculo'], 'dominioVeiculo': i['dominioVeiculo'], 'temas': i['temas']}
            for i in itens
        ],
    }
    pend = [i for i in itens]
    for i in pend:  # só resolve o que ainda não foi decidido, para não martelar o Google
        time.sleep(1.0)
        i['linkOriginal'] = link_original(i['link'])
    saida['itens'] = [
        {'id': id_noticia(i['titulo'], i['veiculo']), 'titulo': i['titulo'], 'link': i['link'], 'linkOriginal': i.get('linkOriginal'),
         'data': i['data'].strftime('%Y-%m-%d'), 'veiculo': i['veiculo'], 'dominioVeiculo': i['dominioVeiculo'], 'temas': i['temas']}
        for i in itens]
    SAIDA.write_text(json.dumps(saida, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'NOTICIAS: {len(itens)} itens; falhas: {len(falhas)}')


if __name__ == '__main__':
    main()

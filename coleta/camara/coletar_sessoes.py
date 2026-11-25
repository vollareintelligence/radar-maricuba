import os
import json
import csv
import urllib.request
import time
from datetime import datetime

import os as _os, time as _time
from pathlib import Path as _P
ROOT = str(_P(__file__).resolve().parents[2])
CACHE_DIR = _os.environ.get('LUPA_CACHE_DIR', _os.path.join(ROOT, 'dados', 'cache'))
OUTPUT_DIR = _os.path.join(ROOT, 'dados', 'brutos')
_os.makedirs(CACHE_DIR, exist_ok=True)
_os.makedirs(OUTPUT_DIR, exist_ok=True)

def _fresco(path, horas):
    """Cache válido se existe e tem menos de `horas` horas."""
    return _os.path.exists(path) and (_time.time() - _os.path.getmtime(path)) < horas * 3600
USER_AGENT = 'RadarMaricuba/0.1 (coleta de dados publicos; contato: theobarros.com.br)'
HEADERS = {'User-Agent': USER_AGENT}

def fetch_json(url, cache_filename):
    cache_path = os.path.join(CACHE_DIR, cache_filename)
    if _fresco(cache_path, 6):
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    print(f"Fetching {url} -> {cache_filename}")
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    time.sleep(2.5)
    return data

sessoes_all = []

for ano in [2025, 2026]:
    url = f'https://marica.sicam.app/integracao/?Pautas/{ano}/Json'
    data = fetch_json(url, f'pautas_{ano}.json')
    lista = data.get('Lista', [])
    print(f"Ano {ano}: {len(lista)} sessoes encontradas.")
    
    for item in lista:
        id_sessao = item.get('Id')
        tipo = item.get('Tipo', '')
        raw_data = item.get('Data', '')
        
        # Split Data and Hora
        partes = raw_data.split(' - ')
        data_str = partes[0].strip() if len(partes) > 0 else ''
        hora_str = partes[1].strip() if len(partes) > 1 else ''
        
        numero = item.get('Numero', '')
        presidente = item.get('Presidente', '')
        
        # Pauta
        arq_pauta = item.get('Arquivo') or ''
        tem_pauta = 'sim' if arq_pauta or item.get('Pauta') else 'não'
        url_pauta = ''
        if arq_pauta:
            url_pauta = f"https://marica.sicam.app{arq_pauta}" if arq_pauta.startswith('/') else arq_pauta
        elif item.get('Pauta'):
            p = item.get('Pauta')
            url_pauta = f"https://marica.sicam.app{p}" if p.startswith('/') else p

        # Ata
        caminho_ata = (item.get('CaminhoAta') or '').strip()
        tem_ata = 'sim' if caminho_ata else 'não'
        url_ata = caminho_ata

        # Presenca
        ficha = (item.get('Ficha') or '').strip()
        tem_presenca = 'sim' if ficha else 'não'
        url_presenca = f"https://marica.sicam.app{ficha}" if ficha.startswith('/') else ficha

        # Votacao
        votacao_campo = (item.get('Votacao') or '').strip()
        tem_votacao = 'sim' if votacao_campo else 'não'
        url_votacao = f"https://marica.sicam.app/areapublica/?votacao/{id_sessao}" if tem_votacao == 'sim' else ''

        sessoes_all.append({
            'id_sessao': id_sessao,
            'data': data_str,
            'hora': hora_str,
            'tipo': tipo,
            'numero': numero,
            'presidente': presidente,
            'tem_pauta': tem_pauta,
            'tem_ata': tem_ata,
            'tem_presenca': tem_presenca,
            'tem_votacao': tem_votacao,
            'url_pauta': url_pauta,
            'url_ata': url_ata,
            'url_presenca': url_presenca,
            'url_votacao': url_votacao
        })

# Sort sessions chronologically
def parse_date_sort(s):
    try:
        d = s['data']
        dia, mes, ano = d.split('/')
        h = s['hora'] if s['hora'] else '00:00:00'
        return datetime.strptime(f"{ano}-{mes}-{dia} {h}", "%Y-%m-%d %H:%M:%S")
    except Exception:
        return datetime.min

sessoes_all.sort(key=parse_date_sort)

csv_path = os.path.join(OUTPUT_DIR, 'sessoes.csv')
fieldnames = [
    'id_sessao', 'data', 'hora', 'tipo', 'numero', 'presidente',
    'tem_pauta', 'tem_ata', 'tem_presenca', 'tem_votacao',
    'url_pauta', 'url_ata', 'url_presenca', 'url_votacao'
]

with open(csv_path, 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(sessoes_all)

print(f"\nSalvo {len(sessoes_all)} sessoes em {csv_path}")

# Breakdown by type
tipos_count = {}
for s in sessoes_all:
    t = s['tipo']
    tipos_count[t] = tipos_count.get(t, 0) + 1

print("\nContagem por tipo de sessão:")
for t, c in tipos_count.items():
    print(f"  {t}: {c}")

# Check date gaps for 2026 Tuesdays/Wednesdays/etc. (Câmara usually has regular session days)
print("\nVerificando sessões de 2026 próximas a outubro:")
for s in sessoes_all:
    if '/10/2026' in s['data'] or '/11/2026' in s['data']:
        print(f"  ID {s['id_sessao']} | {s['data']} {s['hora']} | {s['tipo']} nº {s['numero']} | Votacao: {s['tem_votacao']}")

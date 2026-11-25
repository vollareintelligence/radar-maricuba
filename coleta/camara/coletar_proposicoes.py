import os
import sys
import json
import csv
import time
import urllib.request
import datetime

sys.stdout.reconfigure(line_buffering=True)

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
HEADERS = {
    'User-Agent': USER_AGENT,
    'Content-Type': 'application/json',
    'database': 'marica'
}

def formatar_data(data_str):
    if not data_str:
        return ''
    s = str(data_str).strip()
    if len(s) == 8 and s.isdigit():
        # YYYYMMDD -> DD/MM/YYYY
        return f"{s[6:8]}/{s[4:6]}/{s[0:4]}"
    return s

def buscar_proposicoes_autor(id_sicam, nome_autor):
    cache_path = os.path.join(CACHE_DIR, f'proposicoes_autor_{id_sicam}.json')
    if _fresco(cache_path, 6):
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    url = 'https://api.sicam.app/pesquisar'
    today_str = datetime.date.today().strftime('%Y-%m-%d')
    payload = {
        'vereadores': [int(id_sicam)],
        'externos': [],
        'DataInicial': '2025-01-01',
        'DataFinal': today_str,
        'TipoBusca': 'processo'
    }

    print(f"Buscando proposições do autor {id_sicam} ({nome_autor})...", flush=True)
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers=HEADERS
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode('utf-8'))

    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    time.sleep(2.5) # rate limit 1 req / 2s
    return data

def processar_todas_proposicoes():
    vereadores_csv_path = os.path.join(OUTPUT_DIR, 'vereadores.csv')
    if not os.path.exists(vereadores_csv_path):
        print(f"Erro: {vereadores_csv_path} não encontrado.", flush=True)
        return

    with open(vereadores_csv_path, 'r', encoding='utf-8') as f:
        vereadores = list(csv.DictReader(f))

    print(f"Total de vereadores a consultar: {len(vereadores)}", flush=True)

    todas_proposicoes = []
    totais_por_autor = {}

    for idx, v in enumerate(vereadores):
        id_sicam = v['id_sicam'].strip()
        nome = v['nome_parlamentar'].strip()
        if not id_sicam or not id_sicam.isdigit():
            print(f"Pulando autor sem id numérico válido: {v}", flush=True)
            continue

        itens = buscar_proposicoes_autor(id_sicam, nome)
        count = len(itens) if isinstance(itens, list) else 0
        totais_por_autor[f"{nome} (id {id_sicam})"] = count
        print(f"  [{idx+1}/{len(vereadores)}] Autor {nome} (id {id_sicam}): {count} proposições.", flush=True)

        if isinstance(itens, list):
            for it in itens:
                proc_str = str(it.get('processo', '')).strip()
                tipo_str = str(it.get('tipo', '')).strip()
                numero_str = str(it.get('numero', '')).strip()
                
                # Ano
                ano_str = ''
                if '/' in proc_str:
                    ano_str = proc_str.split('/')[1].strip()
                elif it.get('data_entrada'):
                    ano_str = str(it.get('data_entrada'))[:4]

                data_formatada = formatar_data(it.get('data_entrada', ''))
                ementa_str = str(it.get('ementa', '')).strip()
                autores_str = str(it.get('requerente', '')).strip()
                situacao_str = str(it.get('situacao', '')).strip() if it.get('situacao') else ''

                url_processo = proc_str.replace('/', '_')
                url_doc = f"https://marica.sicam.app/processos/?DocumentoPDF/Processo/{url_processo}/web" if proc_str else ''
                url_det = f"https://marica.sicam.app/areapublica/processo/{url_processo.replace('_', '-')}" if proc_str else ''

                todas_proposicoes.append({
                    'processo': proc_str,
                    'tipo': tipo_str,
                    'numero': numero_str,
                    'ano': ano_str,
                    'data': data_formatada,
                    'ementa': ementa_str,
                    'autores': autores_str,
                    'situacao': situacao_str,
                    'url_documento': url_doc,
                    'url_detalhes': url_det,
                    'autor_filtrado_id': id_sicam
                })

    # Save to dados/brutos/proposicoes.csv
    csv_path = os.path.join(OUTPUT_DIR, 'proposicoes.csv')
    fieldnames = [
        'processo', 'tipo', 'numero', 'ano', 'data', 'ementa',
        'autores', 'situacao', 'url_documento', 'url_detalhes', 'autor_filtrado_id'
    ]

    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(todas_proposicoes)

    print(f"\nSalvo {len(todas_proposicoes)} linhas em {csv_path}", flush=True)

    # Conference check: Netuno
    netuno_count = totais_por_autor.get('Netuno (id 15)', 0)
    print(f"\nCONFERÊNCIA NETUNO (id 15): {netuno_count} proposições (esperado: ~471).", flush=True)

    # Group by tipo
    tipos_count = {}
    for p in todas_proposicoes:
        t = p['tipo']
        tipos_count[t] = tipos_count.get(t, 0) + 1

    print("\nProposições por tipo:", flush=True)
    for t, c in sorted(tipos_count.items(), key=lambda x: x[1], reverse=True):
        print(f"  {t}: {c}", flush=True)

    return totais_por_autor, tipos_count

if __name__ == '__main__':
    processar_todas_proposicoes()

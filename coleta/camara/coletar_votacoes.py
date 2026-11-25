import os
import sys
import json
import csv
import re
import time
import urllib.request
from bs4 import BeautifulSoup

# Ensure stdout flushes immediately
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
HEADERS = {'User-Agent': USER_AGENT}

def get_html(url, cache_filename):
    cache_path = os.path.join(CACHE_DIR, cache_filename)
    if os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    print(f"Fetching {url} -> {cache_filename}", flush=True)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        content = resp.read().decode('utf-8', errors='ignore')
    
    with open(cache_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    time.sleep(2.5) # rate limit 1 req / 2s
    return content

def extrair_tipo_e_numero(titulo):
    if not titulo:
        return '', ''
    m = re.match(r'^(.*?)\s+(?:nr\.|nº|n°|n\.)\s*(\d+.*)$', titulo.strip(), re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return titulo.strip(), ''

def extrair_fase_e_resultado(res_str, vot_str):
    fase = ''
    resultado = res_str.strip() if res_str else ''
    if ' - ' in resultado:
        partes = resultado.split(' - ')
        resultado_limpo = partes[0].strip()
        fase = partes[1].strip()
    else:
        resultado_limpo = resultado
        fase = vot_str.strip() if vot_str else ''
    return fase, resultado_limpo

def parse_votacao_html(html, id_sessao):
    presentes = []
    m_pres = re.search(r'const presentes\s*=\s*(\[.*?\]);', html, re.DOTALL)
    if m_pres:
        try:
            presentes = json.loads(m_pres.group(1))
        except Exception as e:
            print(f"Error parsing presentes JSON in sessao {id_sessao}: {e}", flush=True)

    processos = []
    m_proc = re.search(r'const processos\s*=\s*(\[.*?\]);\s*\n', html, re.DOTALL)
    if m_proc:
        try:
            processos = json.loads(m_proc.group(1))
        except Exception as e:
            raw_proc = m_proc.group(1).strip()
            try:
                cleaned_proc = re.sub(r',\s*([\]}])', r'\1', raw_proc)
                processos = json.loads(cleaned_proc)
            except Exception as e2:
                print(f"Error parsing processos JSON in sessao {id_sessao}: {e2}", flush=True)

    return presentes, processos

def processar_todas_votacoes():
    sessoes_csv_path = os.path.join(OUTPUT_DIR, 'sessoes.csv')
    if not os.path.exists(sessoes_csv_path):
        print(f"Erro: {sessoes_csv_path} não encontrado.", flush=True)
        return

    with open(sessoes_csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        sessoes = list(reader)

    print(f"Total de sessões lidas: {len(sessoes)}", flush=True)
    sessoes_com_votacao = [s for s in sessoes if s['tem_votacao'] == 'sim']
    print(f"Sessões com votação a processar: {len(sessoes_com_votacao)}", flush=True)

    # Sessões recentes podem ter ata/votação incompleta: refaz o cache das últimas 5 datas
    from datetime import datetime as _dt
    def _d(x):
        try: return _dt.strptime(x['data'], '%d/%m/%Y')
        except Exception: return _dt.min
    for _s in sorted(sessoes_com_votacao, key=_d)[-5:]:
        for _n in (f"votacao_{_s['id_sessao']}.html",):
            _p = os.path.join(CACHE_DIR, _n)
            if os.path.exists(_p): os.remove(_p)

    todas_presencas = []
    todas_votacoes = []
    todos_votos_nominais = []
    novos_apelidos = []

    # Read existing apelidos to enrich
    apelidos_map = {}
    apelidos_csv_path = os.path.join(OUTPUT_DIR, 'apelidos.csv')
    if os.path.exists(apelidos_csv_path):
        with open(apelidos_csv_path, 'r', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                apelidos_map[row['nome_como_aparece']] = row['id_sicam']

    for idx, s in enumerate(sessoes_com_votacao):
        id_sessao = s['id_sessao']
        data_sessao = s['data']
        url_fonte = s['url_votacao']
        cache_file = f"votacao_{id_sessao}.html"
        
        if (idx + 1) % 10 == 0 or idx == 0 or idx == len(sessoes_com_votacao) - 1:
            print(f"[{idx+1}/{len(sessoes_com_votacao)}] Processando Sessão {id_sessao} ({data_sessao})...", flush=True)

        try:
            html = get_html(url_fonte, cache_file)
            presentes, processos = parse_votacao_html(html, id_sessao)
        except Exception as err:
            print(f"Erro ao buscar sessão {id_sessao}: {err}", flush=True)
            presentes, processos = [], []

        # 1. Presenças
        if presentes:
            for p in presentes:
                nome_p = p.strip()
                todas_presencas.append({
                    'id_sessao': id_sessao,
                    'data': data_sessao,
                    'nome_como_aparece': nome_p,
                    'presente': 'sim',
                    'url_fonte': url_fonte
                })
                id_s = apelidos_map.get(nome_p, '')
                novos_apelidos.append({
                    'id_sicam': id_s,
                    'nome_como_aparece': nome_p,
                    'onde_aparece': 'votacao_lista_presenca'
                })
        else:
            todas_presencas.append({
                'id_sessao': id_sessao,
                'data': data_sessao,
                'nome_como_aparece': 'sem registro',
                'presente': '',
                'url_fonte': url_fonte
            })

        # 2. Votações
        for proc in processos:
            id_item = proc.get('id', '')
            titulo = proc.get('titulo', '')
            tipo_materia, numero_materia = extrair_tipo_e_numero(titulo)
            proc_numero = proc.get('proc', '')
            fase, resultado = extrair_fase_e_resultado(proc.get('resultado', ''), proc.get('votacao', ''))

            todas_votacoes.append({
                'id_sessao': id_sessao,
                'data': data_sessao,
                'id_item': id_item,
                'tipo_materia': tipo_materia,
                'numero_materia': numero_materia,
                'processo': proc_numero,
                'fase': fase,
                'resultado': resultado,
                'url_fonte': url_fonte
            })

            # 3. Votos Nominais
            votos_dict = proc.get('votos', {})
            grupos_voto = [
                ('Sim', votos_dict.get('favoraveis', [])),
                ('Não', votos_dict.get('contrarios', [])),
                ('Abstenção', votos_dict.get('abstencoes', []))
            ]

            for tipo_voto, lista_votos in grupos_voto:
                for v in lista_votos:
                    if isinstance(v, list) and len(v) >= 2:
                        nome_civil, apelido = v[0].strip(), v[1].strip()
                        nome_como_aparece = apelido if apelido else nome_civil
                    elif isinstance(v, str):
                        nome_civil = v.strip()
                        apelido = ''
                        nome_como_aparece = nome_civil
                    else:
                        continue

                    todos_votos_nominais.append({
                        'id_sessao': id_sessao,
                        'processo': proc_numero,
                        'nome_como_aparece': nome_como_aparece,
                        'voto': tipo_voto,
                        'url_fonte': url_fonte
                    })

                    id_s = apelidos_map.get(nome_como_aparece) or apelidos_map.get(nome_civil, '')
                    if apelido and apelido != nome_civil:
                        novos_apelidos.append({
                            'id_sicam': id_s,
                            'nome_como_aparece': apelido,
                            'onde_aparece': 'votacao_voto_nominal_apelido'
                        })
                    if nome_civil:
                        novos_apelidos.append({
                            'id_sicam': id_s,
                            'nome_como_aparece': nome_civil,
                            'onde_aparece': 'votacao_voto_nominal_nome_civil'
                        })

    # Save presencas.csv
    presencas_csv_path = os.path.join(OUTPUT_DIR, 'presencas.csv')
    with open(presencas_csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['id_sessao', 'data', 'nome_como_aparece', 'presente', 'url_fonte'])
        writer.writeheader()
        writer.writerows(todas_presencas)
    print(f"\nSalvo {len(todas_presencas)} presenças em {presencas_csv_path}", flush=True)

    # Save votacoes.csv
    votacoes_csv_path = os.path.join(OUTPUT_DIR, 'votacoes.csv')
    with open(votacoes_csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'id_sessao', 'data', 'id_item', 'tipo_materia', 'numero_materia',
            'processo', 'fase', 'resultado', 'url_fonte'
        ])
        writer.writeheader()
        writer.writerows(todas_votacoes)
    print(f"Salvo {len(todas_votacoes)} matérias votadas em {votacoes_csv_path}", flush=True)

    # Save votos_nominais.csv
    votos_csv_path = os.path.join(OUTPUT_DIR, 'votos_nominais.csv')
    with open(votos_csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['id_sessao', 'processo', 'nome_como_aparece', 'voto', 'url_fonte'])
        writer.writeheader()
        writer.writerows(todos_votos_nominais)
    print(f"Salvo {len(todos_votos_nominais)} votos nominais em {votos_csv_path}", flush=True)

    # Update apelidos.csv
    existing_apelidos = []
    if os.path.exists(apelidos_csv_path):
        with open(apelidos_csv_path, 'r', encoding='utf-8') as f:
            existing_apelidos = list(csv.DictReader(f))

    all_apelidos = existing_apelidos + novos_apelidos
    seen = set()
    unique_apelidos = []
    for a in all_apelidos:
        key = (a['id_sicam'], a['nome_como_aparece'], a['onde_aparece'])
        if key not in seen:
            seen.add(key)
            unique_apelidos.append(a)

    with open(apelidos_csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['id_sicam', 'nome_como_aparece', 'onde_aparece'])
        writer.writeheader()
        writer.writerows(unique_apelidos)
    print(f"Atualizado {apelidos_csv_path} com {len(unique_apelidos)} apelidos únicos.", flush=True)

    # Check 502 conference
    s502_pres = [p for p in todas_presencas if str(p['id_sessao']) == '502']
    s502_vot = [v for v in todas_votacoes if str(v['id_sessao']) == '502']
    print(f"\nCONFERÊNCIA SESSÃO 502: Presentes={len(s502_pres)} (esperado: 19), Processos votados={len(s502_vot)} (esperado: 13).", flush=True)

if __name__ == '__main__':
    processar_todas_votacoes()

import json
import urllib.request
import urllib.parse
import os
import time
import hashlib
import sys

# Diretórios
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BASE_DIR, 'dados', 'cache', 'nominatim')
CONSOLIDADO_DIR = os.path.join(BASE_DIR, 'dados', 'consolidado')
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(CONSOLIDADO_DIR, exist_ok=True)

USER_AGENT = 'LupaMarica/1.0 (coleta publica; contato: https://lupamarica.com)'
HEADERS = {
    'User-Agent': USER_AGENT,
    'Accept': 'application/json'
}

# Bounding box de Maricá conforme briefing:
# -23.2 < lat < -22.7 e -43.1 < lng < -42.5
LAT_MIN = -23.2
LAT_MAX = -22.7
LNG_MIN = -43.1
LNG_MAX = -42.5

def in_marica(lat, lng):
    try:
        lat = float(lat)
        lng = float(lng)
        return (LAT_MIN < lat < LAT_MAX) and (LNG_MIN < lng < LNG_MAX)
    except:
        return False

def get_cache_filename(query):
    # Hash SHA-256 da query para nome de arquivo seguro
    h = hashlib.sha256(query.strip().encode('utf-8')).hexdigest()
    return os.path.join(CACHE_DIR, f"{h}.json")

def query_nominatim(query):
    cache_file = get_cache_filename(query)
    if os.path.exists(cache_file):
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f), True

    # Se não estiver em cache, faz a requisição respeitando 1s de intervalo
    url = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode({
        'q': query,
        'format': 'json',
        'addressdetails': 1,
        'limit': 5
    })
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            if status in (403, 429):
                print(f"ALERTA: Bloqueio do Nominatim detectado (HTTP {status})!")
                sys.exit(1)
            raw = resp.read().decode('utf-8')
            data = json.loads(raw)
            # Salvar cache intacto
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            # Respeitar rate limit
            time.sleep(1.15)
            return data, False
    except urllib.error.HTTPError as e:
        if e.code in (403, 429):
            print(f"ALERTA CRÍTICO: Bloqueio do Nominatim (HTTP {e.code})!")
            sys.exit(1)
        print(f"Erro HTTP {e.code} ao buscar '{query}': {e}")
        return None, False
    except Exception as e:
        print(f"Erro ao buscar '{query}': {e}")
        return None, False

def main():
    input_path = os.path.join(CONSOLIDADO_DIR, 'problemas_que_nao_somem.json')
    if not os.path.exists(input_path):
        print(f"Arquivo não encontrado: {input_path}")
        sys.exit(1)

    with open(input_path, 'r', encoding='utf-8') as f:
        problemas = json.load(f)

    print(f"Carregados {len(problemas)} problemas de {input_path}")

    # Registro de resultados
    resultados = []
    descartados_fora_marica = []
    
    # Para estatísticas
    stats = {
        'rua': 0,
        'bairro': 0,
        'sem_coordenada': 0
    }

    # Pré-buscar macros únicos para cache eficiente
    macros = set(it['macro'] for it in problemas if it.get('macro'))
    print(f"Total de macros distintos para possível fallback: {len(macros)}")

    # Reaproveita o que já foi geocodificado (mesma rua + mesmo bairro): só consulta o que é novo.
    reuso = {}
    mapa_antigo = os.path.join(CONSOLIDADO_DIR, 'problemas_mapa.json')
    if os.path.exists(mapa_antigo):
        for x in json.load(open(mapa_antigo, encoding='utf-8')):
            if x.get('erro_rede'):
                continue
            reuso[(x['rua'], x.get('macro'))] = {k: x.get(k) for k in ('lat', 'lng', 'precisao', 'fonte', 'consulta')}
    novos = 0

    for idx, item in enumerate(problemas, 1):
        rua = item['rua']
        macro = item.get('macro')

        if (rua, macro) in reuso:
            ponto = dict(item)
            ponto.update(reuso[(rua, macro)])
            resultados.append(ponto)
            stats[ponto['precisao']] += 1
            continue
        novos += 1

        # Montar consulta conforme briefing:
        # "<rua>, <macro>, Maricá, Rio de Janeiro, Brasil"; se macro for nulo, "<rua>, Maricá, Rio de Janeiro, Brasil"
        if macro:
            query_rua = f"{rua}, {macro}, Maricá, Rio de Janeiro, Brasil"
        else:
            query_rua = f"{rua}, Maricá, Rio de Janeiro, Brasil"

        data_rua, from_cache = query_nominatim(query_rua)
        if data_rua is None:  # falha de rede: não grava como definitivo; será tentado de novo na próxima execução
            ponto = dict(item, lat=None, lng=None, precisao='sem_coordenada', fonte='OpenStreetMap/Nominatim', consulta=query_rua, erro_rede=True)
            resultados.append(ponto); stats['sem_coordenada'] += 1
            print(f"[{idx:03d}/{len(problemas)}] ERRO DE REDE (será retentado): {rua} ({macro})")
            continue
        cache_str = "(cache)" if from_cache else "(rede)"
        
        # Verificar se achou rua (tipo highway dentro de Maricá)
        coord_rua = None
        for res in data_rua:
            lat = float(res.get('lat', 0))
            lng = float(res.get('lon', 0))
            if in_marica(lat, lng):
                if res.get('class') == 'highway':
                    coord_rua = (lat, lng, query_rua, res)
                    break
            else:
                descartados_fora_marica.append({
                    'item_idx': idx,
                    'rua': rua,
                    'macro': macro,
                    'consulta': query_rua,
                    'lat': lat,
                    'lng': lng,
                    'display_name': res.get('display_name', '')
                })

        if coord_rua:
            # Encontrou a rua
            lat, lng, consulta_usada, res = coord_rua
            ponto = dict(item)
            ponto['lat'] = round(lat, 6)
            ponto['lng'] = round(lng, 6)
            ponto['precisao'] = 'rua'
            ponto['fonte'] = 'OpenStreetMap/Nominatim'
            ponto['consulta'] = consulta_usada
            resultados.append(ponto)
            stats['rua'] += 1
            print(f"[{idx:03d}/{len(problemas)}] RUA: {rua} ({macro}) -> ({lat:.4f}, {lng:.4f}) {cache_str}")
        else:
            # Não achou a rua. Tentar fallback de bairro/macro se macro existir
            coord_bairro = None
            if macro:
                query_bairro = f"{macro}, Maricá, Rio de Janeiro, Brasil"
                data_bairro, b_cache = query_nominatim(query_bairro)
                for res in data_bairro:
                    lat = float(res.get('lat', 0))
                    lng = float(res.get('lon', 0))
                    if in_marica(lat, lng):
                        coord_bairro = (lat, lng, query_bairro, res)
                        break
                    else:
                        descartados_fora_marica.append({
                            'item_idx': idx,
                            'rua': rua,
                            'macro': macro,
                            'consulta': query_bairro,
                            'lat': lat,
                            'lng': lng,
                            'display_name': res.get('display_name', '')
                        })

            if coord_bairro:
                # Encontrou o bairro
                lat, lng, consulta_usada, res = coord_bairro
                ponto = dict(item)
                ponto['lat'] = round(lat, 6)
                ponto['lng'] = round(lng, 6)
                ponto['precisao'] = 'bairro'
                ponto['fonte'] = 'OpenStreetMap/Nominatim'
                ponto['consulta'] = consulta_usada
                resultados.append(ponto)
                stats['bairro'] += 1
                print(f"[{idx:03d}/{len(problemas)}] BAIRRO: {rua} -> {macro} ({lat:.4f}, {lng:.4f}) {cache_str}")
            else:
                # sem coordenada confiável
                ponto = dict(item)
                ponto['lat'] = None
                ponto['lng'] = None
                ponto['precisao'] = 'sem_coordenada'
                ponto['fonte'] = 'OpenStreetMap/Nominatim'
                ponto['consulta'] = query_rua
                resultados.append(ponto)
                stats['sem_coordenada'] += 1
                print(f"[{idx:03d}/{len(problemas)}] SEM_COORDENADA: {rua} ({macro}) {cache_str}")

    # Salvar saída JSON
    output_path = os.path.join(CONSOLIDADO_DIR, 'problemas_mapa.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    print(f"\nSalvo: {output_path} com {len(resultados)} pontos")
    print(f"Estatísticas: {stats}")
    print(f"Consultas novas ao Nominatim: {novos}")

if __name__ == '__main__':
    main()

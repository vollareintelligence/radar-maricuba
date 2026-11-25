"""Coletor automático diário da Lupa Maricá (manhã e tarde).

Executa coleta resiliente das fontes oficiais e notícias:
1. Coleta notícias recentes de Maricá e promessas (coleta/buscar_noticias.py).
2. Verifica disponibilidade das fontes oficiais (Prefeitura, Câmara/SICAM, Eloweb)
   (a coleta dos CSVs oficiais NÃO é feita aqui; a defasagem é sinalizada por
   coleta/alerta_defasagem.py).
3. Grava dados/consolidado/status_automacao.json com o horário de Brasília (UTC-3).

Regra de ouro: se qualquer portal público estiver temporariamente fora do ar ou mudar
de formato, o coletor registra o aviso e preserva intactos os dados brutos válidos.
"""
import json
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONSOLIDADO = ROOT / 'dados' / 'consolidado'
CONSOLIDADO.mkdir(parents=True, exist_ok=True)

BRT = timezone(timedelta(hours=-3))
USER_AGENT = 'Mozilla/5.0 (compatible; LupaMaricaBot/1.0; +https://lupamarica.com/)'

FONTES = {
    # O catálogo de Dados Abertos mudou de /dados-abertos (404 desde que o portal foi reorganizado)
    # para o endereço abaixo. As demais são as telas do e-Cidade citadas como fonte em site/index.html.
    'prefeitura_dados_abertos': 'https://transparencia.marica.rj.gov.br/governo-digital/dados-abertos/links-e-arquivos',
    'prefeitura_despesas': 'https://transparencia.marica.rj.gov.br/e-cidade/despesas/padrao',
    'prefeitura_servidores': 'https://transparencia.marica.rj.gov.br/e-cidade/servidores',
    'prefeitura_sancoes': 'https://transparencia.marica.rj.gov.br/sancoes-administrativas',
    'camara_sicam': 'https://marica.sicam.app/areapublica',
    'camara_site': 'https://marica.rj.leg.br',
    'camara_eloweb': 'https://cmmarica.eloweb.net/portaltransparencia/1/servidores',
}


def checar_fonte(url: str, timeout: int = 15) -> dict:
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {'ok': True, 'status': int(resp.status)}
    except urllib.error.HTTPError as e:
        return {'ok': False, 'status': int(e.code), 'erro': f'HTTP {e.code}'}
    except Exception as e:
        return {'ok': False, 'status': 0, 'erro': str(e)[:120]}


def rodar_noticias() -> dict:
    script = ROOT / 'coleta' / 'buscar_noticias.py'
    try:
        res = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=180,
        )
        return {
            'ok': res.returncode == 0,
            'codigo': res.returncode,
            'resumo': (res.stdout.strip().splitlines()[-1] if res.stdout.strip() else ''),
            'erro': (res.stderr.strip()[:200] if res.returncode != 0 else ''),
        }
    except Exception as e:
        return {'ok': False, 'codigo': -1, 'resumo': '', 'erro': str(e)[:200]}


def main() -> int:
    agora = datetime.now(BRT)
    print(f'[Lupa Maricá Bot] Iniciando verificação em {agora.strftime("%Y-%m-%d %H:%M BRT")}')

    noticias = rodar_noticias()
    print('[Lupa Maricá Bot] Notícias:', noticias)

    fontes_status = {}
    for nome, url in FONTES.items():
        st = checar_fonte(url)
        fontes_status[nome] = {'url': url, **st}
        print(f'[Lupa Maricá Bot] Fonte {nome}: {st}')

    status = {
        'verificadoEm': agora.strftime('%Y-%m-%d %H:%M BRT'),
        'verificadoData': agora.strftime('%Y-%m-%d'),
        'noticias': noticias,
        'fontes': fontes_status,
    }
    out_file = CONSOLIDADO / 'status_automacao.json'
    out_file.write_text(json.dumps(status, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'[Lupa Maricá Bot] Status gravado em {out_file.relative_to(ROOT)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

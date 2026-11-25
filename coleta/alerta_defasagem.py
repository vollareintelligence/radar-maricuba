"""Sinaliza dados oficiais defasados ou fontes fora do ar (não bloqueia a publicação).

Lê site/dados.js (coletaAte) e dados/consolidado/status_automacao.json.
Regra: avisa se os dados oficiais têm mais de LIMITE_DIAS dias ou se alguma fonte falhou.
Saída: mensagem em stdout, ::warning:: do GitHub Actions e, em $GITHUB_OUTPUT,
`alerta=true|false` e o arquivo alerta.md (corpo da Issue de aviso).
"""
import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIMITE_DIAS = 7
BRT = timezone(timedelta(hours=-3))


def main() -> int:
    hoje = datetime.now(BRT).date()
    m = re.search(r'"coletaAte":"(\d{4}-\d{2}-\d{2})"', (ROOT / 'site' / 'dados.js').read_text(encoding='utf-8'))
    problemas = []
    if m:
        ate = date.fromisoformat(m.group(1))
        dias = (hoje - ate).days
        print(f'Dados oficiais até {ate} ({dias} dia(s) de defasagem)')
        if dias > LIMITE_DIAS:
            problemas.append(f'Dados oficiais da Câmara/Prefeitura parados em {ate.strftime("%d/%m/%Y")} ({dias} dias). A coleta dos CSVs é manual: rodar a coleta e os consolidar*.py.')
    else:
        problemas.append('Não foi possível ler coletaAte em site/dados.js.')

    st_file = ROOT / 'dados' / 'consolidado' / 'status_automacao.json'
    if st_file.exists():
        st = json.loads(st_file.read_text(encoding='utf-8'))
        for nome, f in (st.get('fontes') or {}).items():
            if not f.get('ok'):
                problemas.append(f'Fonte fora do ar ou mudou de endereço: {nome} ({f.get("url")}) -> {f.get("erro", f.get("status"))}')
        if not (st.get('noticias') or {}).get('ok', True):
            problemas.append('Coleta de notícias falhou.')

    for p in problemas:
        print(f'::warning::{p}')
    out = os.environ.get('GITHUB_OUTPUT')
    if out:
        with open(out, 'a', encoding='utf-8') as fh:
            fh.write(f'alerta={"true" if problemas else "false"}\n')
    if problemas:
        (ROOT / 'alerta.md').write_text(
            f'Verificação automática de {hoje.strftime("%d/%m/%Y")}:\n\n' + '\n'.join(f'- {p}' for p in problemas) + '\n',
            encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main())

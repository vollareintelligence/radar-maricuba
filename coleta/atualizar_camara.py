"""Atualiza os dados da Câmara (SICAM) de ponta a ponta, com proteção contra coleta ruim.

Roda NO PC (o portal é acessado de lá; ver README). Passos:
  1. coleta sessões, votações/presenças e proposições (1 req a cada 2,5 s, cache com validade)
  2. recusa a coleta se algum CSV encolheu mais de 2% (portal fora do ar / mudou de formato) e restaura o anterior
  3. consolida, recalcula o placar, gera site/dados.js e roda a porta de qualidade
Uso:  py coleta/atualizar_camara.py
Não faz commit nem push: confira o resultado e publique.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRUTOS = ROOT / 'dados' / 'brutos'
CONSOLIDADO = ROOT / 'dados' / 'consolidado'
ALVOS = ['sessoes.csv', 'presencas.csv', 'votacoes.csv', 'votos_nominais.csv', 'proposicoes.csv', 'apelidos.csv']
COLETA = ['camara/coletar_sessoes.py', 'camara/coletar_votacoes.py', 'camara/coletar_proposicoes.py']
POS = ['consolidar.py', 'geocodificar_problemas.py', 'placar.py', 'build_dados.py', 'qualidade.py']


def linhas(p: Path) -> int:
    return sum(1 for _ in p.open(encoding='utf-8')) - 1 if p.exists() else 0


def rodar(script: str, isolado=False) -> int:
    cmd = [sys.executable] + (['-I'] if isolado else []) + [str(ROOT / 'coleta' / script)]
    print(f'\n>>> {script}', flush=True)
    return subprocess.run(cmd, cwd=str(ROOT)).returncode


def main() -> int:
    backup = Path(tempfile.mkdtemp(prefix='lupa_bkp_'))
    antes = {}
    for n in ALVOS:
        if (BRUTOS / n).exists():
            shutil.copy2(BRUTOS / n, backup / n)
            antes[n] = linhas(BRUTOS / n)

    shutil.copytree(CONSOLIDADO, backup / 'consolidado')

    def restaurar():
        for n in antes:
            shutil.copy2(backup / n, BRUTOS / n)
        shutil.rmtree(CONSOLIDADO)
        shutil.copytree(backup / 'consolidado', CONSOLIDADO)
        print('Dados anteriores restaurados.')

    for s in COLETA:
        if rodar(s) != 0:
            print(f'ERRO em {s}.'); restaurar(); return 1

    for n, a in antes.items():
        d = linhas(BRUTOS / n)
        print(f'{n}: {a} -> {d} linhas')
        if a and d < a * 0.98:
            print(f'RECUSADO: {n} encolheu mais de 2% ({a} -> {d}). Portal fora do ar ou mudou de formato.')
            restaurar(); return 1

    for s in POS:
        if rodar(s, isolado=s in ('build_dados.py', 'qualidade.py')) != 0:
            print(f'ERRO em {s}.'); restaurar(); return 1

    print('\nOK. Confira com `git diff --stat` e publique (commit + push).')
    return 0


if __name__ == '__main__':
    sys.exit(main())

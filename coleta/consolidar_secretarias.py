"""Secretarias somadas (2026), a partir da despesa por órgão do e-cidade (Prefeitura de Maricá).
Só 2026: a soma por órgão bate com o total da instituição (diferença < R$ 2.200).
2025 NÃO é usado: a visão por órgão difere do total da instituição em quase todas as instituições (causa não confirmada)."""
import json, re
from pathlib import Path
import pandas as pd

R = Path(__file__).resolve().parent.parent
B = R / 'dados' / 'brutos' / 'prefeitura'
OUT = R / 'dados' / 'consolidado'

d = pd.read_csv(B / 'despesas_por_orgao.csv')
d = d[d.ano == 2026].copy()
# secretarias = órgãos da Prefeitura cujo nome é de secretaria, mais as secretarias que operam por fundo
FUNDOS_SEC = ('FUNDO MUNICIPAL DE SAUDE', 'FUNDO MUNICIPAL DE ASSISTENCIA SOCIAL DE MARICA', 'FUNDO MUNICIPAL DE PROTEÇÃO E CONSERVAÇÃO AMBIENTAL')
pref = d.instituicao.str.upper().str.startswith('PREFEITURA')
is_sec = d.orgao.str.upper().str.match(r'^(SECRETARIA|SEC ESP)')
sel = d[(pref & is_sec) | d.instituicao.str.upper().isin(FUNDOS_SEC)].copy()
sel['chave'] = sel.orgao.str.upper().str.strip()
g = sel.groupby('chave').agg(nome=('orgao', 'first'), pago=('pago', 'sum'), empenhado=('empenhado', 'sum'), n=('orgao', 'size')).reset_index(drop=True)
g = g.sort_values('pago', ascending=False)
def bonito(s):
    s = s.title()
    for a, b in ((' De ', ' de '), (' Da ', ' da '), (' Do ', ' do '), (' Das ', ' das '), (' E ', ' e '), (' Dos ', ' dos '), (' Em ', ' em ')):
        s = s.replace(a, b)
    return s
itens = [dict(nome=bonito(r.nome), pago=round(r.pago, 2), empenhado=round(r.empenhado, 2)) for r in g.itertuples()]
conf = pd.read_csv(B / 'conferencia_m2c.csv')
c26 = conf[conf.ano == 2026]
out = dict(
    ano=2026, dataBase='2026-11-14',
    totalPago=round(float(g.pago.sum()), 2), totalEmpenhado=round(float(g.empenhado.sum()), 2), n=len(itens),
    itens=itens,
    conferencia=dict(maiorDiferencia=round(float(c26.diferenca.abs().max()), 2), instituicoes=int(len(c26))),
    fonte='https://transparencia.marica.rj.gov.br/e-cidade/despesas/padrao',
    regra='Órgãos da Prefeitura com nome de secretaria, mais Saúde, Assistência Social e Meio Ambiente, que operam por fundo. Fora: Encargos Financeiros, Procuradoria, Gabinete, Ouvidoria, assessorias, Câmara e Fundo Soberano.',
)
json.dump(out, open(OUT / 'secretarias.json', 'w'), ensure_ascii=False, indent=1)
print(len(itens), out['totalPago'], itens[:3])

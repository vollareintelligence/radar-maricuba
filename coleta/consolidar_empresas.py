"""Ficha por empresa: maiores credores privados (2025+2026) cruzados com contratos e sanções, por CNPJ.
Regras uniformes, sem juízo de valor. Uso: python3 -I coleta/consolidar_empresas.py -> dados/consolidado/empresas.json"""
import json, re, sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
ROOT = Path(__file__).resolve().parent.parent
P = ROOT/'dados'/'brutos'/'prefeitura'; CA = ROOT/'dados'/'cache'/'prefeitura'
import importlib.util
def digits(s): return re.sub(r'\D', '', str(s)) if pd.notna(s) else ''
ENTE = r'PREFEITURA MUNICIPAL|CAMARA MUNICIPAL|FUNDO |SOMAR|COMPANHIA (DE |DESENV|MARICA)|ISSM|INSTITUTO DE SEG|INSS|INSTITUTO NACIONAL SEGURO|PIS.?PASEP|RECEITA FEDERAL|FGTS|EMPRESA PUBLICA DE TRANSPORTE|FUNDACAO ESTATAL|INST MUN DE INFORMACAO|MARICA GLOBAL INVEST|INSTITUTO DE CIENCIA'
TIPOS = [('Gestão, parceria ou cessão', r'CONTRATO DE GESTÃO|ORGANIZAÇÃO SOCIAL|CESSÃO|CONVÊNIO|PARCERIA|TERMO DE FOMENTO|TERMO DE COLABORA|TERMO DE COOPERA'),
 ('Shows e eventos', r'SHOW|ARTÍSTIC|EVENTO|FESTIVAL|APRESENTA|BANDA|CANTOR'),
 ('Obras e engenharia', r'OBRA|ENGENHARIA|CONSTRU|PAVIMENT|REFORMA|DRENAGEM|URBANIZA|CONSERVAÇÃO|MANUTENÇÃO'),
 ('Saúde', r'SAÚDE|HOSPIT|MÉDIC|CLÍNIC|EXAME|LABORAT|MEDICAMENT'),
 ('Limpeza e resíduos', r'LIMPEZA|RESÍDUO|COLETA|VARRI'),
 ('Transporte e locação', r'TRANSPORTE|LOCAÇÃO|VEÍCULO|ÔNIBUS|FROTA'),
 ('Tecnologia', r'SOFTWARE|SISTEMA|INFORMÁTICA|TECNOLOGIA|APLICATIVO'),
 ('Alimentação', r'ALIMENT|MERENDA|REFEI|GÊNEROS'),
 ('Educação', r'EDUCA|ENSINO|ESCOLA|FACULDADE|CURSO'),
 ('Publicidade', r'PUBLICIDADE|PROPAGANDA|COMUNICAÇÃO')]
def tipo(o):
    o = str(o).upper()
    for k, p in TIPOS:
        if re.search(p, o): return k
    return 'Outros'
def limpa(o): return re.sub(r'\s+', ' ', str(o).replace('\\N', ' ')).strip()

c = pd.read_csv(P/'contratos.csv', dtype=str)
c['v'] = pd.to_numeric(c.valor_atualizado, errors='coerce').fillna(0)
c['doc'] = c.cpf_cnpj_como_exibido.map(digits); c['tipo'] = c.objeto.map(tipo)
s = pd.read_csv(P/'sancoes.csv', dtype=str); s['doc'] = s.cpf_cnpj_como_exibido.map(digits)
cr = pd.concat([pd.read_csv(CA/f'despesas_credores_{a}.csv', dtype=str).assign(ano=a) for a in (2025, 2026)])
cr['doc'] = cr.Credor.str.split('<BR>').str[1].map(digits); cr['nome'] = cr.Credor.str.split('<BR>').str[0]
for col in ['Empenhado', 'Pago']: cr[col] = pd.to_numeric(cr[col], errors='coerce').fillna(0)
cr = cr[cr.doc != '']
cr = cr[~cr.nome.str.upper().str.contains(ENTE, regex=True)]
g = cr.pivot_table(index='doc', columns='ano', values='Pago', aggfunc='sum', fill_value=0)
g.columns = [f'p{a}' for a in g.columns]
g['nome'] = cr.groupby('doc').nome.first(); g['emp'] = cr.groupby('doc').Empenhado.sum()
g['pago'] = g.p2025 + g.p2026
top = g.nlargest(100, 'pago').reset_index()
out = []
for r in top.itertuples():
    cc = c[c.doc == r.doc].sort_values('v', ascending=False)
    ss = s[s.doc == r.doc]
    out.append(dict(nome=r.nome, cnpj=f'{r.doc[:2]}.{r.doc[2:5]}.{r.doc[5:8]}/{r.doc[8:12]}-{r.doc[12:]}' if len(r.doc) == 14 else r.doc,
        pago25=round(r.p2025/1e6, 2), pago26=round(r.p2026/1e6, 2), pago=round(r.pago/1e6, 2),
        nContratos=int(len(cc)), contratado=round(cc.v.sum()/1e6, 2), tipos=sorted(set(cc.tipo)),
        contratos=[dict(id=f'{x.numero}/{x.ano}', obj=limpa(x.objeto)[:240], tipo=x.tipo, ini=x.vigencia_inicio, fim=x.vigencia_fim,
                        v=round(x.v/1e6, 2), proc=x.processo_licitatorio, url=x.url_fonte) for x in cc.head(6).itertuples()],
        sancoes=[dict(tipo=x.tipo_de_sancao, status=str(x.status) if pd.notna(x.status) else '', fim=str(x.fim_sancao) if pd.notna(x.fim_sancao) else '') for x in ss.itertuples()]))
tot_priv = g.pago.sum()
cobertura = dict(pagoPrivado=round(tot_priv/1e9, 2), comContrato=round(g[g.index.isin(set(c.doc))].pago.sum()/1e9, 2),
                 contratosN=int(len(c)), contratadoBi=round(c.v.sum()/1e9, 2), top100Pct=round(top.pago.sum()/tot_priv*100, 1),
                 top100SemContrato=int(sum(1 for e in out if e['nContratos'] == 0)), top100ComSancao=int(sum(1 for e in out if e['sancoes'])))
(ROOT/'dados'/'consolidado'/'empresas.json').write_text(json.dumps(dict(empresas=out, cobertura=cobertura), ensure_ascii=False))
print(cobertura)
for e in out[:8]: print(e['nome'], e['pago'], e['nContratos'], e['tipos'])

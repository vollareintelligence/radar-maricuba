"""Consolida os dados da Prefeitura para o site. Regras uniformes, documentadas, sem juízo de valor.
Uso: python3 -I coleta/consolidar_prefeitura.py   (gera dados/consolidado/prefeitura.json)
"""
import json, re, unicodedata
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / 'dados' / 'brutos' / 'prefeitura'
CA = ROOT / 'dados' / 'cache' / 'prefeitura'
OUT = ROOT / 'dados' / 'consolidado'
OUT.mkdir(parents=True, exist_ok=True)
FONTE = 'https://transparencia.marica.rj.gov.br'


def norm(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'\s+', ' ', s).strip()


def mi(x):
    return round(float(x) / 1e6, 1)


# ---------------- despesas ----------------
ENTE = [r'prefeitura municipal de marica', r'camara municipal de marica', r'fundo municipal', r'fundo especial',
        r'fundo soberano', r'companhia de cultura e turismo', r'companhia de saneamento de marica',
        r'companhia desenvolvimento marica', r'companhia de desenvolvimento de marica', r'companhia marica alimentos',
        r'empresa publica de transporte', r'\bsomar\b', r'marica global invest', r'instituto de ciencia.*marica',
        r'inst mun de informacao', r'fundacao estatal de saude', r'\bissm\b',
        r'instituto de seguro social de marica']
ENCARGO = [r'\binss\b', r'instituto nacional seguro social', r'pis.?pasep', r'receita federal', r'\bfgts\b', r'caixa economica federal.*fgts']


def classe(nome):
    n = norm(nome)
    if any(re.search(p, n) for p in ENCARGO):
        return 'encargos'
    if any(re.search(p, n) for p in ENTE):
        return 'ente'
    return 'outros'


def load_cred(ano):
    d = pd.read_csv(CA / f'despesas_credores_{ano}.csv', encoding='utf-8-sig')
    s = d.Credor.str.split('<BR>', n=1, expand=True)
    d['credor'] = s[0].str.strip()
    d['doc'] = s[1].str.strip()
    d['classe'] = d.credor.map(classe)
    return d


desp = {}
for ano in (2025, 2026):
    i = pd.read_csv(CA / f'despesas_instituicoes_{ano}.csv', encoding='utf-8-sig')
    c = load_cred(ano)
    e = pd.read_csv(CA / f'despesas_elementos_{ano}.csv', encoding='utf-8-sig')
    assert abs(i.Pago.sum() - c.Pago.sum()) < 1, 'credores x instituições não batem'
    por_classe = {k: dict(n=int(len(g)), pago=mi(g.Pago.sum()), empenhado=mi(g.Empenhado.sum())) for k, g in c.groupby('classe')}
    out = c[c.classe == 'outros'].sort_values('Pago', ascending=False)
    top_out = [dict(nome=r.credor, doc=r.doc, empenhado=mi(r.Empenhado), pago=mi(r.Pago)) for r in out.head(30).itertuples()]
    share20 = float(out.Pago.head(20).sum() / out.Pago.sum() * 100)
    desp[ano] = dict(
        total=dict(empenhado=mi(i.Empenhado.sum()), anulado=mi(i.Anulado.sum()), liquidado=mi(i.Liquidado.sum()), pago=mi(i.Pago.sum())),
        instituicoes=[dict(nome=r.Instituição.title(), empenhado=mi(r.Empenhado), pago=mi(r.Pago)) for r in i.sort_values('Pago', ascending=False).itertuples()],
        elementos=[dict(nome=r.Elemento.capitalize(), pago=mi(r.Pago), empenhado=mi(r.Empenhado)) for r in e.sort_values('Pago', ascending=False).head(14).itertuples()],
        credoresN=int(len(c)), porClasse=por_classe, topOutros=top_out, top20OutrosPct=round(share20, 1),
    )
    print(ano, 'classes', por_classe)

# amostra para conferência humana da classificação
for ano in (2026,):
    c = load_cred(ano)
    print('\nENTES/ENCARGOS 2026 (top):')
    print(c[c.classe != 'outros'].sort_values('Pago', ascending=False)[['credor', 'classe', 'Pago']].head(25).assign(Pago=lambda x: (x.Pago / 1e6).round(1)).to_string(index=False))

# ---------------- folha ----------------
f = pd.read_csv(P / 'folha.csv', low_memory=False)


def num(s):
    return pd.to_numeric(s.astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False), errors='coerce')


f['b'] = num(f.bruto)
f['d'] = num(f.descontos)
f['ativo'] = f.situacao.eq('Ativo')
mens = []
for (a, m), g in f.groupby(['ano', 'mes']):
    ativos = g[g.ativo]
    com_valor = g.b.notna().any()
    mens.append(dict(ano=int(a), mes=int(m), vinculosAtivos=int(len(ativos)), exonerados=int((~g.ativo).sum()),
                     bruto=mi(g.b.sum()) if com_valor else None, liquido=mi(g.liquido.sum()) if com_valor else None))
ult = f[(f.ano == 2026) & (f.mes == 8) & f.ativo]
lot = ult.groupby('lotacao').agg(n=('nome', 'size'), bruto=('b', 'sum')).sort_values('bruto', ascending=False).head(15)
folha = dict(
    mensal=mens,
    lotacoes=[dict(nome=str(k).title(), vinculos=int(r.n), bruto=mi(r.bruto)) for k, r in lot.iterrows()],
    mesRef='08/2026',
    aviso='O portal publica valores de folha só de fevereiro a agosto de 2026. Os demais meses trazem apenas nome, cargo e lotação.',
)

# ---------------- obras ----------------
op = pd.read_csv(P / 'obras_paralisadas.csv')


def motivo_grupo(m):
    n = norm(m)
    if re.search(r'realoc|remanej|retirada|colaborar|atender a solicit|outra prioridade', n):
        return 'Equipe deslocada para outra demanda'
    if re.search(r'material|insumo|vergalh', n):
        return 'Falta de material ou insumo'
    if re.search(r'licen|parecer|vistoria|definic|diretoria|presidencia|projeto|topografia|manual|reajuste|setor|continuidade', n):
        return 'Aguardando definição, projeto, licença ou vistoria'
    return 'Aguardando outra etapa ou equipe'


op['grupo'] = op.motivacao.map(motivo_grupo)
obras_par = [dict(os=int(r.ordem_de_servico), local=str(r.local), bairro=str(r.bairro), lat=float(r.latitude), lng=float(r.longitude),
                  objeto=str(r.objeto_da_intervencao), inicio=str(r.inicio), motivo=str(r.motivacao).strip(), grupo=r.grupo,
                  reinicio=str(r.data_prevista_para_reinicio)) for r in op.itertuples()]
oa = pd.read_csv(P / 'obras_acompanhamento.csv')


def sit(s):
    n = norm(s)
    if n.startswith('conclu'):
        return 'Concluída'
    if 'andamento' in n:
        return 'Em andamento'
    if 'paralis' in n:
        return 'Paralisada'
    return 'Outra situação'


oa['sit'] = oa.situacao.map(sit)
obras_ac = oa.groupby(['tipo_execucao', 'sit']).size().reset_index(name='n').to_dict('records')
obras_total = int(len(oa))
andamento = oa[oa.sit == 'Em andamento']
obras = dict(paralisadas=obras_par, motivosGrupo=op.grupo.value_counts().to_dict(), acompanhamento=obras_ac, acompanhamentoTotal=obras_total,
             fonte=FONTE + '/obras/obras-paralisadas/links-e-arquivos', dataLista='10/10/2026', atualizacaoPortal='19/10/2026',
             semPrevisao=int((op.data_prevista_para_reinicio.str.upper() == 'SEM PREVISÃO').sum()))

# ---------------- secretarias e sanções ----------------
sec = pd.read_csv(P / 'secretarias.csv')
secr = [dict(org=r.secretaria_ou_orgao, titular=str(r.titular_como_aparece), cargo=str(r.cargo)) for r in sec.itertuples()]
sa = pd.read_csv(P / 'sancoes.csv')
sanc = [dict(nome=r.nome, doc=r.cpf_cnpj_como_exibido, tipo=r.tipo_de_sancao, inicio=str(r.inicio_sancao), fim=str(r.fim_sancao),
             status=('' if pd.isna(r.status) else str(r.status)), pub=str(r.data_publicacao_jom), contrato=('' if pd.isna(r.contrato) else str(r.contrato)))
        for r in sa.itertuples()]

# ---------------- vereadores que constam como titulares de secretaria ----------------
vv = pd.read_csv(ROOT / 'dados' / 'brutos' / 'vereadores.csv')
cargo_de = {}
for r in sec.itertuples():
    t = norm(str(r.titular_como_aparece))
    for v in vv.itertuples():
        k = norm(v.nome_civil)
        # regra estrita: nome civil completo (>=3 palavras) aparece inteiro no texto do titular. Sem aproximação,
        # porque atribuir cargo errado a um vereador é erro grave.
        if len(k.split()) >= 3 and k in t:
            cargo_de[int(v.id_sicam)] = dict(nome=v.nome_parlamentar, org=r.secretaria_ou_orgao, titular=str(r.titular_como_aparece))
print('\nvereadores que constam como secretário:', {vv.set_index('id_sicam').nome_parlamentar[k]: v['org'] for k, v in cargo_de.items()})

res = dict(despesas=desp, folha=folha, obras=obras, secretarias=secr, sancoes=sanc, vereadorSecretario=cargo_de,
           fontes=dict(portal=FONTE, despesas=FONTE + '/e-cidade/despesas/padrao', folha=FONTE + '/e-cidade/servidores',
                       obras=FONTE + '/obras', sancoes=FONTE + '/sancoes-administrativas-aplicadas-pela-prefeitura-de-marica/sancoes-administrativas-aplicadas-pela-prefeitura-de-marica/links-e-arquivos',
                       secretarias='https://www.marica.rj.gov.br/secretarias/', consulta='2026-11-14'))
json.dump(res, open(OUT / 'prefeitura.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\nobras motivos:', obras['motivosGrupo'])
print('folha mensal:', [(m['ano'], m['mes'], m['vinculosAtivos'], m['bruto']) for m in mens][-9:])
print('ok ->', OUT / 'prefeitura.json')

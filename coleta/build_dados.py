"""Gera site/dados.js a partir de dados/consolidado + brutos.
Regras: só dados públicos já coletados; mesma régua para todos; nada estimado sem rótulo.
Uso: python3 -I coleta/build_dados.py
"""
import json, re, unicodedata
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
B, C, S = ROOT / 'dados' / 'brutos', ROOT / 'dados' / 'consolidado', ROOT / 'site'


def norm(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'\s+', ' ', s).strip()


vv = pd.read_csv(B / 'vereadores.csv')
site = pd.read_csv(B / 'vereadores_site_camara.csv')
pres = {r['id']: r for r in json.load(open(C / 'presenca.json'))}
votos = {r['id']: r for r in json.load(open(C / 'votos.json'))}
pc = pd.read_csv(C / 'proposicoes_classificadas.csv')
pc['d'] = pd.to_datetime(pc.data, dayfirst=True)
prob = json.load(open(C / 'problemas_que_nao_somem.json'))
jsem = json.load(open(C / 'justificativas_sem_sessao.json'))
PREF = json.load(open(C / 'prefeitura.json')) if (C / 'prefeitura.json').exists() else None
if PREF and (C / 'empresas.json').exists():
    PREF['empresas'] = json.load(open(C / 'empresas.json'))
SECR = json.load(open(C / 'secretarias.json')) if (C / 'secretarias.json').exists() else None
NATAL = json.load(open(C / 'natal.json')) if (C / 'natal.json').exists() else None
PROM = json.load(open(C / 'promessas.json')) if (C / 'promessas.json').exists() else None
PMAPA = json.load(open(C / 'problemas_mapa.json')) if (C / 'problemas_mapa.json').exists() else []
if PREF and (C / 'obras_mapa.json').exists():
    PREF['obrasMapa'] = json.load(open(C / 'obras_mapa.json'))

# junta pelo nome civil (o id do roster do site estava incompleto)
site['k'] = site.nome_civil.map(norm)
site_by_k = {r.k: r for r in site.itertuples()}


def match_site(civil):
    k = norm(civil).replace(' junior', ' jr')
    if k in site_by_k:
        return site_by_k[k]
    for kk, r in site_by_k.items():  # tolerância: um nome contém o outro
        if kk in k or k in kk:
            return r
    return None


GR = ['bairro', 'cobranca', 'lei', 'homenagem', 'outros']
out = []
for v in vv.itertuples():
    pid = int(v.id_sicam)
    p = pres.get(pid)
    if not p:
        continue
    s = match_site(v.nome_civil)
    sub = pc[pc.autor_filtrado_id == pid]
    cont = {g: int((sub.grupo == g).sum()) for g in GR}
    vt = votos.get(pid, {})
    ve, se = vt.get('votos_executivo', 0), vt.get('sim_executivo', 0)
    rec = sub[sub.grupo.isin(['bairro', 'cobranca', 'lei'])].sort_values('d', ascending=False).head(6)
    out.append(dict(
        id=pid, nome=v.nome_parlamentar, civil=str(v.nome_civil).title(),
        partido=(s.partido if s is not None else v.partido),
        emExercicio=(v.em_exercicio == 'sim'),
        foto=(s.foto if s is not None else None),
        ficha=(s.url_ficha if s is not None else None),
        sessoes=p['sessoes'], presencas=p['presencas'], justificadas=p['justificadas'],
        faltas=p['faltas'], licenca=p['licenca_provavel'], pct=p['pct_presenca'],
        motivos=p['motivos'], faltasDatas=p['faltas_datas'],
        inicio=p['inicio'], fim=p['fim'],
        props=cont, propsTotal=int(len(sub)),
        votos=vt.get('votos', 0), nao=vt.get('nao', 0), abst=vt.get('abstencao', 0),
        votosExec=ve, simExec=se,
        recentes=[dict(t=r.tipo, d=r.data, e=str(r.ementa)[:160], g=r.grupo, u=r.url_detalhes) for r in rec.itertuples()],
    ))

# série mensal de proposições por grupo
pc['m'] = pc.d.dt.to_period('M').astype(str)
mensal = pc.groupby(['m', 'grupo']).size().unstack(fill_value=0).reindex(columns=GR, fill_value=0)
mensal = [dict(m=i, **{g: int(r[g]) for g in GR}) for i, r in mensal.iterrows()]

problemas = sorted(prob, key=lambda x: -x['n'])[:40]
for x in problemas:
    x.pop('ids', None)

meta = dict(
    atualizado='2026-11-14', coletaAte=str(pc.d.max().date()),
    sessoes=int(max(p['sessoes'] for p in pres.values())),
    proposicoes=int(len(pc)), votosNominais=int(sum(v['votos'] for v in votos.values())),
    justSemSessao=sum(len(v) if hasattr(v, '__len__') else 1 for v in jsem.values()) if isinstance(jsem, dict) else len(jsem),
    fonte='https://marica.sicam.app/areapublica', fonteCamara='https://marica.rj.leg.br',
    contatoErros='',  # preencher no lançamento (e-mail/WhatsApp do canal de correções)
)
out.sort(key=lambda r: r['nome'])
(S).mkdir(exist_ok=True)
gastometro = dict(
    subsidio=16503.19, cadeiras=21, inicio='2025-01-01',
    fonteSubsidio='https://cmmarica.eloweb.net/portaltransparencia/1/servidores',
    populacao=197277, fontePopulacao='https://www.ibge.gov.br/cidades-e-estados/rj/marica.html',
    dataBase='2026-11-14', diasAno2026=318,
)
js = 'window.DADOS=' + json.dumps(dict(meta=meta, vereadores=out, mensal=mensal, problemas=problemas, prefeitura=PREF, gastometro=gastometro, problemasMapa=PMAPA, secretarias=SECR, natal=NATAL, promessas=PROM), ensure_ascii=False, separators=(',', ':')) + ';'
(S / 'dados.js').write_text(js, encoding='utf-8')
print('vereadores', len(out), 'com foto', sum(1 for r in out if r['foto']), '| dados.js', len(js) // 1024, 'KB')
print('sem foto:', [r['nome'] for r in out if not r['foto']])
print('em exercício:', sum(r['emExercicio'] for r in out), '| meta', meta)

"""Porta de qualidade: o site só é publicado se estas checagens passarem.
Uso: python3 -I coleta/qualidade.py   (sai com código 1 se algo falhar)"""
import json, sys, math
from datetime import date, datetime
from pathlib import Path

S = Path(__file__).resolve().parent.parent / 'site'
t = (S / 'dados.js').read_text(encoding='utf-8')
D = json.loads(t[t.index('{'):t.rindex('}') + 1])
erros = []
def ok(c, msg):
    if not c: erros.append(msg)

M = D['meta']
V = D['vereadores']
ok(len([v for v in V if v['emExercicio']]) == 21, 'esperados 21 vereadores em exercício')
ok(M['sessoes'] > 100 and M['proposicoes'] > 5000 and M['votosNominais'] > 20000, 'volumes da Câmara abaixo do esperado')
ok(M['fonte'].startswith('https://') and M['fonteCamara'].startswith('https://'), 'fontes oficiais ausentes')
idade = (date.today() - datetime.strptime(M['coletaAte'], '%Y-%m-%d').date()).days
ok(idade <= 60, f'coleta com {idade} dias: dados velhos demais para publicar sem aviso')
for v in V:
    if v['emExercicio'] or v.get('foto'):
        ok(bool(v.get('foto')) and (S / v['foto']).exists(), f"foto ausente: {v['nome']}")
    ok(0 <= v['pct'] <= 100, f"presença fora de 0-100: {v['nome']}")
    ok(v['presencas'] + v['justificadas'] + v['faltas'] == v['sessoes'], f"presenças+justificadas+faltas diferente de sessões (licença fica fora do total): {v['nome']}")
P = D.get('prefeitura') or {}
ok('obrasMapa' in P and len(P['obrasMapa']['obras']) >= 200, 'mapa de obras incompleto')
for o in P.get('obrasMapa', {}).get('obras', []):
    ok(-23.2 < o['lat'] < -22.7 and -43.1 < o['lng'] < -42.5, f"coordenada fora de Maricá: obra {o['id']}")
    ok(o.get('fonte', '').startswith('https://'), f"obra sem fonte: {o['id']}")
ok(len(P.get('empresas', {}).get('empresas', P.get('empresas', []))) >= 50, 'ranking de empresas incompleto')
G = D.get('gastometro') or {}
ok(abs(G.get('subsidio', 0) * G.get('cadeiras', 0) - 346566.99) < 1, 'gastômetro: subsídio × cadeiras fora do esperado')
ok(G.get('populacao', 0) > 150000 and G.get('fontePopulacao', '').startswith('https://') and G.get('fonteSubsidio', '').startswith('https://'), 'gastômetro: população ou fontes ausentes')
for a in ('2025', '2026'):
    DA = (P.get('despesas') or {}).get(a) or {}
    ok(any('mara' in i['nome'].lower() and i['pago'] > 10 for i in DA.get('instituicoes', [])), f'gastômetro: pago da Câmara ausente em {a}')
    ok(DA.get('porClasse', {}).get('ente', {}).get('pago', 0) > 0, f'gastômetro: repasses entre entes ausentes em {a}')
PM = D.get('problemasMapa') or []
ok(len([x for x in PM if x.get('lat') is not None]) >= 100, 'camada vermelha incompleta')
for x in PM:
    ok(x.get('precisao') in ('rua', 'bairro', 'sem_coordenada') and x.get('ids') and x.get('fonte'), f"problema sem precisão/ids/fonte: {x.get('rua')}")
    if x.get('lat') is not None:
        ok(-23.2 < x['lat'] < -22.7 and -43.1 < x['lng'] < -42.5, f"problema fora de Maricá: {x['rua']}")
PR = D.get('promessas') or {}
ok(len(PR.get('itens', [])) >= 11 and all(i.get('curto') for i in PR.get('itens', [])) and all(i.get('onde', {}).get('url', '').startswith('https://') and i.get('fontes') and i.get('status') in ('cade', 'parcial', 'prazo') and i.get('achado') for i in PR.get('itens', [])), 'promessas: item sem fonte, status valido ou achado')
import os as _os
_NOT = _os.path.join(_os.path.dirname(__file__), '..', 'dados', 'consolidado', 'noticias.json')
if _os.path.exists(_NOT):
    import json as _json
    _n = _json.load(open(_NOT, encoding='utf-8'))
    ok(all(i.get('link', '').startswith('https://') and i.get('data') and i.get('temas') for i in _n.get('itens', [])), 'noticias: item sem link https, data ou tema')
    ok(_n.get('total', 0) == len(_n.get('itens', [])), 'noticias: total nao bate com itens')
    _ids = {i['id'] for i in PR.get('itens', [])}
    ok(all(set(i.get('temas', [])) <= _ids for i in _n.get('itens', [])), 'noticias: tema que nao e id de promessa')
    ok(not _n.get('falhas'), 'noticias: coleta com consulta sem resposta')
ok(all(n.get('link','').startswith('https://') and n.get('data') and n.get('veiculo') for i in PR.get('itens', []) for n in i.get('imprensa', [])), 'imprensa: item aprovado sem link https, data ou veiculo')
PL = D.get('placar') or {}
ok(bool(PL.get('meses')), 'placar: sem mes fechado')
for _m in PL.get('meses', []):
    ok(len(_m['menos']) == 3 and len(_m['mais']) == 3, 'placar: podio incompleto em ' + _m['mes'])
    ok(_m['sessoes'] >= PL['regras']['minSessoesMes'], 'placar: mes com poucas sessoes ' + _m['mes'])
    ok(all(0 <= r['nota'] <= 100 for r in _m['linhas'] if r['avaliado']), 'placar: nota fora de 0-100 em ' + _m['mes'])
N = D.get('natal') or {}
ok(len(N.get('contratos', [])) == 2 and all(c.get('fonte', '').startswith('https://') and c.get('valor', 0) > 1e6 and c.get('processo') for c in N.get('contratos', [])), 'natal: contratos sem fonte, processo ou valor')
ok(N.get('pagamentos', {}).get('2025', {}).get('pago', 0) > 1e6 and N.get('pagamentos', {}).get('2026', {}).get('pago', 0) > 1e6 and N['pagamentos'].get('fonte', '').startswith('https://'), 'natal: pagamentos ausentes')
def tem_nan(x):
    if isinstance(x, float): return math.isnan(x) or math.isinf(x)
    if isinstance(x, dict): return any(tem_nan(i) for i in x.values())
    if isinstance(x, list): return any(tem_nan(i) for i in x)
    return False
ok(not tem_nan(D), 'há NaN/infinito nos dados')
if erros:
    print('QUALIDADE: FALHOU'); [print(' -', e) for e in erros]; sys.exit(1)
print(f"QUALIDADE: OK ({len(V)} vereadores, {len(P['obrasMapa']['obras'])} obras, coleta até {M['coletaAte']})")

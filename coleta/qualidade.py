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
def tem_nan(x):
    if isinstance(x, float): return math.isnan(x) or math.isinf(x)
    if isinstance(x, dict): return any(tem_nan(i) for i in x.values())
    if isinstance(x, list): return any(tem_nan(i) for i in x)
    return False
ok(not tem_nan(D), 'há NaN/infinito nos dados')
if erros:
    print('QUALIDADE: FALHOU'); [print(' -', e) for e in erros]; sys.exit(1)
print(f"QUALIDADE: OK ({len(V)} vereadores, {len(P['obrasMapa']['obras'])} obras, coleta até {M['coletaAte']})")

"""Todas as obras com coordenadas oficiais, para o mapa. Status normalizado por regra única; texto original preservado.
Uso: python3 -I coleta/consolidar_obras_mapa.py -> dados/consolidado/obras_mapa.json"""
import json, re, unicodedata
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parent.parent
P = ROOT/'dados'/'brutos'/'prefeitura'
def norm(s): return unicodedata.normalize('NFKD', str(s)).encode('ascii','ignore').decode().lower()
def dms(txt):
    m = re.findall(r"(\d+)\D+(\d+)\D+([\d.,]+)\D*([NSEWO])", str(txt).upper())
    out = []
    for d, mi, s, h in m:
        v = int(d) + int(mi)/60 + float(s.replace(',', '.'))/3600
        out.append(-v if h in 'SWO' else v)
    return out
def coords(r):
    try:
        la, lo = float(r.latitude), float(r.longitude)
    except Exception:
        d = dms(r.coordenadas_brutas)
        if len(d) != 2: return None
        la, lo = d
    if not (-23.2 < la < -22.7 and -43.1 < lo < -42.5):  # fora de Maricá: descarta (não corrige no chute)
        return None
    return la, lo
def sit(s):
    n = norm(s)
    if 'paralis' in n: return 'paralisada'
    if 'conclu' in n: return 'concluida'
    if 'andamento' in n: return 'andamento'
    return 'outra'
l = pd.read_csv(P/'obras_localizacao.csv', dtype=str)
a = pd.read_csv(P/'obras_acompanhamento.csv', dtype=str)
pa = pd.read_csv(P/'obras_paralisadas.csv', dtype=str)
A = {str(r.id_ou_contrato): r for r in a.itertuples()}
PA = {str(r.ordem_de_servico): r for r in pa.itertuples()}
out, sem = [], 0
for r in l.itertuples():
    c = coords(r)
    if not c: sem += 1; continue
    ex = A.get(str(r.id_identificacao)); pr = PA.get(str(r.id_identificacao))
    d = dict(id=str(r.id_identificacao), sit=sit(r.situacao), situacaoOriginal=str(r.situacao), exec=str(r.tipo_execucao),
             local=str(r.local) if pd.notna(r.local) else '', bairro=str(r.bairro) if pd.notna(r.bairro) else '',
             obj=str(r.objeto)[:200] if pd.notna(r.objeto) else '', lat=round(c[0], 6), lng=round(c[1], 6), fonte=str(r.url_fonte))
    if ex is not None:
        d.update(inicio=str(ex.inicio) if pd.notna(ex.inicio) else '', prev=str(ex.previsao_ou_conclusao) if pd.notna(ex.previsao_ou_conclusao) else '',
                 pct=str(ex.percentual_executado) if pd.notna(ex.percentual_executado) else '', empresa=str(ex.empresa_executora) if pd.notna(ex.empresa_executora) else '')
    if pr is not None:
        d.update(inicio=str(pr.inicio), motivo=str(pr.motivacao), reinicio=str(pr.data_prevista_para_reinicio))
    out.append(d)
cont = {}
for o in out: cont[o['sit']] = cont.get(o['sit'], 0) + 1
(ROOT/'dados'/'consolidado'/'obras_mapa.json').write_text(json.dumps(dict(obras=out, contagem=cont, semCoordenada=sem), ensure_ascii=False))
print(len(out), cont, 'sem coordenada válida:', sem)

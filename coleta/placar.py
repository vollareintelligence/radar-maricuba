"""Placar mensal da Câmara: os 3 vereadores menos eficientes e os 3 mais eficientes do mês.
Eficiência = entrega (presença + leis/cobranças + indicações) pelo mesmo subsídio de R$ 16.503,19, igual para os 21.

Regras (publicadas no site, iguais para todos):
- Só meses fechados, com pelo menos MIN_SESSOES sessões com lista de presença.
- Só vereadores em exercício que tinham pelo menos MIN_SESS_VEREADOR sessões avaliáveis no mês.
- Pontos (0 a 100):
    Presença em plenário ...... até 50  = 50 × presenças ÷ sessões avaliáveis
    Leis e cobranças .......... até 30  = 15 por projeto de lei/emenda/resolução ou requerimento ao Executivo (máx. 2)
    Indicações de bairro ...... até 20  =  2 por indicação (máx. 10)
    Falta sem justificativa ... −5 cada
    Homenagens (moções, títulos) não pontuam.
- Sessão avaliável: presença, falta sem justificativa ou ausência justificada por motivo político/outro.
  Ausência justificada por saúde ou família e provável licença não entram na conta (nem a favor nem contra).
- Desempate (para baixo): menos presenças, depois menos leis e cobranças.
Uso: python3 -I coleta/placar.py
"""
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
B, C = ROOT / 'dados' / 'brutos', ROOT / 'dados' / 'consolidado'
MIN_SESSOES, MIN_SESS_VEREADOR = 6, 4
SUBSIDIO = 16503.19  # igual para os 21; folha da Câmara (Eloweb). Assessores e gabinete não entram (não são publicados por vereador)
FONTE_SUBSIDIO = 'https://cmmarica.eloweb.net/portaltransparencia/1/servidores'
SAUDE = 'pessoal (saúde ou família)'

st = pd.DataFrame(json.load(open(C / 'presenca_sessoes.json', encoding='utf-8')))
st['m'] = st.data.str[:7]
ver = pd.read_csv(B / 'vereadores.csv')
tit = {int(r.id_sicam): r.nome_parlamentar for r in ver.itertuples() if r.em_exercicio == 'sim'}
pc = pd.read_csv(C / 'proposicoes_classificadas.csv')
pc['dt'] = pd.to_datetime(pc.data, dayfirst=True)
pc['m'] = pc.dt.dt.strftime('%Y-%m')
ultima = st.data.max()  # última sessão coletada
MESES_PT = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']

meses = []
for m, g in st[st.id.isin(tit)].groupby('m'):
    n_sess = g.data.nunique()
    fechado = m < ultima[:7]
    if not fechado or n_sess < MIN_SESSOES:
        continue
    linhas = []
    for pid, nome in tit.items():
        s = g[g.id == pid]
        P = int((s.st == 'P').sum())
        F = int((s.st == 'F').sum())
        Jsaude = int(((s.st == 'J') & (s.motivo == SAUDE)).sum())
        J = int(((s.st == 'J') & (s.motivo != SAUDE)).sum())
        L = int((s.st == 'L').sum())
        aval = P + J + F
        pr = pc[(pc.m == m) & (pc.autor_filtrado_id == pid)]
        leis = int((pr.grupo == 'lei').sum())
        cobr = int((pr.grupo == 'cobranca').sum())
        bairro = int((pr.grupo == 'bairro').sum())
        homen = int((pr.grupo == 'homenagem').sum())
        base = dict(id=pid, nome=nome, presencas=P, justificadas=J, justSaude=Jsaude, faltas=F, licenca=L,
                    avaliaveis=aval, leis=leis, cobrancas=cobr, indicacoes=bairro, homenagens=homen)
        if aval < MIN_SESS_VEREADOR:
            linhas.append(base | dict(avaliado=False))
            continue
        p_pres = 50 * P / aval
        p_lc = 15 * min(2, leis + cobr)
        p_ind = 2 * min(10, bairro)
        pen = -5 * F
        nota = max(0.0, p_pres + p_lc + p_ind + pen)
        base['custoPorPresenca'] = round(SUBSIDIO / P, 2) if P else None
        base['custoPorEntrega'] = round(SUBSIDIO / (leis + cobr), 2) if (leis + cobr) else None
        linhas.append(base | dict(avaliado=True, pPresenca=round(p_pres, 1), pLeisCobrancas=p_lc,
                                  pIndicacoes=p_ind, penalidade=pen, nota=round(nota, 1)))
    av = [r for r in linhas if r['avaliado']]
    av.sort(key=lambda r: (r['nota'], r['presencas'], r['leis'] + r['cobrancas']))
    for i, r in enumerate(av):
        r['posicaoDeBaixo'] = i + 1
    ano, mm = m.split('-')
    meses.append(dict(mes=m, rotulo=f'{MESES_PT[int(mm) - 1]}/{ano}', sessoes=int(n_sess),
                      menos=[r['id'] for r in av[:3]], mais=[r['id'] for r in av[::-1][:3]],
                      linhas=av + [r for r in linhas if not r['avaliado']]))

saida = dict(geradoEm=pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%dT%H:%MZ'), ultimaSessao=ultima,
             regras=dict(minSessoesMes=MIN_SESSOES, minSessoesVereador=MIN_SESS_VEREADOR),
             subsidio=SUBSIDIO, fonteSubsidio=FONTE_SUBSIDIO,
             fonte='https://marica.sicam.app/areapublica/', meses=meses[::-1])
(C / 'placar.json').write_text(json.dumps(saida, ensure_ascii=False, indent=1), encoding='utf-8')
if __name__ == '__main__':
    for mm in saida['meses'][:3]:
        nomes = {r['id']: r for r in mm['linhas']}
        print(mm['rotulo'], mm['sessoes'], 'sessões | menos:',
              [(nomes[i]['nome'], nomes[i]['nota']) for i in mm['menos']], '| mais:',
              [(nomes[i]['nome'], nomes[i]['nota']) for i in mm['mais']])

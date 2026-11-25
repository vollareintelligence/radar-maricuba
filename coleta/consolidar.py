"""Radar Maricuba — consolida os dados brutos do SICAM em uma base única para o site.

Regras (iguais para todos os vereadores):
- Presença só conta em sessões com lista publicada (Ordinária/Extraordinária, nunca Audiência Pública).
- Janela de exercício: da primeira à última presença registrada de cada parlamentar.
- Sequência de 4+ sessões seguidas sem presença e sem justificativa = "provável licença, a confirmar"
  (não entra como falta).
- Ausência justificada = existe documento "Justificativa Ausência" do próprio gabinete citando a data.
- Proposições classificadas pelo tipo oficial; Projetos de Lei de nome de rua/data/semana/campanha
  vão para "homenagens e datas".
"""
import json, re, unicodedata
from collections import defaultdict
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
B = ROOT / 'dados' / 'brutos'
OUT = ROOT / 'dados' / 'consolidado'
OUT.mkdir(parents=True, exist_ok=True)

MESES = {'janeiro': 1, 'fevereiro': 2, 'marco': 3, 'março': 3, 'abril': 4, 'maio': 5, 'junho': 6, 'julho': 7,
         'agosto': 8, 'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12}
RUN_LICENCA = 4


def norm(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'\s+', ' ', s).strip()


ap = pd.read_csv(B / 'apelidos.csv')
ver = pd.read_csv(B / 'vereadores.csv')
ses = pd.read_csv(B / 'sessoes.csv')
pre = pd.read_csv(B / 'presencas.csv')
vot = pd.read_csv(B / 'votacoes.csv')
vn = pd.read_csv(B / 'votos_nominais.csv')
pr = pd.read_csv(B / 'proposicoes.csv')

alias = {norm(r.nome_como_aparece): int(r.id_sicam) for r in ap.itertuples()}
pre['id'] = pre.nome_como_aparece.map(lambda x: alias.get(norm(x)))
vn['id'] = vn.nome_como_aparece.map(lambda x: alias.get(norm(x)))
ses['d'] = pd.to_datetime(ses.data, dayfirst=True)
pre['d'] = pd.to_datetime(pre.data, dayfirst=True)
pr['d'] = pd.to_datetime(pr.data, dayfirst=True)

# ---------- sessões válidas para presença ----------
sem_reg = set(pre.loc[pre.nome_como_aparece == 'sem registro', 'id_sessao'])
validas = ses[(ses.tipo.isin(['Ordinária', 'Extraordinária'])) & (~ses.id_sessao.isin(sem_reg))].sort_values('d')
ordem = list(validas.id_sessao)
data_sessao = dict(zip(ses.id_sessao, ses.d))
presentes = defaultdict(set)
for r in pre.dropna(subset=['id']).itertuples():
    presentes[r.id_sessao].add(int(r.id))

# ---------- justificativas de ausência ----------
just = pr[pr.tipo == 'Justificativa Ausência'].copy()


def datas_justificadas(ementa, d_prot):
    t = norm(ementa)
    out = set()
    # dd/mm/aaaa ou dd/mm/aa (ano com 2 dígitos)
    for dd, mm, yy in re.findall(r'(?<!\d)(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4}|\d{2})(?!\d)', t):
        yy = int(yy)
        yy = yy + 2000 if yy < 100 else yy
        try:
            out.add(pd.Timestamp(yy, int(mm), int(dd)))
        except ValueError:
            pass
    # dd/mm sem ano (ano do protocolo; se ficar >60 dias no futuro, ano anterior)
    for dd, mm in re.findall(r'(?<!\d)(\d{1,2})\s*/\s*(\d{1,2})(?!\s*/|\d)', t):
        try:
            cand = pd.Timestamp(d_prot.year, int(mm), int(dd))
        except ValueError:
            continue
        if (cand - d_prot).days > 60:
            cand = pd.Timestamp(d_prot.year - 1, int(mm), int(dd))
        out.add(cand)
    # "12 de marco", "21 do mes de maio", "12 de mes de marco", "02 abril de 2025", "10, 11 e 12 de maio"
    sep = r'(?:\s*(?:de|do)\s+(?:mes\s+(?:de|do)\s+)?|\s+(?:mes\s+(?:de|do)\s+)?)'
    for grupo, mes in re.findall(r'((?:\d{1,2}\s*(?:,|e|a)?\s*)+)' + sep + r'(' + '|'.join(MESES) + r')', t):
        m = MESES[mes]
        for dd in re.findall(r'\d{1,2}', grupo):
            y = d_prot.year
            try:
                cand = pd.Timestamp(y, m, int(dd))
            except ValueError:
                continue
            if (cand - d_prot).days > 60:  # protocolado em janeiro sobre dezembro
                cand = pd.Timestamp(y - 1, m, int(dd))
            out.add(cand)
    motivo = 'compromisso político' if 'politic' in t else ('pessoal (saúde ou família)' if re.search(r'saude|medic|filh|famil|luto|falec', t) else 'outro / não informado')
    return out, motivo


jdates = defaultdict(dict)  # id -> {date: (motivo, url)}
nome_to_id = {norm(r.nome_parlamentar): int(r.id_sicam) for r in ver.itertuples()}
for r in just.itertuples():
    pid = int(r.autor_filtrado_id)
    ds, motivo = datas_justificadas(r.ementa, r.d)
    for d in ds:
        jdates[pid][d.normalize()] = (motivo, r.url_detalhes)

# ---------- presença por parlamentar ----------
pres_rows, licencas = [], []
status_sessoes = []  # por sessão: P presente, J justificada, F falta, L provável licença (usado no Placar mensal)
for v in ver.itertuples():
    pid = int(v.id_sicam)
    seq = [s for s in ordem if True]
    idx_pres = [i for i, s in enumerate(seq) if pid in presentes[s]]
    if not idx_pres:
        continue
    win = seq[idx_pres[0]: idx_pres[-1] + 1]
    if v.em_exercicio == 'sim' and idx_pres[-1] < len(seq) - 1:
        win = seq[idx_pres[0]:]  # titular em exercício: janela vai até a última sessão
    status = []
    for s in win:
        d = data_sessao[s].normalize()
        if pid in presentes[s]:
            status.append((s, 'P'))
        elif d in jdates[pid]:
            status.append((s, 'J'))
        else:
            status.append((s, 'F'))
    # sequências longas sem presença nem justificativa -> provável licença
    i = 0
    while i < len(status):
        if status[i][1] == 'F':
            j = i
            while j < len(status) and status[j][1] == 'F':
                j += 1
            if j - i >= RUN_LICENCA:
                licencas.append(dict(id=pid, nome=v.nome_parlamentar, de=str(data_sessao[status[i][0]].date()),
                                     ate=str(data_sessao[status[j - 1][0]].date()), sessoes=j - i))
                for k in range(i, j):
                    status[k] = (status[k][0], 'L')
            i = j
        else:
            i += 1
    status_sessoes += [dict(id=pid, data=str(data_sessao[s].date()), st=st, motivo=(jdates[pid][data_sessao[s].normalize()][0] if st == 'J' else None)) for s, st in status]
    c = defaultdict(int)
    for _, st in status:
        c[st] += 1
    considered = c['P'] + c['J'] + c['F']
    motivos = defaultdict(int)
    for s, st in status:
        if st == 'J':
            motivos[jdates[pid][data_sessao[s].normalize()][0]] += 1
    pres_rows.append(dict(id=pid, nome=v.nome_parlamentar, titular=v.em_exercicio == 'sim',
                          inicio=str(data_sessao[win[0]].date()), fim=str(data_sessao[win[-1]].date()),
                          sessoes=considered, presencas=c['P'], justificadas=c['J'], faltas=c['F'],
                          licenca_provavel=c['L'],
                          pct_presenca=round(100 * c['P'] / considered, 1) if considered else None,
                          motivos=dict(motivos),
                          faltas_datas=[str(data_sessao[s].date()) for s, st in status if st == 'F']))
presenca = pd.DataFrame(pres_rows)

# justificativas que citam datas sem sessão registrada no portal
datas_validas = {data_sessao[s].normalize() for s in ordem}
orfas = defaultdict(list)
for pid, dd in jdates.items():
    for d, (motivo, url) in dd.items():
        if d not in datas_validas and d >= pd.Timestamp(2025, 1, 1):
            orfas[str(d.date())].append(pid)

# ---------- votos ----------
vot['proc'] = vot.processo.str.replace('Proc. ', '', regex=False).str.strip()
vn['proc'] = vn.processo.str.replace('Proc. ', '', regex=False).str.strip()
vn = vn.merge(vot[['id_sessao', 'processo', 'tipo_materia', 'numero_materia', 'fase', 'resultado']].drop_duplicates(['id_sessao', 'processo']),
              on=['id_sessao', 'processo'], how='left')
vn['executivo'] = vn.tipo_materia.fillna('').str.contains('Executivo|Mensagem', case=False)
votos = []
for pid, g in vn.dropna(subset=['id']).groupby('id'):
    ex = g[g.executivo]
    votos.append(dict(id=int(pid), votos=len(g), sim=int((g.voto == 'Sim').sum()), nao=int((g.voto == 'Não').sum()),
                      abstencao=int((g.voto == 'Abstenção').sum()), votos_executivo=len(ex),
                      sim_executivo=int((ex.voto == 'Sim').sum())))
votos = pd.DataFrame(votos)
naos = vn[vn.voto != 'Sim'][['id', 'id_sessao', 'processo', 'tipo_materia', 'numero_materia', 'voto', 'resultado', 'url_fonte']]

# ---------- classificação das proposições ----------
HOMEN_PL = re.compile(r'denomina|nomenclatura|institui o dia|dia municipal|semana municipal|mes municipal|campanha|calendario oficial|'
                      r'patrimonio (historico|cultural|imaterial)|utilidade publica|data comemorativa|outubro|novembro|dezembro (laranja|azul|vermelho)')


def grupo(tipo, ementa):
    t, e = norm(tipo), norm(ementa)
    if t.startswith('justificativa'):
        return 'ausencia'
    if t in ('indicacao',):
        return 'bairro'
    if t.startswith('mocao') or 'titulo de cidadao' in t or 'honra ao merito' in t:
        return 'homenagem'
    if t.startswith('projeto de lei') and HOMEN_PL.search(e):
        return 'homenagem'
    if t.startswith('projeto') or t.startswith('emenda') or t.startswith('proposta de emenda') or t == 'indicacao legislativa':
        return 'lei'
    if t.startswith('requerimento') and not any(k in t for k in ('oficializacao', 'licenca', 'inclusao')):
        return 'cobranca'
    return 'outros'


pr['grupo'] = [grupo(t, e) for t, e in zip(pr.tipo, pr.ementa)]

# ---------- bairro e rua ----------
BAIRROS = ['Jardim Atlântico Leste', 'Jardim Atlântico Oeste', 'Jardim Atlântico Central', 'Jardim Atlântico', 'Recanto de Itaipuaçu',
           'Barroco', 'Itaipuaçu', 'Chácaras de Inoã', 'Inoã', 'São José do Imbassaí', 'Itapeba', 'Flamengo', 'Araçatiba', 'Mumbuca',
           'Ponta Negra', 'Jaconé', 'Guaratiba', 'Cordeirinho', 'Bambuí', 'Barra de Maricá', 'Zacarias', 'Ubatiba', 'Retiro',
           'Pindobas', 'Pindobal', 'Ponta Grossa', 'Condado de Maricá', 'Caxito', 'Spar', 'Manoel Ribeiro', 'Silvado', 'Calaboca',
           'Espraiado', 'Lagarto', 'Bananal', 'Marquês de Maricá', 'Santa Paula', 'Parque Nanci', 'Cajueiros', 'Jardim Interlagos',
           'Eldorado', 'Itaocaia Valley', 'Morada das Águias', 'Camburi', 'Rincão Mimoso', 'Vale da Figueira', 'Pedreiras',
           'Jardim Balneário Ipitangas', 'Balneário Bambuí', 'Praia de Itaipuaçu', 'Centro', 'Itaocaia', 'Inoã II', 'Divinéia',
           'Jardim Nova Metrópole', 'Estrada de Itaipuaçu', 'Recanto', 'Vale da Figueira', 'Rio Fundo', 'Cassorotiba', 'São Bento da Lagoa',
           'Restinga de Maricá', 'Engenho do Mato', 'Amizade', 'Lagoinha', 'Morro do Gravatá']
BAIRROS = sorted(set(BAIRROS), key=len, reverse=True)
BN = [(b, norm(b)) for b in BAIRROS]
MACRO = {'jardim atlantico leste': 'Itaipuaçu', 'jardim atlantico oeste': 'Itaipuaçu', 'jardim atlantico central': 'Itaipuaçu',
         'jardim atlantico': 'Itaipuaçu', 'recanto de itaipuacu': 'Itaipuaçu', 'barroco': 'Itaipuaçu', 'praia de itaipuacu': 'Itaipuaçu',
         'estrada de itaipuacu': 'Itaipuaçu', 'recanto': 'Itaipuaçu', 'chacaras de inoa': 'Inoã', 'inoa ii': 'Inoã',
         'balneario bambui': 'Bambuí', 'jardim nova metropole': 'Itapeba'}


def achar_bairro(e):
    t = norm(e)
    for b, bn in BN:
        if re.search(r'\b' + re.escape(bn) + r'\b', t):
            return b
    return None


RUA = re.compile(r'\b(rua|avenida|av\.|estrada|travessa|rodovia|alameda|praca|via)\s+([^,;:\-–()]{1,60})')


def achar_rua(e):
    t = norm(e)
    m = RUA.search(t)
    if not m:
        return None
    nome = re.split(r'\b(no bairro|bairro|localizad|situad|na altura|nas proximidades|proximo|esquina|entre|em frente|com a|com rua|marica|n[oº°]\s?\d)', m.group(2))[0]
    nome = re.sub(r'\s+', ' ', nome).strip(' .')
    tipo = m.group(1).replace('av.', 'avenida').replace('praca', 'praça')
    return (tipo + ' ' + nome).strip().title() if nome else None


TEMAS = [('asfalto', r'asfalt|paviment|recapeament|tapa.?buraco|buraco|calcament|meio.?fio'),
         ('drenagem', r'drenagem|alagament|galeria|manilh|bueiro|escoamento'),
         ('esgoto', r'esgoto|saneamento|fossa'),
         ('iluminacao', r'ilumina|lampada|poste'),
         ('limpeza', r'rocad|capina|limpeza|lixo|entulho|poda'),
         ('transito', r'quebra.?mola|redutor|sinaliza|semaforo|faixa de pedestre|lombada|ponto de onibus|abrigo'),
         ('saude', r'saude|posto|ubs|medic'),
         ('agua', r'agua|abastecimento')]


def tema(e):
    t = norm(e)
    for k, rx in TEMAS:
        if re.search(rx, t):
            return k
    return 'outros'


pr['bairro'] = pr.ementa.map(achar_bairro)
pr['macro'] = pr.bairro.map(lambda b: MACRO.get(norm(b), b) if b else None)
pr['rua'] = pr.ementa.map(achar_rua)
pr['tema'] = pr.ementa.map(tema)

ind = pr[pr.grupo == 'bairro']
rep = (ind.dropna(subset=['rua']).groupby(['rua', 'macro', 'tema'], dropna=False)
       .agg(n=('processo', 'count'), autores=('autores', 'nunique'), d0=('d', 'min'), d1=('d', 'max'), ids=('processo', list))
       .reset_index().query('n >= 3').sort_values('n', ascending=False))

# ---------- saídas ----------
json.dump(status_sessoes, open(OUT / 'presenca_sessoes.json', 'w', encoding='utf-8'), ensure_ascii=False)
presenca.to_json(OUT / 'presenca.json', orient='records', force_ascii=False, indent=1)
votos.to_json(OUT / 'votos.json', orient='records', force_ascii=False, indent=1)
naos.to_csv(OUT / 'votos_nao_abstencao.csv', index=False)
pr.drop(columns=['d']).to_csv(OUT / 'proposicoes_classificadas.csv', index=False)
rep.assign(d0=rep.d0.dt.date.astype(str), d1=rep.d1.dt.date.astype(str)).to_json(OUT / 'problemas_que_nao_somem.json', orient='records', force_ascii=False, indent=1)
pd.DataFrame(licencas).to_csv(OUT / 'licencas_provaveis.csv', index=False)
json.dump(orfas, open(OUT / 'justificativas_sem_sessao.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# ---------- resumo ----------
g = pr.groupby(['autor_filtrado_id', 'grupo']).size().unstack(fill_value=0)
print('Sessões válidas para presença:', len(ordem))
print(presenca.sort_values('pct_presenca')[['nome', 'titular', 'inicio', 'sessoes', 'presencas', 'justificadas', 'faltas', 'licenca_provavel', 'pct_presenca']].to_string(index=False))
print('\nProváveis licenças:'); print(pd.DataFrame(licencas).to_string(index=False))
print('\nJustificativas citando datas sem sessão no portal:', {k: len(v) for k, v in sorted(orfas.items())})
print('\nGrupos:', pr.grupo.value_counts().to_dict())
print('Indicações com bairro:', round(100 * ind.bairro.notna().mean(), 1), '% | com rua:', round(100 * ind.rua.notna().mean(), 1), '%')
print('Ruas com 3+ pedidos do mesmo tema:', len(rep))
print(rep.head(12)[['rua', 'macro', 'tema', 'n', 'autores']].to_string(index=False))
nome = dict(zip(ver.id_sicam, ver.nome_parlamentar))
print('\nVotos:'); print(votos.assign(nome=votos.id.map(nome)).sort_values('nao', ascending=False)[['nome', 'votos', 'nao', 'abstencao', 'votos_executivo', 'sim_executivo']].to_string(index=False))

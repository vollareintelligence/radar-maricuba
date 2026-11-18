"""Curadoria das notícias: o robô só PROPÕE (noticias.json); o site só mostra o que foi APROVADO.

Uso:
  python3 coleta/curadoria.py pendentes            lista candidatas ainda não decididas, por promessa
  python3 coleta/curadoria.py aprovar ID [ID ...]  grava na imprensa.json (vira "Na imprensa" no card)
  python3 coleta/curadoria.py descartar ID [ID ...] não mostra e não volta a propor

Arquivos: dados/consolidado/imprensa.json (aprovadas, com cópia dos dados da notícia)
          dados/consolidado/curadoria.json (ids descartados)
"""
import json
import sys
from pathlib import Path

C = Path(__file__).resolve().parent.parent / 'dados' / 'consolidado'


def ler(nome, padrao):
    p = C / nome
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else padrao


def gravar(nome, obj):
    (C / nome).write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding='utf-8')


def main():
    cmd, ids = (sys.argv[1] if len(sys.argv) > 1 else 'pendentes'), sys.argv[2:]
    cand = {i['id']: i for i in ler('noticias.json', {'itens': []})['itens']}
    imp = ler('imprensa.json', {'itens': []})
    cur = ler('curadoria.json', {'descartadas': []})
    aprov = {i['id'] for i in imp['itens']}
    if cmd == 'pendentes':
        prom = {i['id']: i for i in ler('promessas.json', {'itens': []})['itens']}
        grupos = {}
        for i in cand.values():
            if i['id'] in aprov or i['id'] in cur['descartadas']:
                continue
            for t in i['temas']:
                grupos.setdefault(t, []).append(i)
        for t, lst in grupos.items():
            print(f"\n## {t} | card: {prom.get(t, {}).get('curto', '?')} [{prom.get(t, {}).get('status', '?')}]")
            for i in sorted(lst, key=lambda x: x['data'], reverse=True):
                print(f"  {i['id']} | {i['data']} | {i['titulo'][:95]} | link original: {'sim' if i.get('linkOriginal') else 'NAO'}")
        print(f"\n{sum(len(v) for v in grupos.values())} pendentes")
    elif cmd == 'aprovar':
        for k in ids:
            i = cand.get(k)
            if not i:
                print('id nao encontrado em noticias.json:', k); continue
            if k in aprov:
                continue
            imp['itens'].append({kk: i[kk] for kk in ('id', 'titulo', 'veiculo', 'data', 'temas')} | {'link': i.get('linkOriginal') or i['link'], 'linkOriginal': bool(i.get('linkOriginal'))})
        gravar('imprensa.json', imp); print('aprovadas:', len(imp['itens']))
    elif cmd == 'descartar':
        cur['descartadas'] = sorted(set(cur['descartadas']) | set(ids))
        gravar('curadoria.json', cur); print('descartadas:', len(cur['descartadas']))


if __name__ == '__main__':
    main()

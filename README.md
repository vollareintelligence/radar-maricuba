# Lupa Maricá

Site de acompanhamento da Câmara e da Prefeitura de Maricá, feito só com dados públicos oficiais.
Mostra fatos com a fonte ao lado de cada número. Não faz acusação; a mesma régua vale para todos.

## Como funciona
- `dados/brutos/`: coletas das fontes oficiais (SICAM da Câmara e portal da Prefeitura).
- `coleta/consolidar*.py`: transformam os brutos em `dados/consolidado/`.
- `coleta/build_dados.py`: gera `site/dados.js`.
- `coleta/qualidade.py`: porta de qualidade; se falhar, o site não é publicado.
- `site/`: o site estático (publicado pelo GitHub Pages).
- `coleta/build_dist.py`: gera `dist/radar-maricuba.html`, arquivo único para compartilhar.

## Atualizar os dados

**Câmara (SICAM) — automatizado, rodar no PC** (o portal é acessado de lá; o GitHub Actions não faz essa coleta):
```
py -m venv .venv && .venv\Scripts\pip install pandas beautifulsoup4     # só na primeira vez
set PYTHONUTF8=1
.venv\Scripts\python coleta\atualizar_camara.py
```
Coleta sessões, votações e proposições (1 requisição a cada 2,5 s, ~8 min na primeira vez; depois usa cache),
recusa a coleta se algum CSV encolher mais de 2% (restaura o anterior), consolida, recalcula o placar, gera `site/dados.js`
e roda a porta de qualidade. Depois é só conferir (`git diff --stat`), commitar e dar push. Para agendar, use o Agendador de Tarefas do Windows.
Não regenera o mapa de problemas recorrentes (geocodificação via Nominatim).

**Prefeitura — ainda manual.** As telas do e-Cidade exigem sessão com cookie e token (Laravel); os coletores estão no PC
(`coleta/prefeitura/`), fora deste repositório. Depois de coletar: coloque os CSVs em `dados/brutos/prefeitura/`,
rode `consolidar_prefeitura.py`, `consolidar_empresas.py`, `consolidar_secretarias.py`, `consolidar_obras_mapa.py`, depois
`python3 -I coleta/build_dados.py && python3 -I coleta/qualidade.py`, commit e push. O GitHub Actions publica sozinho.

O robô do GitHub (2x ao dia) só atualiza notícias e checa as fontes; abre uma Issue se os dados oficiais ficarem
parados há mais de 7 dias ou se alguma fonte sair do ar.

## Antes de divulgar
- Preencher `contatoErros` em `coleta/build_dados.py` (canal para reportar erros).
- Conferir os termos de uso do SICAM e da Prefeitura para publicação.
- Mapa: fundo do OpenStreetMap exige o crédito que já aparece no canto do mapa.

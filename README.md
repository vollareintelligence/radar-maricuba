# Radar da Gastança · Maricúba

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
A coleta nas fontes oficiais ainda é feita fora deste repositório. Depois de coletar:
1. Coloque os CSVs novos em `dados/brutos/` e rode os `consolidar*.py`.
2. `python3 -I coleta/build_dados.py && python3 -I coleta/qualidade.py`
3. Faça o commit e o push. O GitHub Actions publica sozinho.

## Antes de divulgar
- Preencher `contatoErros` em `coleta/build_dados.py` (canal para reportar erros).
- Conferir os termos de uso do SICAM e da Prefeitura para publicação.
- Mapa: fundo do OpenStreetMap exige o crédito que já aparece no canto do mapa.

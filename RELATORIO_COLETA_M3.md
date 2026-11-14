# Radar Maricuba — Relatório de Coleta (Módulo 3: Camada Vermelha do Mapa)

**Data da conclusão:** 14/11/2026  
**Ambiente:** Windows 11 (Python 3.12 via `.venv\Scripts\python.exe`)  
**Serviço de Geocodificação:** Nominatim (OpenStreetMap)  
**User-Agent:** `radar-maricuba/1.0 (contato: theobarros.com.br; coleta publica)`  
**Taxa de requisição:** 1 requisição a cada 1,15s (sem concorrência, respeitando o limite de 1 req/s)  
**Cache local:** `dados/cache/nominatim/` (respostas brutas em JSON intactas para nunca repetir chamadas)  
**Bounding Box de Maricá:** `-23.2 < lat < -22.7` e `-43.1 < lng < -42.5`  

---

## 1. Resumo da Geocodificação

Foram processados todos os **143 problemas recorrentes** de [problemas_que_nao_somem.json](file:///C:/Users/theob/.gemini/antigravity/scratch/radar-maricuba/dados/consolidado/problemas_que_nao_somem.json) (casos de mesma rua + mesmo tema com 3 ou mais proposições oficiais da Câmara de Maricá).

| Precisão | Quantidade de Pontos | Percentual | Descrição no Mapa |
| :--- | :---: | :---: | :--- |
| **`rua`** | **99** | 69,2% | Ponto exato da via oficial no OpenStreetMap (`class = highway`). Centroide da via. |
| **`bairro`** | **36** | 25,2% | Centroide aproximado do bairro/distrito (`macro`), pois a via específica não constava mapeada. Rotulado como *"posição aproximada (bairro)"*. |
| **`sem_coordenada`** | **8** | 5,6% | Sem correspondência confiável (via não mapeada e sem macro informado, ou localidade não indexada no OSM). Nenhum ponto arbitrário foi inventado. |
| **Total** | **143** | **100,0%** | **135 pontos geolocalizados (94,4% de cobertura no mapa)** |

---

## 2. Lista dos Itens Sem Coordenada (`sem_coordenada`)

Conforme a regra do projeto (*"não inventar ponto"*), os 8 itens a seguir foram preservados com `lat = null` e `lng = null`:

| # | Rua / Local | Macro (Bairro) | Tema | Proposições (N) | Autores | Período | IDs dos Processos | Motivo Técnico |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :--- | :--- |
| 1 | Avenida Nero Da Silva Bittencourt | *Nulo* | outros | 6 | 1 | 27/03/2025 a 31/07/2025 | 2346/2025, 2257/2025, 2124/2025, 939/2025, 940/2025, 761/2025 | Via não consta no OSM; macro não informado na proposição |
| 2 | Avenida Nero Da Silva Bittencourt | *Nulo* | transito | 5 | 3 | 05/03/2025 a 27/07/2026 | 697/2025, 3225/2026, 2433/2026, 1166/2026, 2130/2025 | Via não consta no OSM; macro não informado na proposição |
| 3 | Rua Luiz Fernando Dos Santos Caetano | *Nulo* | transito | 5 | 3 | 14/04/2025 a 29/06/2026 | 1750/2025, 1100/2026, 1671/2025, 3250/2025, 1021/2025 | Via não consta no OSM; macro não informado na proposição |
| 4 | Praça Equipada | *Nulo* | outros | 4 | 1 | 07/03/2025 a 07/05/2025 | 1643/2025, 1642/2025, 883/2025, 592/2025 | Denominação genérica de praça; sem macro informado |
| 5 | Avenida Nero Da Silva Bittencourt | *Nulo* | asfalto | 3 | 2 | 26/05/2025 a 24/06/2025 | 2043/2025, 2347/2025, 2078/2025 | Via não consta no OSM; macro não informado na proposição |
| 6 | Praça Do Ivan | *Nulo* | outros | 3 | 1 | 18/06/2025 a 30/06/2025 | 2386/2025, 2291/2025, 2238/2025 | Denominação popular de praça; sem macro informado |
| 7 | Rua Luiz Fernando Dos Santos Caetano | *Nulo* | outros | 3 | 2 | 24/03/2025 a 22/07/2025 | 2644/2025, 1194/2025, 766/2025 | Via não consta no OSM; macro não informado na proposição |
| 8 | Rua Nossa Senhora De Fatima | São Bento da Lagoa | transito | 3 | 2 | 07/04/2025 a 09/09/2025 | 1033/2025, 439/2026, 3164/2025 | Nem a rua nem a localidade "São Bento da Lagoa" foram encontradas no OSM |

---

## 3. Lista dos Descartados Fora de Maricá

- **Total de resultados descartados fora do bounding box de Maricá:** **0**
- *Justificativa:* Todas as consultas foram estruturadas explicitamente com o sufixo `", Maricá, Rio de Janeiro, Brasil"`. Nenhum candidato fora dos limites geográficos estipulados (-23.2 < lat < -22.7 e -43.1 < lng < -42.5) foi retornado ou admitido.

---

## 4. Estrutura do Arquivo Gerado (`problemas_mapa.json`)

O arquivo [problemas_mapa.json](file:///C:/Users/theob/.gemini/antigravity/scratch/radar-maricuba/dados/consolidado/problemas_mapa.json) contém a lista completa dos 143 itens com os seguintes campos:
- `rua`: Nome da via ou logradouro original.
- `macro`: Bairro ou distrito associado (ou `null`).
- `tema`: Categoria temática padronizada (ex.: `asfalto`, `iluminacao`, `transito`, `outros`, `limpeza`, `drenagem`, `saude`, `esgoto`).
- `n`: Quantidade de proposições recorrentes registradas no SICAM.
- `autores`: Quantidade de vereadores distintos que protocolaram pedidos para o mesmo local.
- `d0`: Data da primeira proposição (`YYYY-MM-DD`).
- `d1`: Data da última proposição (`YYYY-MM-DD`).
- `ids`: Lista com os números dos processos oficiais da Câmara (ex.: `["1341/2025", "1161/2026"]`) para geração de hiperlinks diretos ao SICAM.
- `lat`: Latitude geográfica em graus decimais (ou `null`).
- `lng`: Longitude geográfica em graus decimais (ou `null`).
- `precisao`: `"rua"`, `"bairro"` ou `"sem_coordenada"`.
- `fonte`: `"OpenStreetMap/Nominatim"`.
- `consulta`: A string textual exata submetida ao Nominatim.

---

## 5. Instruções para o Claude

1. O arquivo `problemas_mapa.json` já está gravado em `dados/consolidado/problemas_mapa.json`.
2. Para o desenho da **camada vermelha**:
   - Renderizar no mapa Leaflet os 135 pontos com coordenadas válidas.
   - Pontos com `precisao == "rua"`: exibir com marcador ou círculo vermelho sólido ("endereço exato").
   - Pontos com `precisao == "bairro"`: exibir com estilo diferenciado (ex.: círculo translúcido ou tracejado) com o selo *"Posição aproximada (bairro)"*.
   - No popup de cada ponto, apresentar: Nome da rua, bairro, tema, quantidade de proposições, número de vereadores que cobraram, intervalo de datas e links diretos para os processos no SICAM.
   - Adicionar controle de camadas no mapa permitindo alternar ou filtrar a camada vermelha de problemas recorrentes.

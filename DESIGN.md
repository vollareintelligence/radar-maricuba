# DESIGN.md — Radar da Gastança · Maricúba

> Fonte única de verdade visual e responsiva, construída segundo os padrões de **`taste-design`** (`google-labs-code/stitch-skills`) adaptados para jornalismo de dados cívico em **PC e dispositivos móveis**.

---

## 1. Atmosfera Visual & Direção Editorial

- **Conceito:** *Cartaz Cívico Editorial* — inspirado em jornalismo investigativo impresso e portais de dados abertos (como *Nexo* e *The Pudding*). Sério, direto, imparcial e imediatamente escaneável.
- **Espectro `taste-design`:**
  - **Densidade:** `6/10` (*Equilibrado para dados*) — denso o suficiente para mostrar números reais sem desperdício, com respiro claro entre blocos.
  - **Variância:** `6/10` (*Assimétrico controlado*) — Hero em 2 colunas assimétricas no PC, alternância de faixas claras (`Papel`) e escuras (`Tinta`), evitando a monotonia de cards idênticos repetidos.
  - **Movimento:** `4/10` (*CSS fluido e sóbrio*) — transições rápidas de `150ms–220ms` exclusivamente em `transform`, `opacity` e `background-color`, respeitando `prefers-reduced-motion: reduce`.

---

## 2. Calibração de Cores

Paleta única quente e neutra de alto contraste (WCAG AA/AAA). **Nunca usar `#000000` puro** nem degradês neon.

| Nome | Hex | Papel Funcional |
|---|---|---|
| **Papel Jornal** (`--paper`) | `#F1E8D6` | Fundo principal da página (reduz fadiga em leitura longa) |
| **Papel Claro** (`--card`) | `#FBF6EA` | Superfície de cards, tabelas e fichas de vereadores |
| **Areia** (`--muted`) | `#E3D8C0` | Cabeçalhos de tabela, trilhas de barras e estados neutros |
| **Tinta** (`--ink`) | `#111111` | Texto principal, bordas estruturais, header e faixas de contraste |
| **Tinta Suave** (`--muted-fg`) | `#4A4338` | Legendas, metadados, subtítulos e créditos de fonte |
| **Vermelho Cartaz** (`--hot`) | `#D93A1E` | Acento único: destaques gráficos, alertas, sombras de ênfase |
| **Vermelho Texto** (`--hot-text`) | `#B72E14` | Links e números de alerta sobre fundos claros (contraste reforçado) |
| **Coral Claro** (`--hot-soft`) | `#FFB199` | Links sobre fundos escuros (`Tinta`) |
| **Verde Cívico** (`--good`) | `#1F7A4D` | Uso estritamente semântico (pódio eficiente, obras concluídas) |

---

## 3. Arquitetura Tipográfica

Fontes **self-hosted** em `site/fonts/` (carregamento instantâneo em 4G, zero dependência externa):

- **Display / Manchetes:** `Anton` — caixa alta, entrelinha justa (`0.92` a `1.0`), escala fluida via `clamp()`.
- **Corpo / Interface:** `Atkinson Hyperlegible` (400 e 700) — criada pelo Braille Institute para máxima diferenciação de caracteres e algarismos.
  - Tamanho base: `17px` no PC, `16px` no mobile.
  - Largura máxima de leitura em parágrafos: `62ch–68ch`.
- **Números e Tabelas:** `font-variant-numeric: tabular-nums` obrigatório em contadores, rankings, placares, porcentagens e valores em R\$.
- **Fórmulas / Código:** pilha monospace nativa (`ui-monospace, Menlo, Consolas, monospace`).

---

## 4. Layout & Ritmo Visual

- **Container:** `max-width: 1160px`, padding lateral fluido (`clamp(16px, 3vw, 28px)`).
- **Header (Sticky):**
  - **PC:** linha única com marca à esquerda e **7 seções principais** (`Gastômetro`, `Vereadores`, `Placar`, `Prefeitura`, `Promessas`, `Empresas`, `Obras`) sem quebra de linha, com indicador visual de seção ativa.
  - **Mobile (`<= 860px`):** barra compacta fixa com botão `Menu` (`min-height: 44px`) que abre gaveta vertical clara com todas as seções.
- **Hero Assimétrico:**
  - **PC (`>= 860px`):** grid `minmax(0, 1.25fr) minmax(300px, 0.85fr)` — à esquerda, kicker, manchete em `Anton`, resumo de escopo e **1 CTA primário** (`Ver o Gastômetro`) + link secundário discreto (`Como lemos os dados`); à direita, painel escuro de impacto com o **total pago pela Prefeitura**, data oficial de atualização e selo de imparcialidade.
  - **Mobile (`< 860px`):** colapsa para 1 coluna mantendo o total pago visível logo abaixo da manchete, acompanhado pelos atalhos rápidos em grade `2x2` e o botão principal de compartilhamento no WhatsApp.
- **Hierarquia de Superfícies (sem poluição de sombras):**
  - **Sombra dura offset** (`5px 5px 0 var(--hot)` ou `4px 4px 0 var(--ink)`) reservada a elementos de destaque: Painel do Hero, KPIs de resumo (`.stat`), contadores do Gastômetro (`.gc`) e Pódio.
  - **Cards de dados densos** (rankings, tabelas, listas, filtros): borda limpa `2px solid var(--ink)` sem sombra pesada, usando divisores finos e espaço negativo.
  - **Unificação total:** `border-radius: 0` em toda a interface do Tema Cartaz (incluindo Promessas, Natal, Empresas, Tabelas e Modal de ficha), mantendo círculos apenas para avatares/fotos e marcadores semânticos de mapa.

---

## 5. Regras Responsivas (PC + Mobile)

1. **Zero overflow horizontal** em qualquer viewport (`320px` até `1920px+`). Tabelas largas sempre dentro de `.tscroll`.
2. **Alvos de toque mínimos de `44x44px`** em todos os botões, filtros, inputs, `<summary>` e links de navegação.
3. **Colapso limpo abaixo de `768px`:** grades multi-colunas passam a 1 coluna (exceto a grade de KPIs `.stats` e `.atalhos`, que usam 2 colunas equilibradas no mobile e 1 coluna abaixo de `360px`).
4. **Pódio do Mês no mobile:** preserva o layout compacto 2-1-3 (rosto, nome, nota e botão *Ver os dados*), garantindo leitura sem apertar texto.
5. **Mapa de Obras:** lado a lado com a lista no PC (`1.3fr 0.7fr`); empilhado no mobile com dica de gesto com dois dedos.

---

## 6. Anti-Padrões Proibidos

- Sem `Inter`, sem serifas genéricas (`Times New Roman`, `Georgia`).
- Sem `#000000` puro, sem brilhos neon, sem gradientes roxo/azul de IA.
- Sem misturar cantos arredondados (`12px`) com o estilo editorial reto do Tema Cartaz.
- Sem textos vazios ("Role para explorar", "Descubra mais") ou métricas inventadas — todo número tem fonte oficial.
- Sem animar `top`/`left`/`width`/`height` — apenas `transform` e `opacity`.

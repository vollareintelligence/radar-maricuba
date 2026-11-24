# Ativação do Cidadão Fiscalizador (Supabase — 2 minutos)

O módulo **Cidadão Fiscalizador** já está pronto no site (`site/index.html`) e no painel de moderação (`site/moderar.html`). Para ativá-lo gratuitamente:

## Passo 1 — Criar projeto gratuito no Supabase
1. Acesse [supabase.com](https://supabase.com) e crie um projeto gratuito (ex.: `lupa-marica`, região *South America — São Paulo*).
2. No menu lateral, abra **SQL Editor → New query**.
3. Copie todo o conteúdo de `supabase/schema.sql`, cole lá e clique em **Run**.

## Passo 2 — Criar seu login de administrador (para moderar)
1. No menu lateral do Supabase, vá em **Authentication → Users → Add user → Create new user**.
2. Crie o e-mail e senha de quem vai moderar os relatos (ex.: você e o Sargento Simões).
   - **Dica de segurança:** em **Authentication → Sign In / Providers → Email**, desative *Allow new users to sign up* (assim ninguém de fora consegue criar conta de admin).

## Passo 3 — Conectar o site ao Supabase
1. No Supabase, vá em **Project Settings → API**.
2. Copie a **Project URL** e a chave pública **`anon` / `publishable`**.
3. Cole os dois valores em `site/cidadao-config.js` e faça commit/push na branch `Designer-Eleitoral`:
   ```js
   window.LUPA_CIDADAO_CFG = {
     SUPABASE_URL: "https://SEU-PROJETO.supabase.co",
     SUPABASE_ANON_KEY: "SUA-CHAVE-ANON-AQUI"
   };
   ```

## Como usar no dia a dia
- **Moradores:** enviam relatos (anônimos ou identificados) com foto e local direto em `https://lupamarica.com/#cidadao`.
- **Moderação (você e o Sargento Simões):** acessem `https://lupamarica.com/moderar.html`, façam login com o e-mail/senha criados no Passo 2, vejam os relatos pendentes (incluindo dados privados do denunciante e link para o Google Maps), aprovem com 1 clique e atualizem o status (*Em andamento*, *Resolvido*, *Resposta da Prefeitura* ou *Atuação de Vereador*).

> **Privacidade garantida por RLS:** a tabela `relatos_privados` (nome e WhatsApp do denunciante) tem leitura pública **100% bloqueada no banco de dados**. Além disso, todas as fotos passam por recompressão em `<canvas>` no navegador antes do upload, removendo metadados EXIF do celular.

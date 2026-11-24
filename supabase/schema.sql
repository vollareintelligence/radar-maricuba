-- =====================================================================
-- LUPA MARICÁ — CIDADÃO FISCALIZADOR (Schema + RLS + Storage)
-- Execute este arquivo inteiro no SQL Editor do seu projeto Supabase.
-- =====================================================================

-- 1. Tabela pública de relatos (exibe no portal somente status aprovados)
create table if not exists public.relatos (
  id bigint generated always as identity primary key,
  protocolo text generated always as ('LM-' || lpad(id::text, 4, '0')) stored,
  created_at timestamptz not null default now(),
  atualizado_em timestamptz not null default now(),
  categoria text not null,
  titulo text not null,
  bairro text not null,
  local_referencia text not null,
  descricao text not null,
  lat double precision,
  lng double precision,
  foto_url text,
  status text not null default 'pendente'
    check (status in ('pendente', 'aprovado', 'andamento', 'resolvido', 'rejeitado')),
  resposta_prefeitura text,
  atuacao_vereador text,
  foto_depois_url text
);

-- 2. Tabela PRIVADA de dados do denunciante (NUNCA acessível ao público)
create table if not exists public.relatos_privados (
  relato_id bigint primary key references public.relatos(id) on delete cascade,
  created_at timestamptz not null default now(),
  anonimo boolean not null default true,
  nome_denunciante text,
  contato_denunciante text
);

-- 3. Ativar Row Level Security (RLS) nas duas tabelas
alter table public.relatos enable row level security;
alter table public.relatos_privados enable row level security;

-- Políticas de leitura pública (apenas relatos aprovados/em andamento/resolvidos)
drop policy if exists "public_select_aprovados" on public.relatos;
create policy "public_select_aprovados"
  on public.relatos
  for select
  to anon
  using (status in ('aprovado', 'andamento', 'resolvido'));

-- Administradores autenticados podem ver, moderar e atualizar tudo
drop policy if exists "admin_all_relatos" on public.relatos;
create policy "admin_all_relatos"
  on public.relatos
  for all
  to authenticated
  using (true)
  with check (true);

-- Tabela privada: ZERO acesso para anon; acesso exclusivo para admins logados
drop policy if exists "admin_all_relatos_privados" on public.relatos_privados;
create policy "admin_all_relatos_privados"
  on public.relatos_privados
  for all
  to authenticated
  using (true)
  with check (true);

-- 4. Função segura (RPC) para envio público de relatos
-- Força status='pendente', isola dados pessoais e devolve apenas o protocolo.
create or replace function public.enviar_relato(
  p_categoria text,
  p_titulo text,
  p_bairro text,
  p_local_referencia text,
  p_descricao text,
  p_lat double precision default null,
  p_lng double precision default null,
  p_foto_url text default null,
  p_anonimo boolean default true,
  p_nome_denunciante text default null,
  p_contato_denunciante text default null
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  v_id bigint;
  v_protocolo text;
begin
  if length(trim(coalesce(p_titulo, ''))) < 4 then
    raise exception 'Informe um título claro para o problema.';
  end if;
  if length(trim(coalesce(p_bairro, ''))) < 2 or length(trim(coalesce(p_local_referencia, ''))) < 3 then
    raise exception 'Informe o bairro e a rua ou local do problema.';
  end if;
  if length(trim(coalesce(p_descricao, ''))) < 10 then
    raise exception 'Descreva o problema com pelo menos 10 caracteres.';
  end if;

  insert into public.relatos (
    categoria, titulo, bairro, local_referencia, descricao,
    lat, lng, foto_url, status
  ) values (
    left(trim(p_categoria), 60),
    left(trim(p_titulo), 120),
    left(trim(p_bairro), 80),
    left(trim(p_local_referencia), 160),
    left(trim(p_descricao), 1200),
    p_lat,
    p_lng,
    case when p_foto_url is not null and p_foto_url like 'https://%' then left(p_foto_url, 500) else null end,
    'pendente'
  )
  returning id, protocolo into v_id, v_protocolo;

  insert into public.relatos_privados (
    relato_id, anonimo, nome_denunciante, contato_denunciante
  ) values (
    v_id,
    coalesce(p_anonimo, true),
    case when coalesce(p_anonimo, true) then null else nullif(left(trim(coalesce(p_nome_denunciante, '')), 120), '') end,
    case when coalesce(p_anonimo, true) then null else nullif(left(trim(coalesce(p_contato_denunciante, '')), 60), '') end
  );

  return jsonb_build_object('protocolo', v_protocolo);
end;
$$;

grant execute on function public.enviar_relato(
  text, text, text, text, text, double precision, double precision, text, boolean, text, text
) to anon, authenticated;

-- 5. Bucket de fotos no Supabase Storage
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'fotos-relatos',
  'fotos-relatos',
  true,
  5242880,
  array['image/jpeg', 'image/png', 'image/webp']
)
on conflict (id) do nothing;

-- Permitir leitura pública das fotos e upload apenas de imagens para o bucket fotos-relatos
drop policy if exists "public_read_fotos_relatos" on storage.objects;
create policy "public_read_fotos_relatos"
  on storage.objects
  for select
  to anon, authenticated
  using (bucket_id = 'fotos-relatos');

drop policy if exists "public_upload_fotos_relatos" on storage.objects;
create policy "public_upload_fotos_relatos"
  on storage.objects
  for insert
  to anon, authenticated
  with check (bucket_id = 'fotos-relatos');

drop policy if exists "admin_delete_fotos_relatos" on storage.objects;
create policy "admin_delete_fotos_relatos"
  on storage.objects
  for delete
  to authenticated
  using (bucket_id = 'fotos-relatos');

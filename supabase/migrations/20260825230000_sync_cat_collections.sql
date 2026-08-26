-- Conserva la colección gatuna por cuenta para restaurarla al iniciar sesión
-- en otra PC. Cada usuario sólo puede leer y actualizar su propia fila.
create table if not exists public.cat_collection_states (
  user_id uuid primary key references auth.users(id) on delete cascade,
  state jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now(),
  constraint cat_collection_states_state_is_object
    check (jsonb_typeof(state) = 'object')
);

comment on table public.cat_collection_states is
  'Private per-user Xomacito cat collection state used for cross-device restore.';

alter table public.cat_collection_states enable row level security;

create policy "Users can read their own cat collection"
on public.cat_collection_states
for select
to authenticated
using ((select auth.uid()) = user_id);

create policy "Users can create their own cat collection"
on public.cat_collection_states
for insert
to authenticated
with check ((select auth.uid()) = user_id);

create policy "Users can update their own cat collection"
on public.cat_collection_states
for update
to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

revoke all on table public.cat_collection_states from anon;
grant select, insert, update on table public.cat_collection_states to authenticated;

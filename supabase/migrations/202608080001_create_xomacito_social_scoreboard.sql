-- Backend social de Xomacito: identidad, marcador público y progreso.
-- La contraseña se administra exclusivamente mediante Supabase Auth.

create table if not exists public.profiles (
    id uuid primary key references auth.users(id) on delete cascade,
    username text not null unique,
    downloads_count bigint not null default 0 check (downloads_count >= 0),
    cats_count integer not null default 0 check (cats_count >= 0),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint profiles_username_format
        check (username ~ '^[a-z0-9][a-z0-9._-]{2,31}$')
);

create index if not exists profiles_leaderboard_idx
    on public.profiles (downloads_count desc, cats_count desc, username);

alter table public.profiles enable row level security;

drop policy if exists scoreboard_is_publicly_readable on public.profiles;
create policy scoreboard_is_publicly_readable
    on public.profiles
    for select
    to anon, authenticated
    using (true);

create or replace function public.create_xomacito_profile()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
    requested_username text;
begin
    requested_username := lower(trim(coalesce(new.raw_user_meta_data ->> 'username', '')));

    if requested_username !~ '^[a-z0-9][a-z0-9._-]{2,31}$' then
        raise exception 'La ID de Xomacito no tiene un formato valido.';
    end if;

    insert into public.profiles (id, username)
    values (new.id, requested_username);
    return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
    after insert on auth.users
    for each row execute function public.create_xomacito_profile();

-- El argumento se conserva por compatibilidad con el cliente, pero una llamada
-- autenticada siempre vale exactamente una descarga (también para una cola).
create or replace function public.increment_downloads(delta integer default 1)
returns void
language plpgsql
security definer
set search_path = ''
as $$
begin
    if (select auth.uid()) is null then
        raise exception 'Authentication required';
    end if;

    update public.profiles
    set downloads_count = downloads_count + 1,
        updated_at = now()
    where id = (select auth.uid());

    if not found then
        raise exception 'Profile not found';
    end if;
end;
$$;

create or replace function public.set_cat_count(value integer)
returns void
language plpgsql
security definer
set search_path = ''
as $$
begin
    if (select auth.uid()) is null then
        raise exception 'Authentication required';
    end if;

    update public.profiles
    set cats_count = greatest(
            cats_count,
            least(greatest(coalesce(value, 0), 0), 10000)
        ),
        updated_at = now()
    where id = (select auth.uid());

    if not found then
        raise exception 'Profile not found';
    end if;
end;
$$;

revoke insert, update, delete on table public.profiles from anon, authenticated;
grant select on table public.profiles to anon, authenticated;

revoke all on function public.create_xomacito_profile() from public, anon, authenticated;
revoke all on function public.increment_downloads(integer) from public, anon;
revoke all on function public.set_cat_count(integer) from public, anon;
grant execute on function public.increment_downloads(integer) to authenticated;
grant execute on function public.set_cat_count(integer) to authenticated;

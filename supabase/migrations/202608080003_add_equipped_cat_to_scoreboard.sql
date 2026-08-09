alter table public.profiles
    add column if not exists equipped_cat_id text not null default '';

create or replace function public.set_equipped_cat(value text)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
    actor uuid := (select auth.uid());
begin
    if actor is null then
        raise exception 'authentication required';
    end if;

    update public.profiles
    set equipped_cat_id = left(coalesce(value, ''), 80),
        updated_at = now()
    where id = actor;
end;
$$;

drop function if exists public.get_xomacito_leaderboard();

create or replace function public.get_xomacito_leaderboard()
returns table (
    username text,
    downloads_count bigint,
    cats_count integer,
    streak_days integer,
    best_streak integer,
    active_today boolean,
    equipped_cat_id text
)
language sql
stable
security definer
set search_path = ''
as $$
    select
        p.username,
        p.downloads_count,
        p.cats_count,
        coalesce(a.streak_days, 0),
        coalesce(a.best_streak, 0),
        coalesce(a.last_active_on = current_date, false),
        p.equipped_cat_id
    from public.profiles as p
    left join public.profile_activity as a on a.id = p.id
    order by p.downloads_count desc, p.cats_count desc, p.username asc
    limit 100;
$$;

revoke all on function public.set_equipped_cat(text) from public, anon, authenticated;
revoke all on function public.get_xomacito_leaderboard() from public, anon, authenticated;
grant execute on function public.set_equipped_cat(text) to authenticated;
grant execute on function public.get_xomacito_leaderboard() to anon, authenticated;

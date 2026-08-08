create table if not exists public.profile_activity (
    id uuid primary key references public.profiles(id) on delete cascade,
    streak_days integer not null default 0 check (streak_days >= 0),
    best_streak integer not null default 0 check (best_streak >= 0),
    last_active_on date not null default current_date
);

alter table public.profile_activity enable row level security;
revoke all on table public.profile_activity from anon, authenticated;

create or replace function public.record_daily_activity()
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

    insert into public.profile_activity (id, streak_days, best_streak, last_active_on)
    values (actor, 1, 1, current_date)
    on conflict (id) do update
    set streak_days = case
            when public.profile_activity.last_active_on = current_date
                then public.profile_activity.streak_days
            when public.profile_activity.last_active_on = current_date - 1
                then public.profile_activity.streak_days + 1
            else 1
        end,
        best_streak = greatest(
            public.profile_activity.best_streak,
            case
                when public.profile_activity.last_active_on = current_date
                    then public.profile_activity.streak_days
                when public.profile_activity.last_active_on = current_date - 1
                    then public.profile_activity.streak_days + 1
                else 1
            end
        ),
        last_active_on = current_date;
end;
$$;

create or replace function public.get_xomacito_leaderboard()
returns table (
    username text,
    downloads_count bigint,
    cats_count integer,
    streak_days integer,
    best_streak integer,
    active_today boolean
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
        coalesce(a.last_active_on = current_date, false)
    from public.profiles as p
    left join public.profile_activity as a on a.id = p.id
    order by p.downloads_count desc, p.cats_count desc, p.username asc
    limit 100;
$$;

revoke all on function public.record_daily_activity() from public, anon, authenticated;
revoke all on function public.get_xomacito_leaderboard() from public, anon, authenticated;
grant execute on function public.record_daily_activity() to authenticated;
grant execute on function public.get_xomacito_leaderboard() to anon, authenticated;

create schema if not exists private;

revoke all on schema private from public;

create table if not exists private.email_signup_rewards (
  user_id uuid primary key references auth.users (id) on delete cascade,
  claimed_at timestamptz not null default now()
);

alter table private.email_signup_rewards enable row level security;
revoke all on table private.email_signup_rewards from public, anon, authenticated;

create or replace function public.claim_email_signup_bonus()
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  actor uuid := (select auth.uid());
  account_email text;
  account_confirmed_at timestamptz;
  inserted_rows integer := 0;
begin
  if actor is null then
    return false;
  end if;

  select lower(u.email), u.email_confirmed_at
    into account_email, account_confirmed_at
    from auth.users as u
   where u.id = actor;

  if account_email is null
     or account_confirmed_at is null
     or account_email like '%@rvtoyahqxpduhrwemfyv.supabase.co' then
    return false;
  end if;

  insert into private.email_signup_rewards (user_id)
  values (actor)
  on conflict (user_id) do nothing;

  get diagnostics inserted_rows = row_count;
  return inserted_rows = 1;
end;
$$;

revoke all on function public.claim_email_signup_bonus() from public, anon;
grant execute on function public.claim_email_signup_bonus() to authenticated;

comment on function public.claim_email_signup_bonus() is
  'Claims Xomacito email signup rolls once for the authenticated non-legacy account.';

create schema if not exists private;

revoke all on schema private from public;

create table if not exists private.account_roll_gifts (
  user_id uuid not null references auth.users (id) on delete cascade,
  campaign text not null,
  rolls_granted integer not null,
  created_at timestamptz not null default now(),
  claimed_at timestamptz,
  primary key (user_id, campaign),
  constraint account_roll_gifts_campaign_not_blank check (btrim(campaign) <> ''),
  constraint account_roll_gifts_amount_valid check (rolls_granted between 1 and 1000)
);

create index if not exists account_roll_gifts_pending_user_idx
  on private.account_roll_gifts (user_id)
  where claimed_at is null;

alter table private.account_roll_gifts enable row level security;
revoke all on table private.account_roll_gifts from public, anon, authenticated;

create or replace function public.claim_account_roll_gifts()
returns integer
language plpgsql
security definer
set search_path = ''
as $$
declare
  actor uuid := (select auth.uid());
  awarded integer := 0;
begin
  if actor is null then
    return 0;
  end if;

  with claimed as (
    update private.account_roll_gifts
       set claimed_at = now()
     where user_id = actor
       and claimed_at is null
    returning rolls_granted
  )
  select coalesce(sum(rolls_granted), 0)::integer
    into awarded
    from claimed;

  return awarded;
end;
$$;

revoke all on function public.claim_account_roll_gifts() from public, anon;
grant execute on function public.claim_account_roll_gifts() to authenticated;

comment on function public.claim_account_roll_gifts() is
  'Atomically claims pending creator-authorized rolls for the authenticated Xomacito account.';

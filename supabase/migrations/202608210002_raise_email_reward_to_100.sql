alter table private.email_signup_rewards
  add column if not exists rolls_awarded integer not null default 10;

alter table private.email_signup_rewards
  drop constraint if exists email_signup_rewards_rolls_awarded_check;

alter table private.email_signup_rewards
  add constraint email_signup_rewards_rolls_awarded_check
  check (rolls_awarded between 0 and 100);

update private.email_signup_rewards
   set rolls_awarded = 10
 where rolls_awarded < 10;

create or replace function public.claim_email_roll_reward()
returns integer
language plpgsql
security definer
set search_path = ''
as $$
declare
  actor uuid := (select auth.uid());
  account_email text;
  account_confirmed_at timestamptz;
  already_awarded integer := 0;
  target_reward constant integer := 100;
begin
  if actor is null then
    return 0;
  end if;

  select lower(u.email), u.email_confirmed_at
    into account_email, account_confirmed_at
    from auth.users as u
   where u.id = actor;

  if account_email is null
     or account_confirmed_at is null
     or account_email like '%@rvtoyahqxpduhrwemfyv.supabase.co' then
    return 0;
  end if;

  insert into private.email_signup_rewards (user_id, rolls_awarded)
  values (actor, 0)
  on conflict (user_id) do nothing;

  select r.rolls_awarded
    into already_awarded
    from private.email_signup_rewards as r
   where r.user_id = actor
   for update;

  if already_awarded >= target_reward then
    return 0;
  end if;

  update private.email_signup_rewards
     set rolls_awarded = target_reward,
         claimed_at = now()
   where user_id = actor;

  return target_reward - already_awarded;
end;
$$;

revoke all on function public.claim_email_roll_reward() from public, anon;
grant execute on function public.claim_email_roll_reward() to authenticated;

comment on function public.claim_email_roll_reward() is
  'Returns the unclaimed portion of Xomacito''s 100-roll verified-email reward.';

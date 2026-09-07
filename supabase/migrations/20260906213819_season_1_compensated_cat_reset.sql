-- One-time season transition. Keep full pre-transition account snapshots private.
create schema if not exists xomacito_private;
revoke all on schema xomacito_private from public, anon, authenticated;
create table if not exists xomacito_private.season_resets (
  user_id uuid primary key references auth.users(id) on delete cascade,
  previous_profile jsonb not null, previous_state jsonb,
  credit_cents bigint, applied_at timestamptz,
  created_at timestamptz not null default now()
);
alter table xomacito_private.season_resets enable row level security;
create table if not exists xomacito_private.cat_prices (
  cat_id text primary key, price_cents integer not null check(price_cents > 0)
);
alter table xomacito_private.cat_prices enable row level security;
insert into xomacito_private.cat_prices(cat_id,price_cents) values
('cat-cf837ae651c8',3411),
('cat-6f08664122e1',3271),
('cat-3fbb2a6fdb2e',3178),
('cat-3645f4659a5e',3181),
('cat-40eaa59f7dbf',3143),
('cat-b065d39c3af3',732),
('cat-0ca9c525ec8d',955),
('cat-796d8a90b763',950),
('cat-93931df03c55',841),
('cat-5f139ff978a3',960),
('cat-e78cf17a3656',603),
('cat-916179ba1e97',926),
('cat-da442533a1b0',969),
('cat-faffbe771c61',734),
('cat-5a99d9f019f0',617),
('cat-4003245df557',770),
('cat-3a59baa03982',379),
('cat-8f0749e297d8',206),
('cat-1c4f9080cb04',233),
('cat-94e6a7c08f4e',297),
('cat-1408c919b204',397),
('cat-acd399dccfe9',282),
('cat-f6fd6c7f4318',335),
('cat-a09cea027523',221),
('cat-54df6df04d00',272),
('cat-ab38e4323df4',121),
('cat-f9b340e15c37',130),
('cat-25c9c2d55dd1',99),
('cat-764d3e67c4d6',94),
('cat-c3e5d849aaf1',84),
('cat-95b401288e51',94),
('cat-9d019a170598',112),
('cat-41f56f0e849e',134),
('cat-2a7f6a7fc801',80),
('cat-65e243565280',132),
('cat-c6737f642f05',84),
('cat-b4368fa41edb',87),
('cat-70d051e3cdc3',110),
('cat-f539dc1c2b24',119),
('cat-6b2b2b73966b',71),
('cat-84d0a01fd6de',103),
('cat-9d5d7cc2731c',74),
('cat-bfadb104aeaa',112),
('cat-59b9b1997b94',125),
('cat-c312687abd1b',138),
('cat-909e10bb0d1b',77),
('cat-f725c47d70ae',110),
('cat-b5033e4ca089',128),
('cat-1b188fd7e0a3',72),
('cat-910f73deffc0',78),
('cat-4f069cb4aa3f',139),
('cat-5c74482dca4d',115),
('cat-4096337af0df',105),
('cat-cce7d93737ac',50),
('cat-57baf2530327',38),
('cat-5f11d37275bf',52),
('cat-dd7073c137d7',55),
('cat-03ffd51c1f63',52),
('cat-78c9e93978da',44),
('cat-3bbfd30f2821',43),
('cat-e616ff52f30d',54),
('cat-723238baff93',43),
('cat-56f95ffd8ed1',48),
('cat-80ff7f4dbd91',49),
('cat-6f9d314cd2cb',51),
('cat-7d3be7698746',53),
('cat-7bfb02f5b4c6',44),
('cat-f4a6e039841a',48),
('cat-def791a58c21',33),
('cat-8631d5430d04',46),
('cat-d528a357f667',32),
('cat-b8334df9028f',46),
('cat-d26a33f78978',32),
('cat-572e6e78723b',49),
('cat-19624f7d5233',41),
('cat-ce156c4411b8',40),
('cat-09c91bf94ae4',47),
('cat-5ddb51d21f15',43),
('cat-655d97e229cb',30),
('cat-3816f4a936b7',41),
('cat-a0958da00076',45),
('cat-97575d0c8d17',40),
('cat-1b6b82ae401e',30),
('cat-677dcb11e5bb',54),
('cat-6c167b2e632b',55),
('cat-1dc2bdb2779c',37),
('cat-0ac1969ab0b0',43),
('cat-4d893d57c779',53),
('cat-f7af68ca6e04',44),
('cat-f539cf60cd72',22),
('cat-17f068fe4e01',16),
('cat-e18ba4039d39',23),
('cat-9f7b93d87f0d',25),
('cat-c1e5dd4260b1',18),
('cat-1d8b7b31ead0',23),
('cat-d3b872881f51',15),
('cat-ece5e967a836',16),
('cat-a8f9ddf5d9a7',11),
('cat-3d288e090f04',10),
('cat-a91d7b555e03',13),
('cat-2668bdeb0608',17),
('cat-f02b5c872ce8',16),
('cat-919f833c9054',18),
('cat-915602b2df5f',21),
('cat-1f6a613f8243',11),
('cat-9c7df073821e',24),
('cat-a00a4762aa72',19),
('cat-1c99dd7b1cc2',22),
('cat-855a784bd141',14),
('cat-1683d765c66e',10),
('cat-5ac99bc29562',19),
('cat-e6001e26a0ed',18),
('cat-b2b307b99018',21),
('cat-855f675ac835',25),
('cat-3ac7e2fe6f9e',24),
('cat-5b9212e22df6',23),
('cat-14d209067d6e',21),
('cat-2c2050908762',17),
('cat-4cb098b7addc',25),
('cat-c041e1f0ab5a',24),
('cat-ab6bd6dc66a2',22),
('cat-05be9be9ca2d',23),
('cat-80c746c7529e',22),
('cat-7894c6dff168',14),
('cat-39018fb703a2',19),
('cat-412378ffef6b',19),
('cat-b2df823bc8cf',14),
('cat-8f36e3336c8c',21),
('cat-163a222a5760',20),
('cat-c137fdca8b96',22),
('cat-d143a1578eb7',17),
('cat-d0855234cdbc',22),
('cat-e616d3a36866',12),
('cat-1ae45b559307',12),
('cat-e71e6d2cc7b3',19),
('cat-8f255261a642',24),
('cat-588080687be2',18),
('cat-a975dba8b1f1',14),
('cat-1d8fb0659fdf',18),
('cat-35c428c969e2',13),
('cat-0c760aa0f614',23),
('cat-cbf39f5eeb76',10),
('cat-cf85e6539348',13),
('cat-beef2bab6955',20),
('cat-a1b5f048a7cb',20),
('cat-beb53e5431d3',21),
('cat-9862a14577c1',11),
('cat-7ac6febcca46',21),
('cat-2ef4a682126f',17),
('cat-65d78402fdcf',22)
on conflict(cat_id) do update set price_cents=excluded.price_cents;

create or replace function xomacito_private.reset_cat_economy(s jsonb)
returns jsonb language plpgsql security invoker set search_path = '' as $$
declare
  inv jsonb; zeros jsonb; sold jsonb; credit bigint; cash bigint;
begin
  if coalesce((s->>'economyEpoch')::int,0) >= 1 then return s; end if;
  if s ? 'walletCents' and jsonb_typeof(s->'inventory') = 'object' then
    inv := s->'inventory'; cash := greatest(0,coalesce((s->>'walletCents')::bigint,0));
  else
    select coalesce(jsonb_object_agg(k, 1 + greatest(0,coalesce((s->'duplicates'->>k)::bigint,0))), '{}')
    into inv from (select distinct jsonb_array_elements_text(coalesce(s->'unlockedIds','[]')) as k) ids;
    cash := greatest(0,coalesce((s->>'earnedRolls')::bigint,0)) * 100;
  end if;
  if exists(select 1 from jsonb_each_text(inv) i left join xomacito_private.cat_prices p on p.cat_id=i.key where i.value::bigint > 0 and p.cat_id is null) then
    raise exception 'Unknown cat in pre-season inventory: compensation requires catalogue review';
  end if;
  select coalesce(sum(p.price_cents * greatest(0,i.value::bigint)),0),
         coalesce(jsonb_object_agg(i.key,i.value::bigint) filter(where i.value::bigint > 0),'{}')
  into credit,sold from jsonb_each_text(inv) i join xomacito_private.cat_prices p on p.cat_id=i.key;
  select jsonb_object_agg(cat_id,0) into zeros from xomacito_private.cat_prices;
  return s || jsonb_build_object('schema',7,'economyEpoch',1,'resetCreditCents',credit,
    'liquidatedInventory',sold,'walletCents',cash+credit,
    'inventory',zeros || jsonb_build_object('cat-c3e5d849aaf1',1), 'equippedId','cat-c3e5d849aaf1',
    'economyRevision',greatest(0,coalesce((s->>'economyRevision')::bigint,
      (s->>'rollBalanceRevision')::bigint,0))+1,'economyUpdatedAt',0);
end $$;
revoke all on function xomacito_private.reset_cat_economy(jsonb) from public,anon,authenticated;

insert into xomacito_private.season_resets(user_id,previous_profile,previous_state)
select p.id,to_jsonb(p),c.state from public.profiles p left join public.cat_collection_states c on c.user_id=p.id
on conflict(user_id) do nothing;
alter table public.profiles add column if not exists season_downloads_baseline bigint not null default 0;
update public.profiles p set season_downloads_baseline=(r.previous_profile->>'downloads_count')::bigint
from xomacito_private.season_resets r where r.user_id=p.id;

-- A legacy application cannot overwrite an already compensated collection.
create or replace function xomacito_private.guard_cat_season()
returns trigger language plpgsql security definer set search_path = '' as $$
declare incoming jsonb := new.state;
begin
  if (select auth.uid()) is not null and (select auth.uid()) <> new.user_id then
    raise exception 'Account mismatch';
  end if;
  if tg_op='UPDATE' and coalesce((old.state->>'economyEpoch')::int,0)>=1 then
    if coalesce((incoming->>'economyEpoch')::int,0)<1 then
      new.state := old.state; return new;
    end if;
    -- Receipts are immutable, including when ordinary gameplay advances the wallet.
    new.state := incoming || jsonb_build_object('resetCreditCents',old.state->'resetCreditCents',
       'liquidatedInventory',old.state->'liquidatedInventory');
  else
    new.state := xomacito_private.reset_cat_economy(incoming);
    update xomacito_private.season_resets
    set previous_state=coalesce(previous_state,incoming),
        credit_cents=(new.state->>'resetCreditCents')::bigint, applied_at=now()
    where user_id=new.user_id and applied_at is null;
  end if;
  return new;
end $$;
revoke all on function xomacito_private.guard_cat_season() from public,anon,authenticated;
drop trigger if exists guard_cat_season on public.cat_collection_states;
create trigger guard_cat_season before insert or update on public.cat_collection_states
for each row execute function xomacito_private.guard_cat_season();
update public.cat_collection_states set state=state where coalesce((state->>'economyEpoch')::int,0)<1;

create or replace function public.set_cat_count(value integer)
returns void language plpgsql security definer set search_path = '' as $$
begin
  if (select auth.uid()) is null then raise exception 'Authentication required'; end if;
  update public.profiles p set cats_count=coalesce((select sum(greatest(0,i.value::bigint))::int
    from public.cat_collection_states c, lateral jsonb_each_text(coalesce(c.state->'inventory','{}')) i
    where c.user_id=p.id),0), updated_at=now() where p.id=(select auth.uid());
end $$;
revoke all on function public.set_cat_count(integer) from public,anon;
grant execute on function public.set_cat_count(integer) to authenticated;

create or replace function public.get_xomacito_leaderboard()
returns table(username text, downloads_count bigint, cats_count integer, streak_days integer,
 best_streak integer,active_today boolean,equipped_cat_id text)
language sql stable security definer set search_path = '' as $$
  select p.username, greatest(0,p.downloads_count-p.season_downloads_baseline),
    coalesce((select sum(greatest(0,i.value::bigint))::int
      from jsonb_each_text(coalesce(c.state->'inventory','{}')) i),0),
    coalesce(a.streak_days,0),coalesce(a.best_streak,0),
    coalesce(a.last_active_on=current_date,false),coalesce(c.state->>'equippedId','')
  from public.profiles p left join public.profile_activity a on a.id=p.id
    left join public.cat_collection_states c on c.user_id=p.id
  order by greatest(0,p.downloads_count-p.season_downloads_baseline) desc,p.username asc limit 100;
$$;
revoke all on function public.get_xomacito_leaderboard() from public;
grant execute on function public.get_xomacito_leaderboard() to anon,authenticated;
notify pgrst, 'reload schema';

-- Creator-authorized one-time gift: $30 virtual = 30 rolls of $1.
-- Fixed cutoff: registrations after this request do not receive this campaign.
insert into private.account_roll_gifts (user_id, campaign, rolls_granted)
select id, 'community-2026-10-06-virtual-30', 30
from auth.users
where created_at <= timestamptz '2026-10-06 18:40:32+00'
on conflict (user_id, campaign) do nothing;

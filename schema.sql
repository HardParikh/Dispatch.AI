-- Run this once in the Supabase SQL editor (Dashboard -> SQL Editor -> New query).
-- It creates the loads table that store.py reads and writes over HTTPS.

create table if not exists loads (
    load_id text primary key,
    origin_city text default '',
    origin_state text default '',
    dest_city text default '',
    dest_state text default '',
    weight_lbs integer default 0,
    equipment text default 'unknown',
    commodity text default '',
    pickup_date text default '',
    reference_number text default '',
    state text default 'draft',
    validation_errors jsonb default '[]'::jsonb,
    inferred_fields jsonb default '[]'::jsonb,
    actions jsonb default '[]'::jsonb,
    created_at timestamptz default now(),
    source_message text default ''
);

-- Allow the anon key to read and write for this demo.
-- For a real app you would write tighter row level security policies.
alter table loads enable row level security;

create policy "allow all for anon on loads"
    on loads
    for all
    using (true)
    with check (true);

-- If you already created the v1 loads table, run this to add the new column.
alter table loads add column if not exists agent_trace_id text default '';

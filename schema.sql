-- Jalankan ini di Supabase SQL Editor

create table reminders (
  id uuid default gen_random_uuid() primary key,
  user_number text not null,
  message text not null,
  remind_at text not null,
  repeat text default 'none',
  priority text default 'normal',
  status text default 'active',
  created_at timestamp with time zone default timezone('utc', now())
);

-- Index buat query lebih cepet
create index idx_reminders_status on reminders(status);
create index idx_reminders_remind_at on reminders(remind_at);
create index idx_reminders_user on reminders(user_number);

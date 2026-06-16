create table if not exists public.documents (
    doc_id uuid primary key,
    file_name text not null unique,
    file_path text not null,
    file_type text not null,
    upload_time timestamp without time zone not null default now(),
    status text not null default 'processing',
    chunk_count integer not null default 0,
    error_msg text,
    created_at timestamp without time zone not null default now(),
    updated_at timestamp without time zone not null default now(),
    constraint documents_status_check
        check (status in ('processing', 'completed', 'failed'))
);

create index if not exists idx_documents_status on public.documents(status);
create index if not exists idx_documents_upload_time on public.documents(upload_time desc);

create or replace function public.set_documents_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

drop trigger if exists trg_documents_updated_at on public.documents;

create trigger trg_documents_updated_at
before update on public.documents
for each row
execute function public.set_documents_updated_at();

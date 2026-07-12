-- Esquema de etapa Bronze para Supabase
-- Sirve para almacenar los datos crudos de los archivos Excel en forma de filas JSONB

create schema if not exists bronze;

create table if not exists bronze.grupos (
    id bigserial primary key,
    source_file text not null default 'grupos.xlsx',
    row_number integer not null,
    raw_data jsonb not null,
    loaded_at timestamptz not null default now(),
    unique (source_file, row_number)
);

create table if not exists bronze.solicitudes_completo (
    id bigserial primary key,
    source_file text not null default 'Solicitudes_completo_ANONIMIZADO.xlsx',
    row_number integer not null,
    raw_data jsonb not null,
    loaded_at timestamptz not null default now(),
    unique (source_file, row_number)
);

create table if not exists bronze.recepcion (
    id bigserial primary key,
    source_file text not null default 'Recepcion_ANONIMIZADO.xlsx',
    row_number integer not null,
    raw_data jsonb not null,
    loaded_at timestamptz not null default now(),
    unique (source_file, row_number)
);

create table if not exists bronze.maestro_articulos (
    id bigserial primary key,
    source_file text not null default 'Maestro_Articulos_ANONIMIZADO.xlsx',
    row_number integer not null,
    raw_data jsonb not null,
    loaded_at timestamptz not null default now(),
    unique (source_file, row_number)
);

create table if not exists bronze.proveedores (
    id bigserial primary key,
    source_file text not null default 'Proveedores_ANONIMIZADO.xlsx',
    row_number integer not null,
    raw_data jsonb not null,
    loaded_at timestamptz not null default now(),
    unique (source_file, row_number)
);

create table if not exists bronze.articulos (
    id bigserial primary key,
    source_file text not null default 'Articulos_ANONIMIZADO.xlsx',
    row_number integer not null,
    raw_data jsonb not null,
    loaded_at timestamptz not null default now(),
    unique (source_file, row_number)
);

create index if not exists idx_bronze_grupos_raw_data on bronze.grupos using gin (raw_data);
create index if not exists idx_bronze_solicitudes_raw_data on bronze.solicitudes_completo using gin (raw_data);
create index if not exists idx_bronze_recepcion_raw_data on bronze.recepcion using gin (raw_data);
create index if not exists idx_bronze_maestro_raw_data on bronze.maestro_articulos using gin (raw_data);
create index if not exists idx_bronze_proveedores_raw_data on bronze.proveedores using gin (raw_data);
create index if not exists idx_bronze_articulos_raw_data on bronze.articulos using gin (raw_data);

-- Vista simple para que se vea bien en el dashboard
create or replace view bronze.v_resumen as
select 'grupos' as tabla, count(*) as filas from bronze.grupos
union all
select 'solicitudes_completo', count(*) from bronze.solicitudes_completo
union all
select 'recepcion', count(*) from bronze.recepcion
union all
select 'maestro_articulos', count(*) from bronze.maestro_articulos
union all
select 'proveedores', count(*) from bronze.proveedores
union all
select 'articulos', count(*) from bronze.articulos;

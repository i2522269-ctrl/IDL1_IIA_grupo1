-- ============================================================
-- NORMALIZACION RELACIONAL 3FN - ESQUEMA "normalizado"
-- ============================================================
-- La capa silver quedo limpia pero con datos de catalogo repetidos
-- en las tablas de hechos (artdes, artmed, artgrinv, solpro).
-- Aca separamos dimensiones de hechos y dejamos las llaves foraneas
-- bien puestas, que para eso sufrimos la limpieza antes.

-- Hallazgos de integridad que se conservan como NULL (no se pierde data):
--   solicitudes.artcitem fuera de catalogo: 722 filas (231 artcitem distintos)
--   solicitudes.solpro fuera de proveedores: 179 filas
--   recepcion.solnum sin pedido en solicitudes: 957 filas
--   recepcion.artcitem fuera de catalogo: 1 fila
--   maestro_articulos.artgrinv sin grupo: 19 filas (9011, 9801, 9901)
--   recepcion duplicados (solnum,artcitem,nrdcac): 630 -> clave surrogate


DROP SCHEMA IF EXISTS normalizado CASCADE;
CREATE SCHEMA normalizado;

-- ============================================================
-- 1. DIMENSION: GRUPOS
-- ============================================================
CREATE TABLE normalizado.grupos (
    artgrinv TEXT PRIMARY KEY,
    nombre   TEXT NOT NULL
);

INSERT INTO normalizado.grupos (artgrinv, nombre)
SELECT artgrinv, nombre FROM silver.grupos;

-- ============================================================
-- 2. DIMENSION: PROVEEDORES
-- ============================================================
CREATE TABLE normalizado.proveedores (
    acrecodi TEXT PRIMARY KEY,
    acreraso TEXT,
    acredire TEXT,
    acretelf TEXT,
    acreciud TEXT,
    acreiden TEXT,
    acreruc  TEXT
);

INSERT INTO normalizado.proveedores (acrecodi, acreraso, acredire, acretelf, acreciud, acreiden, acreruc)
SELECT acrecodi, acreraso, acredire, acretelf, acreciud, acreiden, acreruc
FROM silver.proveedores;

-- ============================================================
-- 3. DIMENSION: MAESTRO DE ARTICULOS
-- ============================================================
CREATE TABLE normalizado.maestro_articulos (
    artcitem TEXT PRIMARY KEY,
    artdes   TEXT,
    artmed   TEXT,
    artgrinv TEXT REFERENCES normalizado.grupos (artgrinv),
    artcosu1 NUMERIC(15,2),
    artstseg INTEGER,
    artfusal DATE,
    artfuent DATE,
    artubi   TEXT,
    artcoum1 NUMERIC(15,2),
    artcmon  TEXT,
    artpreu2 NUMERIC(15,2)
);

INSERT INTO normalizado.maestro_articulos
    (artcitem, artdes, artmed, artgrinv, artcosu1, artstseg, artfusal, artfuent,
     artubi, artcoum1, artcmon, artpreu2)
SELECT m.artcitem, m.artdes, m.artmed,
       -- hay 19 articulos con grupo que no existe en el catalogo de grupos;
       -- se quedan sin grupo pero no perdemos el articulo
       (SELECT g.artgrinv FROM normalizado.grupos g WHERE g.artgrinv = m.artgrinv),
       m.artcosu1, m.artstseg, m.artfusal, m.artfuent,
       m.artubi, m.artcoum1, m.artcmon, m.artpreu2
FROM silver.maestro_articulos m;

-- ============================================================
-- 4. HECHO: SOLICITUDES
-- ============================================================
CREATE TABLE normalizado.fact_solicitudes (
    solnum  INTEGER PRIMARY KEY,
    artcitem TEXT REFERENCES normalizado.maestro_articulos (artcitem),
    soltip  TEXT,
    solcan  NUMERIC(15,2),
    solurg  TEXT,
    solusr  TEXT,
    solfec  DATE,
    solord  INTEGER,
    solmon  INTEGER,
    solpre  NUMERIC(15,2),
    solsts  TEXT,
    solsta  INTEGER,
    solpro  TEXT REFERENCES normalizado.proveedores (acrecodi)
);

INSERT INTO normalizado.fact_solicitudes
    (solnum, artcitem, soltip, solcan, solurg, solusr, solfec, solord,
     solmon, solpre, solsts, solsta, solpro)
SELECT s.solnum,
       -- los articulos que no estan en el maestro se dejan en NULL;
       -- preferimos perder el match a inventar articulos fantasma
       (SELECT m.artcitem FROM normalizado.maestro_articulos m WHERE m.artcitem = s.artcitem),
       s.soltip, s.solcan, s.solurg, s.solusr, s.solfec, s.solord,
       s.solmon, s.solpre, s.solsts, s.solsta,
       (SELECT p.acrecodi FROM normalizado.proveedores p WHERE p.acrecodi = s.solpro)
FROM silver.solicitudes s;

-- ============================================================
-- 5. HECHO: RECEPCION
-- ============================================================
-- Clave surrogate porque un mismo (solnum, artcitem, nrdcac) puede
-- aparecer varias veces (entregas parciales que se repiten).
CREATE TABLE normalizado.fact_recepcion (
    id_recepcion SERIAL PRIMARY KEY,
    solnum   INTEGER REFERENCES normalizado.fact_solicitudes (solnum),
    artcitem TEXT REFERENCES normalizado.maestro_articulos (artcitem),
    solcan   NUMERIC(15,2),
    nrdcac   NUMERIC(15,2),
    artstock NUMERIC(15,2),
    solpre   NUMERIC(15,2),
    solmon   INTEGER,
    solurg   TEXT,
    solusr   TEXT,
    nrcfec   DATE,
    solfec   DATE,
    nrcnum   INTEGER,
    solord   INTEGER,
    soltip   TEXT,
    solpro   TEXT REFERENCES normalizado.proveedores (acrecodi)
);

INSERT INTO normalizado.fact_recepcion
    (solnum, artcitem, solcan, nrdcac, artstock, solpre, solmon,
     solurg, solusr, nrcfec, solfec, nrcnum, solord, soltip, solpro)
SELECT CASE WHEN EXISTS (SELECT 1 FROM normalizado.fact_solicitudes f WHERE f.solnum = r.solnum) THEN r.solnum END,
       CASE WHEN EXISTS (SELECT 1 FROM normalizado.maestro_articulos m WHERE m.artcitem = r.artcitem) THEN r.artcitem END,
       r.solcan, r.nrdcac, r.artstock, r.solpre, r.solmon,
       r.solurg, r.solusr, r.nrcfec, r.solfec, r.nrcnum, r.solord, r.soltip, r.solpro
FROM silver.recepcion r;

-- ============================================================
-- 6. HECHO: STOCK POR UBICACION
-- ============================================================
-- Solo lo propio del stock por almacen; las fechas y precios que
-- repetian al maestro se fueron a la dimension.
CREATE TABLE normalizado.fact_stock (
    artcitem TEXT REFERENCES normalizado.maestro_articulos (artcitem),
    ubialm   TEXT,
    ubistock NUMERIC(15,2),
    artuptrn TEXT,
    artfureq DATE,
    PRIMARY KEY (artcitem, ubialm)
);

INSERT INTO normalizado.fact_stock (artcitem, ubialm, ubistock, artuptrn, artfureq)
SELECT a.artcitem, a.ubialm, a.ubistock, a.artuptrn, a.artfureq
FROM silver.articulos a;


-- ============================================================
-- VERIFICACION FINAL
-- ============================================================
-- Conteos esperados (mismos registros que silver, solo reacomodados):
--   grupos:             32
--   proveedores:       456
--   maestro_articulos: 43,255
--   fact_solicitudes:  41,971
--   fact_recepcion:    43,109
--   fact_stock:         4,130

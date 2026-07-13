-- ============================================================
-- CAPA BRONZE - VERIFICACION DE DATOS INGERTADOS
-- ============================================================

-- Conteo por tabla en bronze:
--   grupos: 32
--   proveedores: 456
--   maestro_articulos: 43,255
--   articulos: 4,130
--   recepcion: 43,109
--   solicitudes: 41,971


-- ============================================================
-- ANALISIS DE CALIDAD DE DATOS
-- ============================================================

-- DUPLICADOS POR CLAVE PRIMARIA:
--   solicitudes: 0 duplicados
--   maestro_articulos: 0 duplicados
--   grupos: 0 duplicados
--   proveedores: 0 duplicados
--   recepcion: 3,249 filas con mismo solnum (multiples articulos por pedido, NO son duplicados)
--   articulos: 482 filas con mismo artcitem (distintas ubicaciones de almacen, NO son duplicados)

-- DUPLICADOS REALES (todas las columnas identicas):
--   recepcion: 0 filas 100% identicas
--   articulos: 0 filas 100% identicas

-- VALORES VACIOS/NULOS:
--   maestro_articulos.artfusal: 12,696 (29.4%)
--   maestro_articulos.artfuent: 13,364 (30.9%)
--   maestro_articulos.artubi:   21,328 (49.3%)
--   maestro_articulos.artcmon:  20,578 (47.6%)
--   articulos.artfureq:          4,019 (97.3%)
--   proveedores.acredire:         456 (100.0%)
--   recepcion.nrcgui:               28 (0.1%)


-- ============================================================
-- CAPA SILVER - LIMPIEZA Y CARGA
-- ============================================================

DROP SCHEMA IF EXISTS silver CASCADE;
CREATE SCHEMA silver;

-- 1. GRUPOS
CREATE TABLE silver.grupos (
    artgrinv TEXT PRIMARY KEY,
    nombre TEXT NOT NULL
);
INSERT INTO silver.grupos (artgrinv, nombre)
SELECT TRIM(artgrinv), TRIM(nombre)
FROM bronze.grupos
WHERE TRIM(artgrinv) IS NOT NULL AND TRIM(artgrinv) != '';

-- 2. PROVEEDORES
CREATE TABLE silver.proveedores (
    acrecodi TEXT PRIMARY KEY, acreraso TEXT, acredire TEXT,
    acretelf TEXT, acreciud TEXT, acreiden TEXT, acreruc TEXT
);
INSERT INTO silver.proveedores (acrecodi, acreraso, acredire, acretelf, acreciud, acreiden, acreruc)
SELECT TRIM(acrecodi), TRIM(acreraso), NULLIF(TRIM(acredire),''),
       NULLIF(TRIM(acretelf),''), NULLIF(TRIM(acreciud),''),
       NULLIF(TRIM(acreiden),''), NULLIF(TRIM(acreruc),'')
FROM bronze.proveedores WHERE TRIM(acrecodi) IS NOT NULL AND TRIM(acrecodi) != '';

-- 3. MAESTRO DE ARTICULOS
CREATE TABLE silver.maestro_articulos (
    artcitem TEXT PRIMARY KEY, artdes TEXT, artmed TEXT, artgrinv TEXT,
    artcosu1 NUMERIC(15,2), artstseg INTEGER, artfusal DATE, artfuent DATE,
    artubi TEXT, artcoum1 NUMERIC(15,2), artcmon TEXT, artpreu2 NUMERIC(15,2)
);
INSERT INTO silver.maestro_articulos
    (artcitem,artdes,artmed,artgrinv,artcosu1,artstseg,artfusal,artfuent,artubi,artcoum1,artcmon,artpreu2)
SELECT TRIM(artcitem), TRIM(artdes), TRIM(artmed), TRIM(artgrinv),
    NULLIF(REGEXP_REPLACE(artcosu1,'[^0-9.\-]','','g'), '')::NUMERIC,
    NULLIF(REGEXP_REPLACE(artstseg,'[^0-9\-]','','g'), '')::INTEGER,
    CASE WHEN artfusal ~ '^[0-9]{6}$' THEN TO_DATE(artfusal,'YYMMDD')
         WHEN artfusal ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' THEN TO_DATE(artfusal,'YYYY-MM-DD')
         ELSE NULL END,
    CASE WHEN artfuent ~ '^[0-9]{6}$' THEN TO_DATE(artfuent,'YYMMDD')
         WHEN artfuent ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' THEN TO_DATE(artfuent,'YYYY-MM-DD')
         ELSE NULL END,
    NULLIF(TRIM(artubi),''),
    NULLIF(REGEXP_REPLACE(artcoum1,'[^0-9.\-]','','g'), '')::NUMERIC,
    NULLIF(TRIM(artcmon),''),
    NULLIF(REGEXP_REPLACE(artpreu2,'[^0-9.\-]','','g'), '')::NUMERIC
FROM bronze.maestro_articulos WHERE TRIM(artcitem) IS NOT NULL AND TRIM(artcitem) != '';

-- 4. ARTICULOS (stock por ubicacion)
CREATE TABLE silver.articulos (
    artcitem TEXT, artdes TEXT, artmed TEXT, artgrinv TEXT, ubialm TEXT,
    ubistock NUMERIC(15,2), artfusal DATE, artuptrn TEXT, artfureq DATE,
    artfuent DATE, artfusal_1 DATE, artcoum1 NUMERIC(15,2),
    PRIMARY KEY (artcitem, ubialm)
);
INSERT INTO silver.articulos
    (artcitem,artdes,artmed,artgrinv,ubialm,ubistock,artfusal,artuptrn,artfureq,artfuent,artfusal_1,artcoum1)
SELECT TRIM(artcitem), TRIM(artdes), TRIM(artmed), TRIM(artgrinv), TRIM(ubialm),
    NULLIF(REGEXP_REPLACE(ubistock,'[^0-9.\-]','','g'), '')::NUMERIC,
    CASE WHEN artfusal ~ '^[0-9]{6}$' THEN TO_DATE(artfusal,'YYMMDD')
         WHEN artfusal ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' THEN TO_DATE(artfusal,'YYYY-MM-DD')
         ELSE NULL END,
    NULLIF(TRIM(artuptrn),''),
    CASE WHEN artfureq ~ '^[0-9]{6}$' THEN TO_DATE(artfureq,'YYMMDD')
         WHEN artfureq ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' THEN TO_DATE(artfureq,'YYYY-MM-DD')
         ELSE NULL END,
    CASE WHEN artfuent ~ '^[0-9]{6}$' THEN TO_DATE(artfuent,'YYMMDD')
         WHEN artfuent ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' THEN TO_DATE(artfuent,'YYYY-MM-DD')
         ELSE NULL END,
    CASE WHEN artfusal_1 ~ '^[0-9]{6}$' THEN TO_DATE(artfusal_1,'YYMMDD')
         WHEN artfusal_1 ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' THEN TO_DATE(artfusal_1,'YYYY-MM-DD')
         ELSE NULL END,
    NULLIF(REGEXP_REPLACE(artcoum1,'[^0-9.\-]','','g'), '')::NUMERIC
FROM bronze.articulos WHERE TRIM(artcitem) IS NOT NULL AND TRIM(artcitem) != '';

-- 5. RECEPCION
CREATE TABLE silver.recepcion (
    solnum INTEGER, artcitem TEXT, artdes TEXT, artmed TEXT, artgrinv TEXT,
    solcan NUMERIC(15,2), nrdcac NUMERIC(15,2), artstock NUMERIC(15,2),
    solpre NUMERIC(15,2), solmon INTEGER, solurg TEXT, solusr TEXT,
    nrcfec DATE, solfec DATE, nrcnum INTEGER, solord INTEGER,
    soltip TEXT, solpro TEXT
);
INSERT INTO silver.recepcion
    (solnum,artcitem,artdes,artmed,artgrinv,solcan,nrdcac,artstock,solpre,solmon,
     solurg,solusr,nrcfec,solfec,nrcnum,solord,soltip,solpro)
SELECT NULLIF(REGEXP_REPLACE(solnum,'[^0-9\-]','','g'), '')::INTEGER,
    TRIM(artcitem), TRIM(artdes), TRIM(artmed), TRIM(artgrinv),
    NULLIF(REGEXP_REPLACE(solcan,'[^0-9.\-]','','g'), '')::NUMERIC,
    NULLIF(REGEXP_REPLACE(nrdcac,'[^0-9.\-]','','g'), '')::NUMERIC,
    NULLIF(REGEXP_REPLACE(artstock,'[^0-9.\-]','','g'), '')::NUMERIC,
    NULLIF(REGEXP_REPLACE(solpre,'[^0-9.\-]','','g'), '')::NUMERIC,
    NULLIF(REGEXP_REPLACE(solmon,'[^0-9\-]','','g'), '')::INTEGER,
    NULLIF(TRIM(solurg),''), NULLIF(TRIM(solusr),''),
    CASE WHEN nrcfec ~ '^[0-9]{6}$' THEN TO_DATE(nrcfec,'YYMMDD')
         WHEN nrcfec ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' THEN TO_DATE(nrcfec,'YYYY-MM-DD')
         ELSE NULL END,
    CASE WHEN solfec ~ '^[0-9]{6}$' THEN TO_DATE(solfec,'YYMMDD')
         WHEN solfec ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' THEN TO_DATE(solfec,'YYYY-MM-DD')
         ELSE NULL END,
    NULLIF(REGEXP_REPLACE(nrcnum,'[^0-9\-]','','g'), '')::INTEGER,
    NULLIF(REGEXP_REPLACE(solord,'[^0-9\-]','','g'), '')::INTEGER,
    NULLIF(TRIM(soltip),''), NULLIF(TRIM(solpro),'')
FROM bronze.recepcion WHERE TRIM(solnum) IS NOT NULL AND TRIM(solnum) != '';

-- 6. SOLICITUDES
CREATE TABLE silver.solicitudes (
    solnum INTEGER, artcitem TEXT, artdes TEXT, soltip TEXT,
    solcan NUMERIC(15,2), solurg TEXT, solusr TEXT, solfec DATE,
    solord INTEGER, solmon INTEGER, solpre NUMERIC(15,2), solsts TEXT,
    solsta INTEGER, solpro TEXT, artmed TEXT, artgrinv TEXT
);
INSERT INTO silver.solicitudes
    (solnum,artcitem,artdes,soltip,solcan,solurg,solusr,solfec,
     solord,solmon,solpre,solsts,solsta,solpro,artmed,artgrinv)
SELECT NULLIF(REGEXP_REPLACE(solnum,'[^0-9\-]','','g'), '')::INTEGER,
    TRIM(artcitem), TRIM(artdes), NULLIF(TRIM(soltip),''),
    NULLIF(REGEXP_REPLACE(solcan,'[^0-9.\-]','','g'), '')::NUMERIC,
    NULLIF(TRIM(solurg),''), NULLIF(TRIM(solusr),''),
    CASE WHEN solfec ~ '^[0-9]{6}$' THEN TO_DATE(solfec,'YYMMDD')
         WHEN solfec ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' THEN TO_DATE(solfec,'YYYY-MM-DD')
         ELSE NULL END,
    NULLIF(REGEXP_REPLACE(solord,'[^0-9\-]','','g'), '')::INTEGER,
    NULLIF(REGEXP_REPLACE(solmon,'[^0-9\-]','','g'), '')::INTEGER,
    NULLIF(REGEXP_REPLACE(solpre,'[^0-9.\-]','','g'), '')::NUMERIC,
    NULLIF(TRIM(solsts),''),
    NULLIF(REGEXP_REPLACE(solsta,'[^0-9\-]','','g'), '')::INTEGER,
    NULLIF(TRIM(solpro),''),
    NULLIF(TRIM(artmed),''), NULLIF(TRIM(artgrinv),'')
FROM bronze.solicitudes WHERE TRIM(solnum) IS NOT NULL AND TRIM(solnum) != '';


-- ============================================================
-- VERIFICACION FINAL
-- ============================================================
-- grupos: 32
-- proveedores: 456
-- maestro_articulos: 43,255
-- articulos: 4,130
-- recepcion: 43,109
-- solicitudes: 41,971

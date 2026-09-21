-- STF Transparency Platform — Analytical KPIs
-- Runs zero-copy against DuckDB / Parquet Gold Models

-- 1. Processes: Annual intake and distribution trends
SELECT 
    d.year AS ano,
    COUNT(*) AS total_processos,
    COUNT(CASE WHEN p.situacao = 'EM TRAMITAÇÃO' THEN 1 END) AS em_tramitacao,
    COUNT(CASE WHEN p.situacao = 'BAIXADO' THEN 1 END) AS baixados
FROM fact_processes p
JOIN dim_date d ON p.date_distribuicao_key = d.date_key
GROUP BY d.year
ORDER BY ano DESC;

-- 2. Processes: Most common process types (Classes Processuais)
SELECT 
    classe_sigla,
    classe_descricao,
    COUNT(*) AS total_acoes,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentual
FROM fact_processes
GROUP BY classe_sigla, classe_descricao
ORDER BY total_acoes DESC;

-- 3. Decisions: Volume by category (Monocrática vs Colegiada) and year
SELECT 
    d.year AS ano_decisao,
    f.categoria_decisao,
    COUNT(*) AS total_decisoes
FROM fact_decisions f
JOIN dim_date d ON f.date_decisao_key = d.date_key
GROUP BY d.year, f.categoria_decisao
ORDER BY ano_decisao DESC, total_decisoes DESC;

-- 4. Decisions: Outcome distribution (Resultados)
SELECT 
    resultado,
    COUNT(*) AS quantidade,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentual
FROM fact_decisions
GROUP BY resultado
ORDER BY quantidade DESC;

-- 5. Decisions: Volume and outcome breakdown by Rapporteur (Ministros)
SELECT 
    relator,
    COUNT(*) AS total_decisoes,
    COUNT(CASE WHEN categoria_decisao = 'MONOCRATICA' THEN 1 END) AS monocraticas,
    COUNT(CASE WHEN categoria_decisao = 'COLEGIADA' THEN 1 END) AS colegiadas
FROM fact_decisions
GROUP BY relator
ORDER BY total_decisoes DESC;

-- 6. Origin: Distribution of cases by Origin State (UF) and Geographic Region
SELECT 
    o.regiao,
    p.uf_origem,
    COUNT(*) AS total_processos
FROM fact_processes p
JOIN dim_origin o ON p.uf_origem = o.uf_origem
GROUP BY o.regiao, p.uf_origem
ORDER BY o.regiao, total_processos DESC;

-- 7. Duration / Lead time: Elapsed days from distribution to decision
SELECT 
    p.classe_sigla,
    ROUND(AVG(f.data_decisao - p.data_distribuicao), 1) AS media_dias_ate_decisao,
    MEDIAN(f.data_decisao - p.data_distribuicao) AS mediana_dias_ate_decisao,
    MIN(f.data_decisao - p.data_distribuicao) AS min_dias,
    MAX(f.data_decisao - p.data_distribuicao) AS max_dias
FROM fact_decisions f
JOIN fact_processes p ON f.process_id = p.process_id
GROUP BY p.classe_sigla
ORDER BY media_dias_ate_decisao DESC;


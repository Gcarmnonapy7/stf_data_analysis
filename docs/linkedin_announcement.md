# 🚀 LinkedIn Publication Kit: STF Transparency Platform (v1.0)

Este documento contém o kit completo para publicação no LinkedIn (em Português e Inglês), além do roteiro de carrossel de imagens, destaques técnicos e hashtags estratégicas para maximizar o engajamento e visibilidade profissional.

---

## 📌 Opção 1: Publicação em Português (PT-BR) — Recomendada para o ecossistema brasileiro

> **Dica**: Copie o texto abaixo e utilize as quebras de linha para manter a leitura agradável no feed do LinkedIn.

```markdown
⚖️ Como construí uma plataforma open-source de Data Lakehouse e Análise de Sobrevivência para dados públicos do STF (v1.0) 🇧🇷

A transparência pública no Brasil é fundamental, mas dados brutos de tribunais frequentemente sofrem com silos, falta de contratos formais de schema e lentidão no consumo analítico.

Para enfrentar esse desafio, desenvolvi a STF Transparency Platform: uma infraestrutura de engenharia de dados moderna, ponta a ponta, processando o acervo do Supremo Tribunal Federal (Corte Aberta) de 2018 a 2026.

Principais arquiteturas e marcos entregues na versão 1.0:

1️⃣ Arquitetura Medalhão Vetorizada (Polars + DuckDB)
Substituição do paradigma tradicional por pipelines vetorizados em memória. Os dados brutos (Bronze) passam por normalização tipada e deduplicação (Silver) e desembocam em um Data Lakehouse colunar analítico (Gold) em milissegundos, com DuckDB rodando local e em contêiner.

2️⃣ Modelagem de Sobrevivência de Backlog (Kaplan-Meier Estimator)
Em vez de médias simples que distorcem a realidade de processos judiciais, implementei análise de sobrevivência temporal não paramétrica:
- Meia-vida global do acervo (t_0.5 ≈ 274 dias para 50% de resolução).
- Taxas de retenção em marcos críticos (30d, 90d, 180d, 365d, 730d).
- Estratificação dinâmica por classe processual (HC, RE, ADI) e por Ministro Relator.

3️⃣ Open Lakehouse: Delta Lake & Apache Iceberg
Exportação nativa das tabelas analíticas para os formatos abertos mais adotados da indústria (ACID transaction logs em _delta_log e metadados Iceberg v2), permitindo integração plug-and-play com Databricks, Snowflake, Trino e Spark.

4️⃣ Serving Avançado & DuckDB WebAssembly (Wasm)
- Endpoints de streaming de alta velocidade (CSV, NDJSON/JSON Lines e Parquet particionado).
- Console SQL in-browser alimentado por DuckDB-Wasm: o usuário pode executar consultas analíticas complexas direto no navegador, sem sobrecarregar o backend.

5️⃣ Data Quality & Governança (100% dos Contratos Ativos)
Validações automáticas em todas as etapas: unicidade de chaves, integridade referencial temporal, teto constitucional remuneratório e hashes SHA-256 no manifest de proveniência.

6️⃣ Observabilidade e Visualização
Dashboards integrados no Grafana e Apache Superset, além de interface web nativa em FastAPI e notebooks reprodutíveis no Jupyter Lab.

7️⃣ CI/CD & Deploy de Produção
Workflows automatizados no GitHub Actions com testes unitários em matriz Python 3.11/3.12 e publicação automatizada de imagem OCI multi-stage no GitHub Container Registry (GHCR).

🔗 Repositório completo no GitHub (código aberto com licença MIT):
https://github.com/Gcarmnonapy7/stf_data_analysis

Feedback, sugestões e PRs são muito bem-vindos! O que acharam da abordagem de usar Análise de Sobrevivência no Direito?

#DataEngineering #DuckDB #Polars #Python #Lakehouse #DeltaLake #ApacheIceberg #DataQuality #GovTech #LawTech #OpenSource #DataScience #FastAPI #Docker
```

---

## 🌐 Option 2: English Publication (EN) — For Global Tech Community

```markdown
⚖️ Building an Open-Source Data Lakehouse & Survival Analytics Platform for the Brazilian Supreme Court (STF) 🚀

Judicial and governmental data are vital for democracy, but raw public feeds often struggle with schema drift, lack of contracts, and slow analytical engines.

I'm thrilled to release v1.0 of the STF Transparency Platform: a modern, end-to-end data platform processing over 8 years of public caseload, decision, and administrative data from Brazil's Supreme Federal Court.

Key Architectural Highlights:

🔹 Vectorized Medallion Architecture (Polars & DuckDB):
Processing raw feeds (Bronze) into normalized typed Parquet (Silver) and dimensional Lakehouse models (Gold) in under 0.6 seconds without JVM/cluster bloat.

🔹 Non-Parametric Backlog Survival Analysis (Kaplan-Meier):
Going beyond naive averages to model true court case throughput:
- Global backlog half-life calculation (t_0.5 ≈ 274 days).
- Retention probabilities at 30, 90, 180, 365, and 730 days.
- Stratification across legal classes (Habeas Corpus, Constitutional Appeals) and Reporting Justices.

🔹 Open Lakehouse Formats (Delta Lake & Apache Iceberg):
Curated tables exported into production-ready Delta Lake (_delta_log ACID commit logs) and Apache Iceberg v2 specifications for seamless federation with Databricks, Trino, and Snowflake.

🔹 Zero-Latency In-Browser SQL via DuckDB-Wasm:
Users can query the entire curated lakehouse directly in the web browser using WebAssembly threads, with zero server CPU overhead.

🔹 High-Throughput Streaming Export:
FastAPI streaming endpoints delivering chunked CSV, NDJSON, and columnar Parquet downloads.

🔹 Rigorous Data Quality Contracts:
100% passing automated contracts verifying referential temporal logic, constitutional wage caps, and SHA-256 provenance checksums.

🔹 Production DataOps:
Multi-Python CI/CD pipeline on GitHub Actions, multi-stage hardened Docker image, and Grafana / Apache Superset dashboards.

Check out the full repository and stars on GitHub:
👉 https://github.com/Gcarmnonapy7/stf_data_analysis

Would love to hear your thoughts on applied survival modeling in legal tech!

#DataEngineering #Lakehouse #DuckDB #Polars #Python #DeltaLake #ApacheIceberg #WebAssembly #FastAPI #DevOps #DataOps #OpenSource
```

---

## 🎨 Roteiro Sugerido para Carrossel de Imagens (PDF / Slides)

Se optar por publicar em formato de Carrossel (alta taxa de cliques no LinkedIn):

| Slide | Título do Slide | Conteúdo Visual Sugerido |
| :--- | :--- | :--- |
| **Slide 1 (Capa)** | *Modern Data Stack para Dados do STF* | Logo do STF + ícones DuckDB, Polars, FastAPI, Iceberg, Grafana. Frase: *Da ingestão bruta ao Lakehouse analítico em milissegundos*. |
| **Slide 2** | *O Problema: Dados Públicos vs Consumo Analítico* | Desafios de latência, ausência de contratos de dados e métricas enganosas como médias simples de tramitação. |
| **Slide 3** | *Arquitetura Medalhão Vetorizada* | Diagrama Bronze (CSV + SHA256) ➔ Silver (Polars Parquet) ➔ Gold (DuckDB Lakehouse). |
| **Slide 4** | *Modelagem Estatística: Kaplan-Meier* | Gráfico da curva de sobrevivência mostrando a meia-vida do acervo (274 dias) e a queda de retenção ao longo dos anos. |
| **Slide 5** | *Open Lakehouse: Delta Lake & Iceberg* | Ilustração das estruturas de pastas `_delta_log/` e `metadata/v1.metadata.json` geradas automaticamente. |
| **Slide 6** | *DuckDB-Wasm: SQL no Navegador* | Screenshot do modal do DuckDB-Wasm rodando uma consulta SQL analítica direto no client-side sem bater no servidor. |
| **Slide 7** | *Dashboards & Observabilidade* | Screenshots dos painéis do Grafana (distribuição por Ministro e orçamento anual) e Apache Superset. |
| **Slide 8 (Call to Action)** | *Código 100% Aberto no GitHub* | Link do repositório, convite para dar Star ⭐ e conectar no LinkedIn. |

---

## 💡 Dicas para a Postagem

1. **Horário de Ouro**: Publique de terça a quinta-feira, preferencialmente entre as **08:30 e as 10:30** da manhã ou entre as **17:00 e 18:30**.
2. **Primeiro Comentário**: Deixe o link direto do GitHub também no primeiro comentário fixado para facilitar para quem lê pelo celular.
3. **Mídia**: Inclua um vídeo curto de 15 segundos da interface web rodando ou um GIF demonstrando o DuckDB-Wasm e o gráfico de Kaplan-Meier.


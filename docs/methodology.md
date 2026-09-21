# ⚖️ STF Transparency Platform — Methodology & Principles

## 1. Political Neutrality & Non-Partisanship
The primary goal of the **STF Transparency Platform** is to make public judicial data accessible, reproducible, and easy to analyze for researchers, citizens, journalists, and legal scholars.

- The platform **does not** score judicial decisions as "good" or "bad".
- The platform **does not** generate partisan commentary.
- All statistics reflect official court classifications, verbatim categories, and transparent mathematical aggregations.

## 2. Data Cleaning & Normalization Rules
1. **Primary Key Deduplication**: When multiple raw records share the same entity identifier (`process_id` or `decision_id`), deduplication keeps the first recorded occurrence unless timestamps indicate an update.
2. **Missing Values**: Empty strings, `"N/A"`, `"NULL"`, and `"NaN"` are standardized to SQL `NULL` values rather than arbitrary defaults.
3. **Date Consistency**: Decisions recorded as occurring prior to a process's official distribution date are flagged by the Data Quality Gate for manual inspection.
4. **State Codes (UF)**: All geographic origin fields are converted to uppercase 2-letter ISO 3166-2:BR codes. Unmapped entries are explicitly categorized as `"Indeterminado"`.

## 3. Metric Formulations
- **Active Backlog**: Count of processes where `situacao` equals `'EM TRAMITAÇÃO'`.
- **Duration to Decision**: Calendar days elapsed between `data_distribuicao` and `data_decisao`.
- **Monocracy Ratio**: Ratio of decisions rendered by a single justice (`MONOCRATICA`) versus collegiate decisions rendered by chambers or the plenary bench (`COLEGIADA`).


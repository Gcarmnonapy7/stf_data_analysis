# 📖 STF Transparency Platform — Data Dictionary

This data dictionary documents the schema across Bronze, Silver, and Gold layers.

---

## 1. Silver Datasets

### `silver/processos.parquet`
| Column | Type | Nullable | Description | Example |
| :--- | :--- | :--- | :--- | :--- |
| `process_id` | `Utf8` | No (PK) | Canonical compound identifier (`{classe}-{numero}`) | `ADI-7123` |
| `numero_processo` | `Int64` | Yes | Numeric process sequential number | `7123` |
| `classe_sigla` | `Utf8` | No | Abbreviated procedural class acronym | `ADI`, `RE`, `HC` |
| `classe_descricao` | `Utf8` | Yes | Full description of procedural class | `Ação Direta de Inconstitucionalidade` |
| `assunto` | `Utf8` | Yes | Legal topic hierarchy | `DIREITO TRIBUTÁRIO \| Impostos \| ICMS` |
| `relator` | `Utf8` | Yes | Reporting Minister | `Min. Luís Roberto Barroso` |
| `data_autuacao` | `Date` | Yes | Filing/autuação date | `2022-04-10` |
| `data_distribuicao`| `Date` | No | Distribution to Justice date | `2022-04-12` |
| `uf_origem` | `Utf8` | Yes | Origin Brazilian state acronym | `SP`, `DF`, `RJ` |
| `orgao_julgador` | `Utf8` | Yes | Competent bench | `Plenário`, `1ª Turma`, `2ª Turma` |
| `situacao` | `Utf8` | Yes | Case status | `EM TRAMITAÇÃO`, `BAIXADO`, `JULGADO` |
| `ano_distribuicao` | `Int32` | No | Year of distribution | `2022` |
| `mes_distribuicao` | `Int32` | No | Month of distribution | `4` |

### `silver/decisoes.parquet`
| Column | Type | Nullable | Description | Example |
| :--- | :--- | :--- | :--- | :--- |
| `decision_id` | `Utf8` | No (PK) | Unique decision identifier | `DEC-10492` |
| `process_id` | `Utf8` | No (FK) | Reference to process | `ADI-7123` |
| `numero_processo` | `Int64` | Yes | Numeric process number | `7123` |
| `classe_sigla` | `Utf8` | No | Class acronym | `ADI` |
| `data_decisao` | `Date` | No | Date decision was rendered | `2023-08-15` |
| `tipo_decisao` | `Utf8` | Yes | Decision format specification | `Monocrática`, `Acórdão - Plenário Virtual` |
| `categoria_decisao`| `Utf8` | No | High-level categorization | `MONOCRATICA`, `COLEGIADA`, `PRESIDENCIA` |
| `resultado` | `Utf8` | Yes | Substantive outcome | `Provido`, `Negado Seguimento`, `Procedente` |
| `relator` | `Utf8` | Yes | Justice who rendered decision | `Min. Alexandre de Moraes` |
| `orgao_colegiado` | `Utf8` | Yes | Bench / chamber | `Plenário`, `Gabinete do Relator` |
| `texto_resumo` | `Utf8` | Yes | Decision syllabus / summary | `Decisão proferida no âmbito do...` |
| `ano_decisao` | `Int32` | No | Year of decision | `2023` |
| `mes_decisao` | `Int32` | No | Month of decision | `8` |

---

## 2. Gold Dimensional Model

### `fact_processes`
Consolidates process metrics and foreign keys to dimensions:
- `date_distribuicao_key` $\rightarrow$ `dim_date.date_key`
- `date_autuacao_key` $\rightarrow$ `dim_date.date_key`

### `fact_decisions`
Records decision events connected to:
- `date_decisao_key` $\rightarrow$ `dim_date.date_key`
- `process_id` $\rightarrow$ `fact_processes.process_id`

### `dim_date`
Calendar table providing dates, Portuguese month and weekday names, quarters, and business day flags.

### `dim_origin`
Maps Brazilian states (`uf_origem`) to geographic macro-regions (`Sul`, `Sudeste`, `Centro-Oeste`, `Nordeste`, `Norte`).

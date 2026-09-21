"""Sample and fixture generator for STF Corte Aberta datasets.

Generates realistic, schema-valid datasets matching the official STF open data
specifications. This ensures full reproducibility and offline developer experience.
"""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path
from typing import List, Tuple

# Canonical STF Classes
CLASSES: List[Tuple[str, str]] = [
    ("ADI", "Ação Direta de Inconstitucionalidade"),
    ("ADC", "Ação Declaratória de Constitucionalidade"),
    ("ADPF", "Arguição de Descumprimento de Preceito Fundamental"),
    ("RE", "Recurso Extraordinário"),
    ("ARE", "Agravo em Recurso Extraordinário"),
    ("HC", "Habeas Corpus"),
    ("MS", "Mandado de Segurança"),
    ("Rcl", "Reclamação"),
    ("MI", "Mandado de Injunção"),
    ("ACO", "Ação Cível Originária"),
]

MINISTROS: List[str] = [
    "Min. Luís Roberto Barroso",
    "Min. Gilmar Mendes",
    "Min. Cármen Lúcia",
    "Min. Dias Toffoli",
    "Min. Luiz Fux",
    "Min. Edson Fachin",
    "Min. Alexandre de Moraes",
    "Min. Nunes Marques",
    "Min. André Mendonça",
    "Min. Cristiano Zanin",
    "Min. Flávio Dino",
]

ASSUNTOS: List[str] = [
    "DIREITO CONSTITUCIONAL | Direitos Fundamentais | Liberdade de Expressão",
    "DIREITO TRIBUTÁRIO | Impostos | ICMS | Base de Cálculo",
    "DIREITO ADMINISTRATIVO | Concurso Público | Reserva de Vagas",
    "DIREITO PENAL | Crimes contra o Patrimônio | Estelionato",
    "DIREITO PROCESSUAL CIVIL | Coisa Julgada | Eficácia Temporal",
    "DIREITO DO TRABALHO | Terceirização | Responsabilidade Subsidiária",
    "DIREITO AMBIENTAL | Proteção de Biomas | Competência Administrativa",
    "DIREITO PREVIDENCIÁRIO | Benefícios | Regra de Transição",
]

UFS: List[str] = [
    "SP", "RJ", "MG", "RS", "PR", "BA", "DF", "SC", "GO", "PE",
    "CE", "PA", "MT", "MA", "ES", "MS", "PB", "RN", "AL", "PI",
    "AM", "RO", "SE", "TO", "AC", "AP", "RR",
]

TIPOS_DECISAO: List[str] = [
    "Monocrática",
    "Acórdão - Plenário Presencial",
    "Acórdão - Plenário Virtual",
    "Acórdão - 1ª Turma",
    "Acórdão - 2ª Turma",
    "Decisão da Presidência",
]

RESULTADOS: List[str] = [
    "Provido",
    "Não Provido",
    "Negado Seguimento",
    "Prejudicado",
    "Procedente",
    "Improcedente",
    "Parcialmente Procedente",
    "Concedida a Ordem",
    "Denegada a Ordem",
    "Extinto sem Resolução de Mérito",
]

TIPOS_RECURSO: List[str] = [
    "Embargos de Declaração",
    "Agravo Interno / Regimental",
    "Embargos de Divergência",
    "Agravo em Recurso Extraordinário",
]


def random_date(start_year: int = 2018, end_year: int = 2026) -> date:
    start_date = date(start_year, 1, 1)
    end_date = date(end_year, 12, 31)
    delta_days = (end_date - start_date).days
    return start_date + timedelta(days=random.randint(0, delta_days))


def generate_fixtures(
    output_dir: Path | str,
    n_processes: int = 500,
    seed: int = 42,
) -> dict[str, Path]:
    """Generates schema-compliant CSV fixtures in the specified directory."""
    random.seed(seed)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    proc_dir = out_dir / "processos"
    dec_dir = out_dir / "decisoes"
    rec_dir = out_dir / "recursos"
    rg_dir = out_dir / "repercussao_geral"

    for d in (proc_dir, dec_dir, rec_dir, rg_dir):
        d.mkdir(parents=True, exist_ok=True)

    # 1. Generate Processes
    proc_file = proc_dir / "processos_stf.csv"
    processes_data = []

    for i in range(1, n_processes + 1):
        class_code, class_desc = random.choice(CLASSES)
        proc_num = random.randint(100000, 1500000)
        proc_id = f"{class_code}-{proc_num}"
        relator = random.choice(MINISTROS)
        distrib_date = random_date(2018, 2026)
        autuacao_date = distrib_date - timedelta(days=random.randint(1, 15))
        assunto = random.choice(ASSUNTOS)
        uf = random.choice(UFS)
        situacao = random.choices(["EM TRAMITAÇÃO", "BAIXADO", "JULGADO"], weights=[0.3, 0.5, 0.2])[0]
        orgao = "Plenário" if class_code in ["ADI", "ADC", "ADPF"] else random.choice(["1ª Turma", "2ª Turma", "Plenário"])

        processes_data.append({
            "process_id": proc_id,
            "numero_processo": proc_num,
            "classe_sigla": class_code,
            "classe_descricao": class_desc,
            "assunto": assunto,
            "relator": relator,
            "data_autuacao": autuacao_date.isoformat(),
            "data_distribuicao": distrib_date.isoformat(),
            "uf_origem": uf,
            "orgao_julgador": orgao,
            "situacao": situacao,
        })

    with open(proc_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(processes_data[0].keys()))
        writer.writeheader()
        writer.writerows(processes_data)

    # 2. Generate Decisions
    dec_file = dec_dir / "decisoes_stf.csv"
    decisions_data = []
    dec_counter = 1

    for p in processes_data:
        distrib_date = date.fromisoformat(p["data_distribuicao"])
        # Some processes have 1 or 2 decisions
        num_dec = random.choices([1, 2, 3], weights=[0.6, 0.3, 0.1])[0]
        for step in range(num_dec):
            dec_date = distrib_date + timedelta(days=random.randint(30, 400 * (step + 1)))
            if dec_date > date(2026, 12, 31):
                dec_date = date(2026, 12, 31)

            tipo_dec = random.choice(TIPOS_DECISAO)
            resultado = random.choice(RESULTADOS)
            orgao_dec = p["orgao_julgador"] if "Acórdão" in tipo_dec else "Gabinete do Relator"

            decisions_data.append({
                "decision_id": f"DEC-{dec_counter}",
                "process_id": p["process_id"],
                "numero_processo": p["numero_processo"],
                "classe_sigla": p["classe_sigla"],
                "data_decisao": dec_date.isoformat(),
                "tipo_decisao": tipo_dec,
                "resultado": resultado,
                "relator": p["relator"],
                "orgao_colegiado": orgao_dec,
                "texto_resumo": f"Decisão proferida no âmbito do {p['process_id']} julgando {resultado.lower()}.",
            })
            dec_counter += 1

    with open(dec_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(decisions_data[0].keys()))
        writer.writeheader()
        writer.writerows(decisions_data)

    # 3. Generate Appeals (Recursos)
    rec_file = rec_dir / "recursos_stf.csv"
    recursos_data = []
    rec_counter = 1

    for p in processes_data[: int(n_processes * 0.4)]:  # 40% of processes have appeals
        distrib_date = date.fromisoformat(p["data_distribuicao"])
        interposicao_date = distrib_date + timedelta(days=random.randint(60, 300))
        julgamento_date = interposicao_date + timedelta(days=random.randint(30, 180))

        tipo_rec = random.choice(TIPOS_RECURSO)
        resultado_rec = random.choice(["Provido", "Não Provido", "Rejeitado", "Não Conhecido"])

        recursos_data.append({
            "recurso_id": f"REC-{rec_counter}",
            "process_id": p["process_id"],
            "tipo_recurso": tipo_rec,
            "data_interposicao": interposicao_date.isoformat(),
            "data_julgamento": julgamento_date.isoformat(),
            "resultado_recurso": resultado_rec,
            "relator": p["relator"],
        })
        rec_counter += 1

    with open(rec_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(recursos_data[0].keys()))
        writer.writeheader()
        writer.writerows(recursos_data)

    # 4. Generate Repercussão Geral
    rg_file = rg_dir / "repercussao_geral_stf.csv"
    rg_data = []
    temas = [
        (1234, "Constitucionalidade da alíquota do ICMS sobre energia elétrica"),
        (1010, "Direito ao esquecimento na esfera cível"),
        (987, "Incidência de imposto de renda sobre juros de mora"),
        (855, "Responsabilidade solidária dos entes federados no fornecimento de medicamentos"),
        (723, "Possibilidade de flexibilização de normas trabalhistas por acordo coletivo"),
        (1111, "Poder de polícia ambiental municipal em terras protegidas"),
    ]
    for tema_num, titulo in temas:
        reconhecimento = random_date(2015, 2022)
        rg_data.append({
            "tema_numero": tema_num,
            "titulo": titulo,
            "data_reconhecimento": reconhecimento.isoformat(),
            "status": random.choice(["Julgado com repercussão geral", "Em tramitação"]),
            "relator": random.choice(MINISTROS),
            "tese_fixada": f"Tese fixada para o Tema {tema_num} com eficácia vinculante.",
        })

    with open(rg_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rg_data[0].keys()))
        writer.writeheader()
        writer.writerows(rg_data)

    return {
        "processos": proc_file,
        "decisoes": dec_file,
        "recursos": rec_file,
        "repercussao_geral": rg_file,
    }


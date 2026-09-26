import sys

from .sources import fetch_raw_text, find_provider_info, find_review_text
from .extract import extract_model_comparison, extract_provider_comparison, extract_status_uptime
from .store import save_model_comparison, save_provider_comparison
from .verify import (
    ExtractionRejected,
    Verified,
    verify_model_extraction,
    verify_provider_extraction,
    verify_uptime,
)
from .report import generate_report, generate_provider_report


def _print_summary(verified: Verified, changes: list, source_url: str) -> None:
    # Mostra o que foi aprovado, o que foi descartado e por quê, e o que
    # mudou em relação ao que já estava salvo — nada disso deve ser silencioso.
    print(f"Fonte: {source_url}")
    for field, quote in verified.evidence.items():
        print(f"  OK       {field}: \"{quote[:90]}\"")
    for field, reason in verified.rejected.items():
        print(f"  DESCARTADO {field}: {reason}")
    for field, old, new in changes:
        label = "REGISTRADO (1º valor)" if old is None else "ATUALIZADO"
        print(f"  {label} {field}: {old} -> {new}")


def run_pipeline(url: str, model_key: str, facts_only: bool = False) -> Verified:
    raw_text = fetch_raw_text(url)
    extraction = extract_model_comparison(raw_text)
    verified = verify_model_extraction(extraction, raw_text, model_key)
    changes = save_model_comparison(verified.comparison, model_key, url, verified.evidence, facts_only=facts_only)
    _print_summary(verified, changes, url)
    # O relatório completo (com todas as notas de qualidade, ~7 KB) só serve pra
    # quem roda na mão. No modo agendado ele repetia depois de cada alvo e
    # enterrava as linhas que importam no log do CI.
    if not facts_only:
        generate_report()
    return verified


def run_quality_pipeline(model_name: str, model_key: str) -> None:
    url, raw_text = find_review_text(model_name)
    extraction = extract_model_comparison(raw_text)
    # A identidade esperada vem da chave (curta e estável), não da consulta de busca,
    # que pode ter texto extra (empresa, ano, aspas).
    verified = verify_model_extraction(extraction, raw_text, model_key)
    changes = save_model_comparison(verified.comparison, model_key, url, verified.evidence)
    _print_summary(verified, changes, url)
    generate_report()


def run_provider_pipeline(provider_name: str, provider_key: str) -> None:
    url, raw_text = find_provider_info(provider_name)
    extraction = extract_provider_comparison(raw_text)
    verified = verify_provider_extraction(extraction, raw_text, provider_key)
    changes = save_provider_comparison(verified.comparison, provider_key, url, verified.evidence)
    _print_summary(verified, changes, url)
    generate_provider_report()


def run_status_pipeline(status_url: str, provider_name: str, provider_key: str, quiet: bool = False) -> Verified:
    # Uptime medido vem da página de status oficial, não de busca: a URL é
    # informada por quem roda, então a fonte é sempre a oficial.
    raw_text = fetch_raw_text(status_url)
    result = extract_status_uptime(raw_text)
    verified = verify_uptime(result.api_uptime_pct, result.evidence_quote, raw_text, provider_name)
    changes = save_provider_comparison(verified.comparison, provider_key, status_url, verified.evidence)
    _print_summary(verified, changes, status_url)
    if not quiet:
        generate_provider_report()
    return verified


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        if mode == "url":
            facts_only = "--facts-only" in sys.argv[4:]
            run_pipeline(sys.argv[2], sys.argv[3], facts_only=facts_only)
        elif mode == "quality":
            run_quality_pipeline(sys.argv[2], sys.argv[3])
        elif mode == "provider":
            run_provider_pipeline(sys.argv[2], sys.argv[3])
        elif mode == "status":
            run_status_pipeline(sys.argv[2], sys.argv[3], sys.argv[4])
        else:
            print("Uso: python -m market_intel.run_pipeline url <URL> <model_key>")
            print("  ou: python -m market_intel.run_pipeline quality <nome-do-modelo> <model_key>")
            print("  ou: python -m market_intel.run_pipeline provider <nome-do-provedor> <provider_key>")
            print("  ou: python -m market_intel.run_pipeline status <URL-da-pagina-de-status> <nome-do-provedor> <provider_key>")
    except ExtractionRejected as error:
        # Alvo errado: nada é salvo. Sai com erro pra scripts perceberem.
        print(f"COLETA REJEITADA (nada foi salvo): {error}")
        sys.exit(1)

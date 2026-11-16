"""Public-site whitelist and value-free privacy audit."""
from __future__ import annotations

from experiments.redesign_20261116.build_public_site import DOCS, select
from experiments.redesign_20261116.public_release_audit import scan_text


def test_audit_flags_credentials_and_private_mail_without_public_noreply():
    fake_token = "ghp_" + "A1b2C3d4E5" * 4
    private_mail = "someone" + "@" + "private-company.test"  # built at runtime so this file stays audit-clean
    hits = scan_text(f"token: {fake_token}\nauthor: {private_mail}\nbot: 1+x@users.noreply.github.com")
    kinds = {(level, name) for level, name in hits}
    assert ("CRITICAL", "github_token") in kinds
    assert hits[("MEDIUM", "email_non_public_domain")] == 1  # noreply address is allow-listed


def test_audit_ignores_plain_research_text():
    assert not scan_text("H1 M2 - M0 = +6.09 pp; doi 10.1000/xyz; see https://www.openml.org/d/41156")


def test_site_whitelist_publishes_dashboards_but_not_raw_research_or_internal_notes():
    chosen = {p.relative_to(DOCS).as_posix() for p in select()}
    assert "index.html" in chosen
    assert "research/teacher_dashboard/index.html" in chosen
    assert "research/teacher_dashboard/redesign/index.html" in chosen
    assert "research/teacher_dashboard/data/redesign_20261116/REDESIGN_SITE_MANIFEST.json" in chosen
    assert not any(p.startswith("research/redesign_20261116/") for p in chosen)   # 228 MB raw CSVs stay in Git only
    assert not any("/" not in p and p.endswith(".md") for p in chosen)            # internal audit notes
    assert not any(p.startswith(("reviews/", "superpowers/", "final_math_audit")) for p in chosen)

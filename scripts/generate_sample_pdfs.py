"""Generate fictional proposals used for the classroom demo."""
from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib import colors


PROPOSALS = {
    "apex_systems.pdf": {
        "name": "Apex Systems",
        "summary": "Apex proposes a resilient cloud integration platform with strong security controls for the procurement programme.",
        "solution": "The solution uses API gateway integrations, event-driven services, horizontal scaling, and a documented disaster recovery design. Architecture review is scheduled before build.",
        "plan": "Delivery is planned over 20 weeks: discovery (4), build (10), integration testing (4), and rollout (2). A delivery manager, solution architect, security lead, and six engineers are assigned.",
        "price": [["Item", "Amount"], ["Implementation", "$420,000"], ["Annual support", "$96,000"], ["Assumption", "Client provides identity-provider access"]],
        "security": "Controls include SSO, least privilege, AES-256 encryption at rest, TLS in transit, quarterly access reviews, audit logs, incident response, and ISO 27001 certification.",
        "support": "24/7 severity-one support, named service manager, quarterly service reviews, and three comparable enterprise references are included.",
    },
    "brightpath_tech.pdf": {
        "name": "BrightPath Tech",
        "summary": "BrightPath offers a low-cost, rapid implementation for the procurement programme.",
        "solution": "The proposed hosted portal includes standard workflows and CSV imports. Integration will be confirmed during discovery.",
        "plan": "An eight-week timeline covers configuration, user acceptance testing, and launch. The team has a project lead and two implementation consultants.",
        "price": [["Item", "Amount"], ["Implementation", "$165,000"], ["Annual support", "$36,000"], ["Assumption", "Standard connectors are sufficient"]],
        "security": "The platform uses encrypted connections and routine backups. Detailed certification, privacy, audit-log retention, and incident response information will be supplied later.",
        "support": "Business-hours email support is included. BrightPath has delivered two smaller implementations; references are available on request.",
    },
    "nexaworks.pdf": {
        "name": "NexaWorks",
        "summary": "NexaWorks provides a balanced programme combining configurable integrations, controlled delivery, and a high-touch support model.",
        "solution": "The proposed modular platform integrates through REST APIs and approved middleware. Capacity testing, role design, and a solution prototype are completed before configuration is scaled.",
        "plan": "A 14-week delivery has named milestones: discovery (2 weeks), prototype (3), configuration (5), test and training (3), and go-live (1). The risk register has owners, triggers, and mitigations. The team includes a programme manager, architect, integration lead, security analyst, trainer, and four engineers.",
        "price": [["Item", "Amount"], ["Implementation", "$285,000"], ["Annual support", "$72,000"], ["Assumption", "Up to six external integrations"]],
        "security": "NexaWorks provides SSO, MFA, encryption in transit and at rest, immutable audit records, annual penetration tests, privacy impact assessment support, and SOC 2 Type II controls.",
        "support": "A named customer success manager, 24/7 critical support, monthly adoption reviews, knowledge transfer, and four relevant references are included.",
    },
    "orbit_digital.pdf": {
        "name": "Orbit Digital",
        "summary": "Orbit Digital brings extensive public-sector delivery experience and a proven managed-service approach.",
        "solution": "Orbit will configure its established platform and work with the client to determine how existing systems connect. Integration patterns will be agreed after contract award.",
        "plan": "The 16-week approach includes mobilisation, configuration, testing, training, and launch. A delivery director, project manager, and implementation team are proposed.",
        "price": [["Item", "Amount"], ["Implementation", "$260,000"], ["Annual support", "$68,000"], ["Assumption", "Integration scope agreed during mobilisation"]],
        "security": "The service has encryption, role-based access, security monitoring, backup testing, and an ISO 27001-aligned information-security programme.",
        "support": "Orbit offers 24/7 critical support, a service desk, quarterly reviews, and six references from comparable large organisations.",
    },
}


def build_pdf(path: Path, proposal: dict[str, object]) -> None:
    styles = getSampleStyleSheet()
    document = SimpleDocTemplate(str(path), pagesize=letter, title=str(proposal["name"]))
    story = [Paragraph(f"{proposal['name']} — Supplier Proposal", styles["Title"]), Spacer(1, 14)]
    for heading, key in [
        ("Executive Summary", "summary"), ("Proposed Solution", "solution"),
        ("Implementation Plan, Team, and Milestones", "plan"), ("Security, Compliance, and Risk Controls", "security"),
        ("Support, Experience, and References", "support"),
    ]:
        story.extend([Paragraph(heading, styles["Heading2"]), Paragraph(str(proposal[key]), styles["BodyText"]), Spacer(1, 10)])
        if heading == "Implementation Plan, Team, and Milestones":
            story.append(Paragraph("Commercial Proposal", styles["Heading2"]))
            table = Table(proposal["price"])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey), ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]))
            story.extend([table, Spacer(1, 10)])
    document.build(story)


if __name__ == "__main__":
    output = Path("sample_rfps")
    output.mkdir(parents=True, exist_ok=True)
    for filename, proposal in PROPOSALS.items():
        build_pdf(output / filename, proposal)
    print(f"Generated {len(PROPOSALS)} fictional proposals in {output}")

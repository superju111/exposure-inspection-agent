"""
Report generation module (产出模块).

Generates two output formats:
  1. JSON report (machine-readable, for integration with ticketing/SOC)
  2. Markdown report (human-readable, for management review)

Reports include:
  - Executive summary with statistics
  - Findings sorted by priority
  - Evidence chain for each finding
  - Remediation recommendations
  - LLM analysis appendix (where applicable)
"""
import json
import os
from datetime import datetime
from typing import Optional


class Reporter:
    """Generate exposure inspection reports."""

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate(self, findings: list, scan_metadata: dict,
                 llm_analyses: Optional[dict] = None) -> str:
        """
        Generate both JSON and Markdown reports.
        Returns the path to the Markdown report.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Generate JSON report
        json_report = self._build_json_report(findings, scan_metadata, llm_analyses)
        json_path = os.path.join(self.output_dir, f"exposure_report_{timestamp}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_report, f, ensure_ascii=False, indent=2)

        # Generate Markdown report
        md_report = self._build_markdown_report(json_report)
        md_path = os.path.join(self.output_dir, f"exposure_report_{timestamp}.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_report)

        print(f"[Reporter] Reports generated: {md_path}", flush=True)
        return md_path

    def _build_json_report(self, findings, scan_metadata, llm_analyses=None):
        """Build structured JSON report."""
        # Statistics
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        priority_counts = {}
        for f in findings:
            sev = f.get("severity", "low")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
            pri = f.get("priority", "P4")
            priority_counts[pri] = priority_counts.get(pri, 0) + 1

        return {
            "report_id": f"EXP-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "generated_at": datetime.now().isoformat(),
            "scan_metadata": scan_metadata,
            "summary": {
                "total_findings": len(findings),
                "severity_breakdown": severity_counts,
                "priority_breakdown": priority_counts,
            },
            "findings": findings,
            "llm_analyses": llm_analyses or {},
        }

    def _build_markdown_report(self, report: dict) -> str:
        """Build human-readable Markdown report."""
        lines = []
        meta = report["scan_metadata"]
        summary = report["summary"]

        lines.append("# Internet Exposure Inspection Report")
        lines.append("")
        lines.append(f"**Report ID:** {report['report_id']}")
        lines.append(f"**Generated:** {report['generated_at']}")
        lines.append(f"**Scan Date:** {meta.get('scan_date', 'N/A')}")
        lines.append(f"**Assets Scanned:** {meta.get('total_assets', 0)}")
        lines.append(f"**Total Ports Scanned:** {meta.get('total_ports_scanned', 0)}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Executive Summary
        lines.append("## Executive Summary")
        lines.append("")
        sev = summary["severity_breakdown"]
        lines.append(f"- Total findings: **{summary['total_findings']}**")
        lines.append(f"- Critical: **{sev.get('critical', 0)}**")
        lines.append(f"- High: **{sev.get('high', 0)}**")
        lines.append(f"- Medium: **{sev.get('medium', 0)}**")
        lines.append(f"- Low: **{sev.get('low', 0)}**")
        lines.append("")

        if sev.get("critical", 0) > 0:
            lines.append(
                "> **WARNING:** Critical exposures detected. "
                "Immediate remediation required."
            )
            lines.append("")

        lines.append("---")
        lines.append("")

        # Findings by Priority
        findings = report["findings"]
        current_priority = None
        for f in findings:
            pri = f.get("priority", "P4")
            if pri != current_priority:
                current_priority = pri
                lines.append(f"## {pri}")
                lines.append("")

            lines.append(f"### {f['host']}:{f['port']} - {f['severity'].upper()}")
            lines.append("")
            lines.append(f"- **Rule ID:** {f['rule_id']}")
            lines.append(f"- **Rule Source:** {f['rule_source']}")
            lines.append(f"- **Service:** {f['service']}")
            lines.append(f"- **Risk Score:** {f.get('risk_score', 'N/A')}")
            lines.append(f"- **Evidence:** {f['evidence']}")
            lines.append(f"- **Recommendation:** {f['recommendation']}")
            if f.get("banner"):
                lines.append(f"- **Banner:** `{f['banner'][:150]}`")

            # LLM analysis appendix
            finding_key = f"{f['host']}:{f['port']}"
            llm_analysis = report.get("llm_analyses", {}).get(finding_key)
            if llm_analysis:
                lines.append(f"- **LLM Context Analysis:** {llm_analysis[:300]}")

            lines.append("")

        lines.append("---")
        lines.append("")
        lines.append("## Methodology")
        lines.append("")
        lines.append(
            "Findings are generated by practice-derived rules, not public standards. "
            "Rules are loaded from knowledge/*.yaml files and applied by deterministic "
            "code in analyzer.py. LLM is used only for fuzzy judgment on ambiguous "
            "findings and does not make final classifications."
        )
        lines.append("")
        lines.append(
            "Rule sources: port_risk_rules, banner_signatures, exposure_criteria, "
            "priority_matrix. See knowledge/ directory for rule definitions and "
            "docs/knowledge_rationale.md for derivation methodology."
        )

        return "\n".join(lines)

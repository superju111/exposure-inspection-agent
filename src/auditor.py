"""
Audit logging module (留痕模块).

Writes NDJSON audit logs for every step of the agent pipeline.
This is the evidence chain that proves:
  1. Agent ran a complete cycle (trigger -> data -> judgment -> output)
  2. OctoBus calls were made through the gateway (not direct backend)
  3. Each finding has a traceable rule source and evidence
  4. LLM calls (if any) are logged with prompts and responses

Log format: NDJSON (Newline-Delimited JSON) - one JSON object per line.
This format is queryable, grep-able, and matches OctoBus server-side audit logs.
"""
import json
import os
import time
from datetime import datetime


class Auditor:
    """NDJSON audit logger for the full agent pipeline."""

    def __init__(self, output_dir: str):
        self.log_dir = os.path.join(output_dir, "logs")
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_file = os.path.join(
            self.log_dir,
            f"agent_audit_{datetime.now().strftime('%Y%m%d')}.ndjson"
        )
        self.cycle_id = f"cycle_{int(time.time())}"
        self._log("cycle_start", {"cycle_id": self.cycle_id})

    def _log(self, event_type: str, data: dict):
        """Write a single NDJSON log entry."""
        entry = {
            "timestamp": time.time(),
            "iso_timestamp": datetime.now().isoformat(),
            "cycle_id": self.cycle_id,
            "event_type": event_type,
            **data,
        }
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def log_trigger(self, trigger_type: str, trigger_detail: dict):
        """Log the trigger event."""
        self._log("trigger", {
            "trigger_type": trigger_type,
            "trigger_detail": trigger_detail,
        })

    def log_collection(self, asset_count: int, results: list):
        """Log data collection results."""
        self._log("data_collection", {
            "asset_count": asset_count,
            "results_summary": [
                {
                    "host": r.get("host"),
                    "open_ports": r.get("total_open", 0),
                    "error": r.get("error"),
                }
                for r in results
            ],
        })

    def log_octobus_call(self, service: str, method: str,
                         request: dict, response: dict, status: str):
        """Log an OctoBus gateway call."""
        self._log("octobus_call", {
            "service": service,
            "method": method,
            "request_summary": {k: str(v)[:100] for k, v in request.items()},
            "response_summary": {k: str(v)[:100] for k, v in (response or {}).items()},
            "status": status,
        })

    def log_analysis(self, findings: list):
        """Log analysis results."""
        self._log("analysis", {
            "total_findings": len(findings),
            "findings_summary": [
                {
                    "host": f["host"],
                    "port": f["port"],
                    "severity": f["severity"],
                    "rule_id": f["rule_id"],
                    "rule_source": f["rule_source"],
                    "risk_score": f.get("risk_score"),
                    "priority": f.get("priority"),
                }
                for f in findings
            ],
        })

    def log_report(self, report_path: str, finding_count: int):
        """Log report generation."""
        self._log("report_generated", {
            "report_path": report_path,
            "finding_count": finding_count,
        })

    def log_llm_call(self, finding_key: str, prompt_summary: str,
                    response_summary: str, status: str):
        """Log LLM fuzzy judgment call."""
        self._log("llm_call", {
            "finding_key": finding_key,
            "prompt_summary": prompt_summary[:200],
            "response_summary": (response_summary or "")[:200],
            "status": status,
        })

    def log_error(self, stage: str, error: str):
        """Log an error during pipeline execution."""
        self._log("error", {
            "stage": stage,
            "error": error,
        })

    def log_cycle_end(self, success: bool, summary: dict):
        """Log the end of the agent cycle."""
        self._log("cycle_end", {
            "success": success,
            "summary": summary,
        })

    def finalize(self, success: bool, summary: dict):
        """Write cycle end log entry."""
        self.log_cycle_end(success, summary)
        print(f"[Auditor] Audit log: {self.log_file}", flush=True)

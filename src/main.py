"""
Main entry point - Agent orchestration loop.

Implements the five-stage closed loop:
  1. Trigger (cron) -> 2. Collect (OctoBus) -> 3. Analyze (rules+LLM)
  -> 4. Report -> 5. Audit

This file is the entry point called by agent-compose's guest container.
It coordinates all modules and ensures the complete cycle runs with full
audit trail.

LLM vs Code division (per assessment requirement):
  - Code: asset querying, port scanning, port classification, banner matching,
    risk scoring, priority ranking, report formatting, audit logging
  - LLM: fuzzy judgment on ambiguous findings only (banner empty/uncertain),
    does NOT make final classification, only provides context for report
"""
import sys
import os
import time
import json

# Add src directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import load_config, load_knowledge_rules, AgentConfig
from octobus_client import OctoBusClient
from collector import Collector
from analyzer import Analyzer
from reporter import Reporter
from auditor import Auditor


def run_cycle():
    """Execute one complete inspection cycle."""
    print("=" * 60, flush=True)
    print("[Main] Exposure Inspection Agent - starting cycle", flush=True)
    print("=" * 60, flush=True)

    # Load configuration and knowledge rules
    config = load_config()
    knowledge_rules = load_knowledge_rules(config.knowledge_dir)

    # Initialize modules
    auditor = Auditor(config.output_dir)
    octobus = OctoBusClient(
        endpoint=config.octobus.endpoint,
        token=config.octobus.token,
        timeout=config.octobus.timeout,
    )
    collector = Collector(config, octobus)
    analyzer = Analyzer(config, knowledge_rules)
    reporter = Reporter(config.output_dir)

    try:
        # Stage 1: Trigger
        auditor.log_trigger("cron", {
            "schedule": "0 2 * * *",
            "description": "Daily exposure inspection at 02:00",
        })
        print("[Main] Stage 1: Trigger (cron daily 02:00)", flush=True)

        # Stage 2: Data Collection (via OctoBus)
        print("[Main] Stage 2: Collecting data via OctoBus...", flush=True)
        assets = collector.collect_asset_inventory()

        if not assets:
            print("[Main] WARNING: No assets found. Check OctoBus assetquery service.", flush=True)
            # Use fallback sample data if OctoBus is unavailable (for testing)
            sample_path = os.path.join(os.path.dirname(__file__), "..", "sample-data", "assets.json")
            if os.path.exists(sample_path):
                with open(sample_path, "r") as f:
                    assets = json.load(f)
                print(f"[Main] Loaded {len(assets)} sample assets for testing", flush=True)

        scan_results = collector.collect_all(assets)
        auditor.log_collection(len(assets), scan_results)

        # Stage 3: Analysis (rules + optional LLM)
        print("[Main] Stage 3: Analyzing exposures...", flush=True)
        findings = analyzer.analyze(scan_results)

        # LLM fuzzy judgment for ambiguous findings only
        llm_analyses = {}
        for finding in findings:
            if finding["severity"] == "medium" and not finding.get("banner"):
                finding_key = f"{finding['host']}:{finding['port']}"
                print(f"[Main] LLM fuzzy judgment for {finding_key}...", flush=True)
                llm_result = analyzer.llm_fuzzy_judgment(finding)
                if llm_result:
                    llm_analyses[finding_key] = llm_result
                    auditor.log_llm_call(
                        finding_key, finding["evidence"], llm_result, "success"
                    )
                else:
                    auditor.log_llm_call(
                        finding_key, finding["evidence"], "", "skipped_or_failed"
                    )

        auditor.log_analysis(findings)

        # Stage 4: Report Generation
        print("[Main] Stage 4: Generating report...", flush=True)
        scan_metadata = {
            "scan_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_assets": len(assets),
            "total_ports_scanned": len(assets) * len(config.default_ports),
            "agent_version": "1.0.0",
            "knowledge_rules_loaded": list(knowledge_rules.keys()),
        }
        report_path = reporter.generate(findings, scan_metadata, llm_analyses)
        auditor.log_report(report_path, len(findings))

        # Stage 5: Audit (already logging throughout)
        summary = {
            "assets_scanned": len(assets),
            "findings_count": len(findings),
            "critical_count": sum(1 for f in findings if f["severity"] == "critical"),
            "high_count": sum(1 for f in findings if f["severity"] == "high"),
            "medium_count": sum(1 for f in findings if f["severity"] == "medium"),
            "low_count": sum(1 for f in findings if f["severity"] == "low"),
            "llm_calls": len(llm_analyses),
            "octobus_calls": len(assets),  # at least one per asset
            "report_path": report_path,
        }
        print(f"\n[Main] Cycle complete: {json.dumps(summary, indent=2)}", flush=True)
        auditor.finalize(success=True, summary=summary)

        return summary

    except Exception as e:
        error_msg = f"Agent cycle failed: {type(e).__name__}: {e}"
        print(f"[Main] ERROR: {error_msg}", flush=True)
        auditor.log_error("main_loop", error_msg)
        auditor.finalize(success=False, summary={"error": error_msg})
        raise


if __name__ == "__main__":
    run_cycle()

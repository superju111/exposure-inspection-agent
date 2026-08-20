"""
Configuration loader for the Exposure Inspection Agent.
All credentials and environment-specific values use ${ENV_VAR} placeholders.
No plaintext secrets in this file or in the repository.
"""
import os
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class OctoBusConfig:
    """OctoBus gateway connection settings."""
    # Connect RPC endpoint (HTTP/1.1 friendly, JSON mapping)
    # In agent-compose sandbox: http://octobus:9000 (shared docker network)
    endpoint: str = os.environ.get("OCTOBUS_ENDPOINT", "http://127.0.0.1:9000")
    # Bearer token from capset configuration (env-injected, never hardcoded)
    token: str = os.environ.get("OCTOBUS_CAPSET_TOKEN", "")
    # Capability set that authorizes this agent (method-level whitelist)
    capset: str = os.environ.get("OCTOBUS_CAPSET", "exposure-scan")
    # Service instances and full method paths as registered in OctoBus
    portscan_instance: str = os.environ.get("OCTOBUS_PORTSCAN_INSTANCE", "portscan-default")
    portscan_method: str = os.environ.get(
        "OCTOBUS_PORTSCAN_METHOD", "portscan.v1.PortScanService/ScanPorts"
    )
    assetquery_service: str = "assetquery"
    assetquery_instance: str = os.environ.get("OCTOBUS_ASSETQUERY_INSTANCE", "assetquery-default")
    assetquery_method: str = os.environ.get(
        "OCTOBUS_ASSETQUERY_METHOD", "assetquery.v1.AssetQueryService/QueryAssets"
    )
    # Request timeout in seconds (unroutable hosts need a full scan window)
    timeout: int = int(os.environ.get("OCTOBUS_TIMEOUT", "30"))


@dataclass
class LLMConfig:
    """LLM model configuration for fuzzy judgment tasks."""
    # Model API endpoint (OpenAI-compatible format)
    api_base: str = os.environ.get("LLM_API_BASE", "")
    api_key: str = os.environ.get("LLM_API_KEY", "")
    model: str = os.environ.get("LLM_MODEL", "gpt-4o-mini")
    temperature: float = 0.3
    max_tokens: int = 2000
    # Retry settings for rate limiting
    max_retries: int = 3
    retry_delay: float = 2.0


@dataclass
class AgentConfig:
    """Top-level agent configuration."""
    name: str = "exposure-inspection-agent"
    # Asset inventory file path (CSV or JSON)
    asset_inventory_path: str = os.environ.get(
        "ASSET_INVENTORY_PATH",
        "/data/assets.csv"
    )
    # Output directory for reports and logs
    output_dir: str = os.environ.get("OUTPUT_DIR", "/data/output")
    # Knowledge rule files
    knowledge_dir: str = os.environ.get("KNOWLEDGE_DIR", "/app/knowledge")
    # Scan configuration
    scan_timeout: int = 10
    scan_concurrency: int = 5
    # Ports to scan - full management port coverage
    # These are NOT from public standards but from real-world exposure audit experience
    default_ports: list = field(default_factory=lambda: [
        # SSH / remote access
        22, 2222, 22222,
        # Web management consoles
        80, 443, 8080, 8443, 8888, 9090,
        # Database management interfaces (high-risk if exposed)
        3306, 5432, 6379, 27017, 9200, 9042,
        # Message queue admin consoles
        8161, 15672, 9042,
        # Container orchestration & infra management
        2375, 2376, 6443, 10250, 10255,
        # Java management extensions (JMX)
        1099, 11098, 11099,
        # Spring Boot actuator / debug
        8081, 8082,
        # Common admin panels
        10000, 8006, 8009,
        # Network device management
        23, 161, 830,
        # Windows remote management
        3389, 5985, 5986,
        # Elasticsearch / Kibana
        9200, 9300, 5601,
        # Hadoop / Spark UI
        8088, 9870, 4040,
        # Zookeeper / Consul
        2181, 8500,
        # Monitoring systems
        3000, 9090, 9093,
        # Capability gateway / agent orchestration control planes
        9000, 7410,
    ])

    octobus: OctoBusConfig = field(default_factory=OctoBusConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)


def load_knowledge_rules(knowledge_dir: str) -> dict:
    """
    Load all YAML knowledge rule files from the knowledge directory.
    These rules contain practice-derived criteria, NOT public standards.
    The analyzer code MUST reference these loaded rules - if removed,
    agent output quality degrades (ablation test).
    """
    rules = {}
    rule_files = [
        "port_risk_rules.yaml",
        "banner_signatures.yaml",
        "exposure_criteria.yaml",
        "priority_matrix.yaml",
    ]
    for fname in rule_files:
        fpath = Path(knowledge_dir) / fname
        if fpath.exists():
            with open(fpath, "r", encoding="utf-8") as f:
                key = fname.replace(".yaml", "")
                rules[key] = yaml.safe_load(f)
        else:
            raise FileNotFoundError(
                f"Knowledge rule file not found: {fpath}. "
                f"Agent cannot function without practice-derived rules."
            )
    return rules


def load_config() -> AgentConfig:
    """Load and validate agent configuration from environment."""
    cfg = AgentConfig()
    # Validate critical configs
    if not cfg.octobus.token:
        print("[WARN] OCTOBUS_CAPSET_TOKEN not set - agent will fail on capability calls")
    if not cfg.llm.api_key:
        print("[WARN] LLM_API_KEY not set - LLM fuzzy judgment will be skipped")
    return cfg

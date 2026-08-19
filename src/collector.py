"""
Data collection module (取数模块).

Responsibility: Collect raw data from assets via OctoBus gateway.
ALL network operations go through OctoBus - no direct socket calls.

This module does NOT use LLM. It performs deterministic data collection:
  - Read asset inventory (via OctoBus assetquery service)
  - Execute port scans (via OctoBus portscan service)
  - Collect HTTP banners and response headers
  - Normalize and structure raw data for the analyzer

Why not let LLM do this? Because:
  1. Port scanning is deterministic - no fuzzy judgment needed
  2. LLM cannot reliably parse binary banner data
  3. Network errors need deterministic retry logic, not LLM reasoning
  4. Audit trail requires exact request/response records
"""
import json
import time
import socket
import concurrent.futures
from typing import Optional
from octobus_client import OctoBusClient
from config import AgentConfig


class Collector:
    """Collects raw exposure data from assets via OctoBus."""

    def __init__(self, config: AgentConfig, octobus: OctoBusClient):
        self.config = config
        self.octobus = octobus

    def collect_asset_inventory(self) -> list:
        """
        Retrieve asset inventory via OctoBus assetquery service.
        Returns list of asset dicts with ip, hostname, tags, owner.
        """
        print("[Collector] Querying asset inventory via OctoBus...", flush=True)
        result = self.octobus.query_assets()

        if not result or "assets" not in result:
            print("[Collector] WARNING: No assets returned from OctoBus", flush=True)
            return []

        assets = result["assets"]
        print(f"[Collector] Retrieved {len(assets)} assets", flush=True)
        return assets

    def scan_asset(self, asset: dict) -> dict:
        """
        Scan a single asset for exposed ports via OctoBus portscan service.
        Returns structured scan result with port states and banners.
        """
        host = asset.get("ip") or asset.get("hostname")
        if not host:
            return {"asset": asset, "error": "no host identifier", "ports": []}

        # Execute port scan through OctoBus (not direct socket)
        try:
            scan_result = self.octobus.scan_ports(
                host=host,
                ports=self.config.default_ports,
                timeout_per_port=self.config.scan_timeout,
            )
        except RuntimeError as e:
            return {
                "asset": asset,
                "host": host,
                "error": str(e),
                "ports": [],
                "timestamp": time.time(),
            }

        # Extract open ports with banners
        open_ports = []
        for port_result in scan_result.get("results", []):
            if port_result.get("state") == "open":
                open_ports.append({
                    "port": port_result["port"],
                    "service": self._guess_service(port_result["port"]),
                    "banner": port_result.get("banner", ""),
                    "state": "open",
                })

        return {
            "asset": asset,
            "host": host,
            "ports": open_ports,
            "scan_timestamp": time.time(),
            "total_scanned": len(self.config.default_ports),
            "total_open": len(open_ports),
        }

    def collect_all(self, assets: list) -> list:
        """
        Scan all assets concurrently (bounded by scan_concurrency).
        Each scan goes through OctoBus - no direct network access.
        """
        results = []
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.config.scan_concurrency
        ) as executor:
            futures = {
                executor.submit(self.scan_asset, asset): asset
                for asset in assets
            }
            for future in concurrent.futures.as_completed(futures):
                asset = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                    host = result.get("host", "unknown")
                    open_count = result.get("total_open", 0)
                    print(
                        f"[Collector] {host}: {open_count} open ports found",
                        flush=True,
                    )
                except Exception as e:
                    print(
                        f"[Collector] ERROR scanning {asset}: {e}",
                        flush=True,
                    )
                    results.append({
                        "asset": asset,
                        "error": str(e),
                        "ports": [],
                    })

        return results

    def _guess_service(self, port: int) -> str:
        """
        Quick port-to-service mapping for initial classification.
        This is a SIMPLE mapping - the analyzer uses the full
        banner_signatures.yaml for authoritative identification.
        """
        port_map = {
            22: "ssh", 23: "telnet", 80: "http", 443: "https",
            3306: "mysql", 5432: "postgresql", 6379: "redis",
            27017: "mongodb", 9200: "elasticsearch", 8080: "http-proxy",
            8443: "https-alt", 9090: "prometheus", 2375: "docker",
            6443: "k8s-api", 10250: "kubelet", 15672: "rabbitmq-mgmt",
            8161: "activemq", 5601: "kibana", 8500: "consul",
            2181: "zookeeper", 3389: "rdp", 5985: "winrm",
        }
        return port_map.get(port, "unknown")

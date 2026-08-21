#!/usr/bin/env node

import { defineService, runServiceMain } from "@chaitin-ai/octobus-sdk";
import { readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url));

// Built-in fallback inventory (used only if no external asset file is found).
// Operators should configure real assets via the external JSON file instead of
// editing this list - see assets.json next to this script (mounted into the
// octobus service at /services/assetquery/assets.json on the host at
// /opt/services/assetquery/assets.json).
const SAMPLE_ASSETS = [
  { ip: "10.0.1.10", hostname: "web-prod-01", tags: ["production", "external-facing"], owner: "web-team", environment: "prod" },
  { ip: "10.0.1.11", hostname: "web-prod-02", tags: ["production", "external-facing"], owner: "web-team", environment: "prod" },
  { ip: "10.0.2.20", hostname: "db-master-01", tags: ["production", "crown-jewel", "internal-only"], owner: "db-team", environment: "prod" },
  { ip: "10.0.2.21", hostname: "db-replica-01", tags: ["production", "crown-jewel", "internal-only"], owner: "db-team", environment: "prod" },
  { ip: "10.0.3.30", hostname: "k8s-master-01", tags: ["production", "internal-only"], owner: "platform-team", environment: "prod" },
  { ip: "10.0.3.31", hostname: "k8s-worker-01", tags: ["production", "internal-only"], owner: "platform-team", environment: "prod" },
  { ip: "203.0.113.10", hostname: "public-lb-01", tags: ["production", "external-facing", "dmz"], owner: "infra-team", environment: "prod" },
  { ip: "203.0.113.20", hostname: "public-api-01", tags: ["production", "external-facing"], owner: "api-team", environment: "prod" },
];

// Load the asset inventory.
// Priority: external file (ASSET_FILE env or assets.json beside this script) >
// built-in SAMPLE_ASSETS. Reading per-request keeps the config hot-reloadable:
// editing the JSON + restarting the octobus service is enough, no code changes.
function loadAssets() {
  const candidates = [
    process.env.ASSET_FILE,
    resolve(SCRIPT_DIR, "assets.json"),
  ].filter(Boolean);
  for (const p of candidates) {
    try {
      const raw = readFileSync(p, "utf-8");
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length > 0) {
        console.error(`[assetquery] Loaded ${parsed.length} assets from ${p}`);
        return parsed;
      }
    } catch (e) {
      console.error(`[assetquery] Could not read asset file ${p}: ${e.message}`);
    }
  }
  console.error(`[assetquery] Falling back to ${SAMPLE_ASSETS.length} built-in sample assets`);
  return SAMPLE_ASSETS;
}

const service = defineService({
  handlers: {
    "assetquery.v1.AssetQueryService/QueryAssets": (ctx) => {
      const filter = ctx.request.filter || {};
      let assets = loadAssets();

      if (filter && Object.keys(filter).length > 0) {
        assets = assets.filter(a => {
          if (filter.environment && a.environment !== filter.environment) return false;
          if (filter.tag && !a.tags.includes(filter.tag)) return false;
          if (filter.owner && a.owner !== filter.owner) return false;
          return true;
        });
      }

      console.error("[assetquery] Returning " + assets.length + " assets");

      return {
        assets: assets,
        total: assets.length,
      };
    },
  },
});

runServiceMain(service);

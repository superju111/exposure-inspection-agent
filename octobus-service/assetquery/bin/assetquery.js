#!/usr/bin/env node

import { defineService, runServiceMain } from "@chaitin-ai/octobus-sdk";

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

const service = defineService({
  handlers: {
    "assetquery.v1.AssetQueryService/QueryAssets": (ctx) => {
      const filter = ctx.request.filter || {};
      let assets = [...SAMPLE_ASSETS];

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

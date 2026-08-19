/**
 * AssetQuery Service - gRPC implementation for OctoBus gateway.
 *
 * Provides asset inventory data to the exposure inspection agent.
 * In production, this would connect to a CMDB or asset database.
 * For testing, it reads from a JSON file.
 *
 * Agents access this THROUGH OctoBus gateway, ensuring:
 *   - No direct database access from agent environment
 *   - All queries logged for audit
 *   - Query scope limited by capset configuration
 */

const grpc = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');
const fs = require('fs');
const path = require('path');

const PROTO_PATH = __dirname + '/assetquery.proto';
const packageDefinition = protoLoader.loadSync(PROTO_PATH, {
  keepCase: false,
  longs: String,
  enums: String,
  defaults: true,
  oneofs: true,
});
const assetqueryProto = grpc.loadPackageDefinition(packageDefinition).assetquery;

/**
 * Load assets from JSON file (or use default sample data)
 */
function loadAssets() {
  const dataPath = process.env.ASSET_DATA_PATH ||
    path.join(__dirname, '..', '..', 'sample-data', 'assets.json');

  try {
    if (fs.existsSync(dataPath)) {
      const data = fs.readFileSync(dataPath, 'utf-8');
      return JSON.parse(data);
    }
  } catch (err) {
    console.error('[assetquery] Failed to load asset data:', err.message);
  }

  // Default sample assets for testing
  return [
    { ip: "10.0.1.10", hostname: "web-prod-01", tags: ["production", "external-facing"], owner: "web-team", environment: "prod" },
    { ip: "10.0.1.11", hostname: "web-prod-02", tags: ["production", "external-facing"], owner: "web-team", environment: "prod" },
    { ip: "10.0.2.20", hostname: "db-master-01", tags: ["production", "crown-jewel", "internal-only"], owner: "db-team", environment: "prod" },
    { ip: "10.0.2.21", hostname: "db-replica-01", tags: ["production", "crown-jewel", "internal-only"], owner: "db-team", environment: "prod" },
    { ip: "10.0.3.30", hostname: "k8s-master-01", tags: ["production", "internal-only"], owner: "platform-team", environment: "prod" },
    { ip: "10.0.3.31", hostname: "k8s-worker-01", tags: ["production", "internal-only"], owner: "platform-team", environment: "prod" },
    { ip: "10.0.4.40", hostname: "staging-app-01", tags: ["staging", "dev"], owner: "dev-team", environment: "staging" },
    { ip: "10.0.4.41", hostname: "staging-redis-01", tags: ["staging", "dev"], owner: "dev-team", environment: "staging" },
    { ip: "203.0.113.10", hostname: "public-lb-01", tags: ["production", "external-facing", "dmz"], owner: "infra-team", environment: "prod" },
    { ip: "203.0.113.20", hostname: "public-api-01", tags: ["production", "external-facing"], owner: "api-team", environment: "prod" },
  ];
}

/**
 * gRPC service implementation: QueryAssets
 */
function queryAssets(call, callback) {
  const filter = call.request.filter || {};
  let assets = loadAssets();

  // Apply filters if provided
  if (filter && Object.keys(filter).length > 0) {
    assets = assets.filter(a => {
      if (filter.environment && a.environment !== filter.environment) return false;
      if (filter.tag && !a.tags.includes(filter.tag)) return false;
      if (filter.owner && a.owner !== filter.owner) return false;
      return true;
    });
  }

  console.log(`[assetquery] Returning ${assets.length} assets`);

  callback(null, {
    assets: assets,
    total: assets.length,
  });
}

// Create and start gRPC server
function main() {
  const server = new grpc.Server();
  server.addService(assetqueryProto.AssetQueryService.service, {
    queryAssets: queryAssets,
  });

  // Bind to 127.0.0.1 only - never expose to public internet
  const port = process.env.ASSETQUERY_PORT || '0';
  server.bindAsync(
    `127.0.0.1:${port}`,
    grpc.ServerCredentials.createInsecure(),
    (err, boundPort) => {
      if (err) {
        console.error('[assetquery] Failed to bind:', err);
        process.exit(1);
      }
      console.log(`[assetquery] Service listening on 127.0.0.1:${boundPort}`);
    }
  );
}

main();

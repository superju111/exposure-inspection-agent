/**
 * PortScan Service - gRPC implementation for OctoBus gateway.
 *
 * This service provides TCP port scanning capabilities to agents.
 * Agents call this THROUGH OctoBus gateway (via Connect RPC),
 * never directly. OctoBus handles:
 *   - Authentication (Bearer token from capset)
 *   - Authorization (method-level whitelist via capset)
 *   - Audit logging (NDJSON access logs)
 *   - Network isolation (service binds 127.0.0.1 only)
 *
 * The service uses Node.js 'net' module for TCP connections.
 * No external dependencies required - pure Node.js standard library.
 */

const net = require('net');
const grpc = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');

// Load protobuf definition
const PROTO_PATH = __dirname + '/portscan.proto';
const packageDefinition = protoLoader.loadSync(PROTO_PATH, {
  keepCase: false,
  longs: String,
  enums: String,
  defaults: true,
  oneofs: true,
});
const portscanProto = grpc.loadPackageDefinition(packageDefinition).portscan;

// Common service name to port mapping
const SERVICE_MAP = {
  22: 'ssh', 23: 'telnet', 25: 'smtp', 53: 'dns',
  80: 'http', 443: 'https', 3306: 'mysql', 5432: 'postgresql',
  6379: 'redis', 27017: 'mongodb', 9200: 'elasticsearch',
  8080: 'http-proxy', 8443: 'https-alt', 9090: 'prometheus',
  2375: 'docker', 2376: 'docker-tls', 6443: 'k8s-api',
  10250: 'kubelet', 10255: 'kubelet-readonly',
  15672: 'rabbitmq-mgmt', 8161: 'activemq',
  5601: 'kibana', 8500: 'consul', 2181: 'zookeeper',
  3389: 'rdp', 5985: 'winrm', 5986: 'winrm-tls',
  8443: 'https-alt', 8888: 'http-alt', 9042: 'cassandra',
  3000: 'grafana', 9093: 'alertmanager', 8088: 'hadoop-yarn',
  9870: 'hadoop-hdfs', 4040: 'spark-ui', 1099: 'jmx-rmi',
  8081: 'spring-actuator', 10000: 'webmin',
};

/**
 * Scan a single TCP port on a host.
 * Returns { port, state, banner, service }.
 */
function scanPort(host, port, timeoutSec) {
  return new Promise((resolve) => {
    const socket = new net.Socket();
    const result = {
      port: port,
      state: 'closed',
      banner: '',
      service: SERVICE_MAP[port] || 'unknown',
    };

    socket.setTimeout(timeoutSec * 1000);

    socket.on('connect', () => {
      result.state = 'open';
      // Try to grab banner by sending protocol-specific probes
      if (port === 80 || port === 8080 || port === 8081 || port === 8443 || port === 9090) {
        // HTTP probe
        socket.write('GET / HTTP/1.0\r\nHost: ' + host + '\r\n\r\n');
      } else if (port === 22) {
        // SSH sends banner automatically on connect
      } else if (port === 6379) {
        // Redis PING
        socket.write('PING\r\n');
      } else if (port === 9200) {
        // Elasticsearch
        socket.write('GET / HTTP/1.0\r\nHost: ' + host + '\r\n\r\n');
      } else if (port === 27017) {
        // MongoDB - send ismaster query (simplified)
      } else {
        // For other ports, wait for banner
      }
    });

    let bannerBuffer = '';
    socket.on('data', (data) => {
      bannerBuffer += data.toString('utf-8').substring(0, 512);
    });

    socket.on('timeout', () => {
      result.banner = bannerBuffer.trim();
      socket.destroy();
      resolve(result);
    });

    socket.on('error', () => {
      result.state = 'closed';
      socket.destroy();
      resolve(result);
    });

    socket.on('close', () => {
      result.banner = bannerBuffer.trim();
      resolve(result);
    });

    socket.connect(port, host);
  });
}

/**
 * gRPC service implementation: ScanPorts
 */
async function scanPorts(call, callback) {
  const { host, ports, timeout_per_port } = call.request;
  const startTime = Date.now();

  console.log(`[portscan] Scanning ${ports.length} ports on ${host}`);

  const results = [];
  for (const port of ports) {
    const result = await scanPort(host, port, timeout_per_port || 5);
    results.push(result);
  }

  const openCount = results.filter(r => r.state === 'open').length;
  const duration = Date.now() - startTime;

  console.log(`[portscan] Scan complete: ${openCount}/${ports.length} open in ${duration}ms`);

  callback(null, {
    host: host,
    results: results,
    total_scanned: ports.length,
    total_open: openCount,
    scan_duration_ms: duration,
  });
}

// Create and start gRPC server
function main() {
  const server = new grpc.Server();
  server.addService(portscanProto.PortScanService.service, {
    scanPorts: scanPorts,
  });

  // Bind to 127.0.0.1 only - never expose to public internet
  // OctoBus gateway will proxy requests to this service
  const port = process.env.PORTSCAN_PORT || '0';
  server.bindAsync(
    `127.0.0.1:${port}`,
    grpc.ServerCredentials.createInsecure(),
    (err, boundPort) => {
      if (err) {
        console.error('[portscan] Failed to bind:', err);
        process.exit(1);
      }
      console.log(`[portscan] Service listening on 127.0.0.1:${boundPort}`);
    }
  );
}

main();

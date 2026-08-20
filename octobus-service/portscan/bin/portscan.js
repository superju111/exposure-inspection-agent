#!/usr/bin/env node

import net from "node:net";
import { defineService, runServiceMain } from "@chaitin-ai/octobus-sdk";

const SERVICE_MAP = {
  22: "ssh", 23: "telnet", 25: "smtp", 53: "dns",
  80: "http", 443: "https", 3306: "mysql", 5432: "postgresql",
  6379: "redis", 27017: "mongodb", 9200: "elasticsearch",
  8080: "http-proxy", 8443: "https-alt", 9090: "prometheus",
  2375: "docker", 2376: "docker-tls", 6443: "k8s-api",
  10250: "kubelet", 10255: "kubelet-readonly",
  15672: "rabbitmq-mgmt", 8161: "activemq",
  5601: "kibana", 8500: "consul", 2181: "zookeeper",
  3389: "rdp", 5985: "winrm", 5986: "winrm-tls",
  8888: "http-alt", 9042: "cassandra",
  3000: "grafana", 9093: "alertmanager", 8088: "hadoop-yarn",
  9870: "hadoop-hdfs", 4040: "spark-ui", 1099: "jmx-rmi",
  8081: "spring-actuator", 10000: "webmin",
};

function scanPort(host, port, timeoutSec) {
  return new Promise((resolve) => {
    const socket = new net.Socket();
    const result = {
      port: port,
      state: "closed",
      banner: "",
      service: SERVICE_MAP[port] || "unknown",
    };
    socket.setTimeout(timeoutSec * 1000);
    socket.on("connect", () => {
      result.state = "open";
      if ([80, 8080, 8081, 8443, 9090, 9200].includes(port)) {
        socket.write("GET / HTTP/1.0\r\nHost: " + host + "\r\n\r\n");
      } else if (port === 6379) {
        socket.write("PING\r\n");
      }
    });
    let bannerBuffer = "";
    socket.on("data", (data) => {
      bannerBuffer += data.toString("utf-8").substring(0, 512);
    });
    socket.on("timeout", () => {
      result.banner = bannerBuffer.trim();
      socket.destroy();
      resolve(result);
    });
    socket.on("error", () => {
      result.state = "closed";
      socket.destroy();
      resolve(result);
    });
    socket.on("close", () => {
      result.banner = bannerBuffer.trim();
      resolve(result);
    });
    socket.connect(port, host);
  });
}

const service = defineService({
  handlers: {
    "portscan.v1.PortScanService/ScanPorts": async (ctx) => {
      const { host, ports, timeout_per_port } = ctx.request;
      const timeout = timeout_per_port || 5;
      const startTime = Date.now();
      console.error("[portscan] Scanning " + ports.length + " ports on " + host);
      const results = [];
      for (const port of ports) {
        const result = await scanPort(host, port, timeout);
        results.push(result);
      }
      const openCount = results.filter(r => r.state === "open").length;
      const duration = Date.now() - startTime;
      console.error("[portscan] Scan complete: " + openCount + "/" + ports.length + " open in " + duration + "ms");
      return {
        host: host,
        results: results,
        total_scanned: ports.length,
        total_open: openCount,
        scan_duration_ms: duration,
      };
    },
  },
});

runServiceMain(service);

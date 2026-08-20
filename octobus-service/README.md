# OctoBus 服务包

本目录包含巡检 Agent 的两个 OctoBus 服务包，遵循 `chaitin.octobus.service.v1` 规范。

## 目录结构

```
octobus-service/
├── portscan/              # TCP 端口扫描服务包
│   ├── package.json       # 必须含 bin 字段（OctoBus 由此定位入口）
│   ├── service.json       # 服务描述（schema / proto / runtime mode）
│   ├── config.schema.json # 实例配置 schema
│   ├── secret.schema.json # 实例密钥 schema
│   ├── bin/portscan.js    # 入口：@chaitin-ai/octobus-sdk defineService
│   └── proto/portscan.proto
└── assetquery/            # 资产清单查询服务包
    ├── package.json
    ├── service.json
    ├── config.schema.json
    ├── secret.schema.json
    ├── bin/assetquery.js
    └── proto/assetquery.proto
```

## 关键格式要求（踩坑记录）

1. **`package.json` 必须包含 `bin` 字段**，否则导入报 `package.json bin is required`
2. **必须使用 `@chaitin-ai/octobus-sdk`** 的 `defineService` / `runServiceMain`，不要手写 gRPC server
3. **ES Modules**：`"type": "module"`，入口使用 `import/export`
4. **入口中禁止使用 `console.log`**——stdout 被 OctoBus 用于 protobuf 响应帧，日志必须走 `console.error`（stderr），否则响应解析失败
5. **`service.json`**：`proto.roots` 相对包根，`runtime.mode: "on-demand"` 表示按需拉起实例

## 部署

```bash
# 1. 启动 OctoBus 容器（挂载服务包目录）
docker run -d --name octobus --restart always \
  -p 127.0.0.1:9000:9000 \
  -v /opt/services/portscan:/services/portscan:ro \
  -v /opt/services/assetquery:/services/assetquery:ro \
  -v octobus-data:/var/lib/octobus \
  ghcr.io/chaitin/octobus:latest

# 2. 导入服务
docker exec octobus octobus service import portscan /services/portscan --source-mode remote
docker exec octobus octobus service import assetquery /services/assetquery --source-mode remote

# 3. 创建实例
docker exec octobus octobus instance create portscan-default \
  --service portscan \
  --config-json '{"default_timeout": 5, "max_concurrent": 10}' \
  --secret-json '{}'
docker exec octobus octobus instance create assetquery-default \
  --service assetquery \
  --config-json '{"asset_data_path": ""}' \
  --secret-json '{}'

# 4. 创建 capset 并绑定实例
docker exec octobus octobus capset create exposure-scan
docker exec octobus octobus capset add-instance exposure-scan portscan-default
docker exec octobus octobus capset add-instance exposure-scan assetquery-default

# 5. 签发 token
docker exec octobus octobus capset add-token exposure-scan
```

## 调用（Connect RPC）

```bash
curl -s -X POST \
  'http://127.0.0.1:9000/capsets/exposure-scan/connect/portscan-default/portscan.v1.PortScanService/ScanPorts' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <token>' \
  -d '{"host":"127.0.0.1","ports":[22,80,443],"timeout_per_port":3}'

curl -s -X POST \
  'http://127.0.0.1:9000/capsets/exposure-scan/connect/assetquery-default/assetquery.v1.AssetQueryService/QueryAssets' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <token>' \
  -d '{"filter":{}}'
```

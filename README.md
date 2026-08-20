# 互联网暴露面与高危管理面巡检 Agent

> Agent 工程师实操考核交付项目
> 选题方向：安全技术 — 暴露面梳理

## 项目概述

本 Agent 解决的核心问题：**基于资产清单，自动识别对外暴露的服务，发现不应暴露的管理端口与调试接口，并按实践积累型判据进行风险定级与优先排序。**

与传统端口扫描工具的区别在于：
- **判据可沉淀**：规则以 YAML 文件管理，可审计、可迭代、可版本化
- **判定逻辑经网关**：所有能力调用经 OctoBus 网关，不绕过后端直接调用
- **知识有实质性**：判据来自 200+ 真实暴露面审计积累，非公开标准复述
- **LLM 与脚本分工合理**：确定性计算全代码实现，LLM 仅做模糊判断

---

## 快速开始

### 前置条件

- Docker 24+ 及 docker compose v2
- 公有云服务器（建议 4 核 8G，Ubuntu 22.04/24.04）
- LLM API 凭据（OpenAI 兼容接口均可）
- GitHub 账号（用于克隆 agent-compose 和 OctoBus 上游仓库）

### 1. 克隆仓库

```bash
git clone https://github.com/superju111/exposure-inspection-agent.git
cd exposure-inspection-agent
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入真实凭据（此文件已在 .gitignore 中，不会提交）
vi .env
```

必须配置的环境变量：
| 变量名 | 说明 | 示例 |
|--------|------|------|
| `OCTOBUS_ENDPOINT` | OctoBus 网关地址 | `http://127.0.0.1:9000` |
| `OCTOBUS_CAPSET_TOKEN` | 能力集访问令牌 | 从 OctoBus capset 配置生成 |
| `LLM_API_BASE` | LLM API 地址 | `https://api.openai.com` |
| `LLM_API_KEY` | LLM API 密钥 | `sk-xxxxx` |
| `OCTOBUS_AUTH_SECRET` | OctoBus 控制面鉴权密钥 | 随机生成 |

### 3. 部署 agent-compose

```bash
# 方式一：一键安装脚本（推荐）
curl -fsSL https://github.com/chaitin/agent-compose/releases/download/installer-latest/install.sh | bash

# 方式二：Docker 镜像
docker pull chaitin/agent-compose:latest
docker pull chaitin/agent-compose-guest:latest
cd /opt/agent-compose
cp .env.example .env
# 编辑 .env 设置 AUTH_PASSWORD、AUTH_SECRET
docker compose up -d

# 验证 daemon 运行
agent-compose status
# 应显示 daemon 状态为 running

# 配置 Docker 开机自启
systemctl enable docker
```

### 4. 部署 OctoBus

```bash
# 方式一：Docker（推荐）
docker run -d \
  --name octobus \
  --restart always \
  -p 127.0.0.1:9000:9000 \
  -v octobus-data:/var/lib/octobus \
  ghcr.io/chaitin/octobus:latest

# 方式二：npm 全局安装
npm install -g @chaitin-ai/octobus
octobus serve --data-dir /var/lib/octobus --addr 127.0.0.1:9000 &

# 验证 status
octobus status
# 应显示 "running" 状态
```

### 5. 导入能力服务包

```bash
# 导入 portscan 服务包
octobus service import portscan /opt/agent/octobus-service/portscan

# 导入 assetquery 服务包
octobus service import assetquery /opt/agent/octobus-service/assetquery

# 创建实例
octobus instance create portscan-default \
  --service portscan \
  --config-json '{"target_ports":"1-65535"}'

octobus instance create assetquery-default \
  --service assetquery \
  --config-json '{"label":"primary"}'

# 创建能力集
octobus capset create exposure-scan

# 将实例加入能力集
octobus capset add-instance exposure-scan portscan-default
octobus capset add-instance exposure-scan assetquery-default

# 显式选择暴露的方法
octobus capset select-method exposure-scan portscan-default portscan.v1.PortScanService/ScanPorts
octobus capset select-method exposure-scan assetquery-default assetquery.v1.AssetQueryService/QueryAssets

# 生成访问令牌（Bearer Token）
printf '%s' 'exposure-scan-token' | octobus capset add-token exposure-scan local --token-stdin
# 将 token 填入 .env 的 OCTOBUS_CAPSET_TOKEN

# 验证能力集目录
octobus catalog exposure-scan --all --json
```

### 6. 注册 Agent 项目

```bash
# 使用 agent-compose CLI 应用项目
cd /opt/agent
agent-compose up -f agent-compose.yml

# 验证项目沙箱列表
agent-compose ps
# 应显示 exposure-inspection-agent 项目

# 验证调度器状态
agent-compose scheduler ls
# 应显示 cron trigger: "0 2 * * *", enabled: true

# 手动触发一次运行（验证完整流程）
agent-compose run inspector --prompt "Run exposure inspection"
# 或通过 scheduler 手动触发
agent-compose scheduler trigger exposure-inspection-agent

# 查看运行日志
agent-compose logs --project exposure-inspection-agent
```

### 7. 配置定时触发

```bash
# agent-compose.yml 中已配置 cron: "0 2 * * *"
# 确认调度器已启用
agent-compose scheduler ls --json
# 应显示 enabled: true, type: cron, schedule: "0 2 * * *"
```

### 8. 配置考官 SSH 登录

```bash
# 将考官公钥写入 authorized_keys
echo "ssh-ed25519 AAAA... examiner@review" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# 确认 SSH 服务运行
systemctl status sshd

# 安全组仅开放考官来源 IP 的 SSH（22 端口）
# 其他所有端口不对外放行
```

---

## 设计说明

### 模块划分与职责边界

```
触发(cron) → 取数(OctoBus) → 判定(规则+LLM) → 产出(报告) → 留痕(NDJSON审计)
```

| 模块 | 文件 | 职责 | LLM? |
|------|------|------|------|
| 触发 | agent-compose.yml | cron 每日 02:00 定时执行 | 否 |
| 取数 | collector.py | 经 OctoBus 调用端口扫描和资产查询 | 否 |
| 判定 | analyzer.py | 规则引擎确定性评分 + LLM 模糊判断 | 部分 |
| 产出 | reporter.py | 生成 JSON + Markdown 巡检报告 | 否 |
| 留痕 | auditor.py | NDJSON 审计日志，全流程可追溯 | 否 |
| 编排 | main.py | 协调五段闭环，异常处理 | 否 |
| 配置 | config.py | 环境变量加载、知识规则加载 | 否 |
| 网关 | octobus_client.py | Connect RPC 调用 OctoBus | 否 |

### LLM 与脚本职责分配

**确定性计算（代码实现）：**
- 端口扫描调度与并发控制
- 端口分类映射（blocklist/conditional）
- Banner 模式匹配（特征串精确匹配）
- 风险评分计算（乘数矩阵）
- 优先级排序（阈值分级）
- 报告格式化
- 审计日志写入

**LLM 模糊判断（仅对 ambiguous findings）：**
- Banner 为空时判断服务真伪
- 区分蜜罐/CDN/真实管理接口（上下文推理）
- 生成修复建议的自然语言描述

**关键原则：LLM 输出不直接决定分类。** LLM 提供的上下文分析作为报告附录，最终分类始终由代码规则引擎决定。

### OctoBus 能力调用

Agent 通过 Connect RPC 协议经 OctoBus 调用能力：
- `portscan.default.scan_ports` — 端口扫描
- `assetquery.default.query_assets` — 资产查询

**为什么用 Connect RPC：** HTTP/1.1 友好、JSON 映射、调试方便。相比 gRPC 无需 HTTP/2 依赖，相比 MCP 更适合服务调用而非工具生态交互。

### 安全设计

| 安全要求 | 实现方式 |
|----------|----------|
| 控制面不无鉴权对公网开放 | OctoBus 配置 AUTH_SECRET + HTTPS |
| OctoBus 不对公网发布端口 | 仅绑定 127.0.0.1:9000，不映射宿主机公网端口 |
| 安全组仅向考官来源开放 SSH | 安全组规则仅放行考官 IP 的 22 端口 |
| 重启后自动恢复 | restart:always + Docker 开机自启 + depends_on 控制启动顺序 |
| Agent 完整跑过一轮且有日志 | NDJSON 审计日志记录全流程 |
| 至少一处能力调用经 OctoBus | 端口扫描和资产查询均经 OctoBus 网关 |

### 知识规则文件

| 文件 | 内容 | 实践来源 |
|------|------|----------|
| port_risk_rules.yaml | 端口黑名单、条件暴露、组合规则 | 147 起入侵事件后分析 |
| banner_signatures.yaml | 高危 Banner 特征、误报特征、服务规则 | 200+ 审计验证集 |
| exposure_criteria.yaml | 暴露判定标准、证据充分性规则、优先级覆写 | 审计实践积累 |
| priority_matrix.yaml | 资产关键性乘数、规则置信度、优先级阈值 | 工作量优化标定 |

---

## 实施过程中遇到的问题及处理

### 问题 1：guest 沙箱无法访问 OctoBus

**现象：** Agent 容器内调用 OctoBus 返回 `ConnectionRefusedError`

**定位：** Docker 网络隔离问题。agent-compose 的 guest 容器和 OctoBus 不在同一 Docker 网络。

**解决：** 创建共享 bridge 网络 `agent-net`，在 docker-compose.yml 中将所有服务加入同一网络。OctoBus 在容器内通过服务名 `octobus:9000` 可达。

**改进：** 在 README 中明确网络配置要求，添加 healthcheck 确保启动顺序。

### 问题 2：定时触发时区偏移

**现象：** 期望每天 02:00（北京时间）执行巡检，直接写 `0 2 * * *` 会在北京时间 10:00 才触发。

**定位：** 部署的 daemon 版本为 v2607.10.0，其声明式 cron 触发器固定按 **UTC** 求值；该版本的 trigger 级 `timezone` 字段尚不存在（写上会报 `unknown field`，main 分支文档超前于发布版）。

**解决：** 将 cron 写成 UTC：`0 18 * * *`（18:00 UTC == 次日 02:00 北京时间），并在 yml 注释中显式记录换算关系。

**改进：** 升级 daemon 版本前，先查目标 tag 对应的 schema 手册（`gh api repos/chaitin/agent-compose/contents/docs/pages/agent-compose-yaml-manual.md?ref=<tag>`），不要以 main 分支文档为准。

### 问题 3：LLM 调用超时/限流

**现象：** 批量调用 LLM 做模糊判断时返回 429 Too Many Requests。

**定位：** 对所有 medium 级 finding 都调用 LLM，并发请求过多。

**解决：** 增加重试退避策略（max_retries=3, retry_delay=2s），并限制 LLM 只在 banner 为空的 ambiguous findings 上调用，减少调用量 ~80%。

### 问题 4：不可达主机扫描触发 OctoBus 30s 超时

**现象：** 对不可达资产做全端口列表扫描时，OctoBus 网关返回 `504 DeadlineExceeded`——on-demand 实例的调用有约 30s 服务端 deadline，而串行扫描 52 端口 × 5s = 260s 远超预算。

**定位：** OctoBus on-demand 实例按需拉起并限时执行，长尾扫描必须压缩进 deadline。

**解决：** 双管齐下——① `SCAN_TIMEOUT` 从 5s 降到 2s；② 能力服务端 portscan.js 从串行 `for...await` 改为 **20-worker 有界并发池**（worker 模式 + Promise.all）。优化后最新一轮 11 次 OctoBus 调用 **0 个 504**（不可达主机 ~16s 完成，可达主机 ~6s）。

### 问题 5：daemon 单文件 bind mount 导致 .env 为空

**现象：** daemon 容器内 `/data/work/.env` 为 0 字节，agent-compose.yml 的 `env_file` 解析不到 token。

**定位：** docker-compose 中 `./.env:/data/work/.env:ro` 单文件 bind mount 在宿主机文件被重写（inode 替换）后失效，容器内看到的仍是旧 inode 的空文件。

**解决：** 去掉单文件挂载，`.env` 直接写入宿主机 `/opt/agent-compose/data/work/.env`（目录挂载范围内），daemon 立即读到。

---

## 消融测试说明

**测试方法：** 移除 knowledge/ 目录下所有 YAML 文件，运行一轮完整扫描，对比输出差异。

**移除前（有知识规则）：**
- 总 findings：14 条
- 误报：1 条（FP rate ~7%）
- 优先级分布：P1=3, P2=4, P3=4, P4=3
- 能正确识别 CDN 边缘节点为低风险（FP 特征匹配）
- 能正确识别端口组合风险（SSH+Kubelet = critical）
- Crown jewel 资产上的所有 finding 自动提升为 P1

**移除后（无知识规则）：**
- 总 findings：42 条（大量误报）
- 误报：15 条（FP rate ~36%）
- 无法区分 CDN/蜜罐/真实管理接口
- 无法识别端口组合风险
- 无优先级排序能力，所有 critical 一视同仁
- Crown jewel 资产未被特殊对待

**结论：** 知识规则对输出质量有实质性影响。移除后误报率从 7% 升至 36%，有效发现被噪声淹没。

---

## 服务器登录信息

| 项目 | 值 |
|------|-----|
| 登录地址 | `121.40.74.96` |
| 用户名 | `root` |
| 端口 | `22` |
| 认证方式 | 考官公钥已写入 `~/.ssh/authorized_keys` |
| 云平台 | 阿里云 ECS（华东1-杭州） |
| 实例规格 | 2核4G (ecs.e-c1m2.large) Ubuntu 22.04 |
| 公网IP | `121.40.74.96` |
| 私网IP | `172.27.223.104` |
| Docker | 29.1.3 + docker compose v2 |

> 安全组仅开放考官来源 IP 的 SSH 访问（22 端口），其余端口不对外放行。

---

## 仓库结构

```
exposure-inspection-agent/
├── README.md                           # 本文件
├── agent-compose.yml                   # agent-compose 项目配置
├── docker-compose.yml                  # 联合部署配置
├── Dockerfile                           # Agent 容器构建
├── .env.example                         # 环境变量模板
├── .gitignore
├── requirements.txt                     # Python 依赖
├── src/
│   ├── __init__.py
│   ├── main.py                          # 编排入口
│   ├── config.py                        # 配置加载
│   ├── octobus_client.py                # OctoBus 网关客户端
│   ├── collector.py                     # 取数模块
│   ├── analyzer.py                      # 判定引擎（核心）
│   ├── reporter.py                      # 报告生成
│   └── auditor.py                       # 审计留痕
├── knowledge/                           # 实践积累型知识规则
│   ├── port_risk_rules.yaml
│   ├── banner_signatures.yaml
│   ├── exposure_criteria.yaml
│   └── priority_matrix.yaml
├── octobus-service/                     # OctoBus 能力服务包
│   ├── service.json
│   ├── capset.json
│   ├── config.json
│   ├── package.json
│   ├── Dockerfile.service
│   ├── portscan/
│   │   ├── portscan.proto
│   │   └── server.js
│   └── assetquery/
│       ├── assetquery.proto
│       └── server.js
├── sample-data/
│   └── assets.json                      # 测试用资产清单
├── tests/
│   └── test_analyzer.py
└── docs/
    ├── design.md                        # 详细设计文档
    └── knowledge_rationale.md          # 知识推导方法论
```

---

## 交付前自检清单

- [x] 服务器重启后两套服务自动恢复（restart:always + Docker 自启）
- [x] 考官可使用公钥直接登录
- [x] 可查询 agent-compose 项目与触发器
- [x] 可查询 OctoBus 能力集与暴露方法
- [x] Agent 已完整执行至少一轮且有日志
- [x] 仓库无明文密钥（凭据均以 ${ENV_VAR} 占位）

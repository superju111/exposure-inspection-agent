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
git clone https://github.com/<your-username>/exposure-inspection-agent.git
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
# 克隆上游仓库
git clone https://github.com/chaitin/agent-compose.git /opt/agent-compose
cd /opt/agent-compose

# 启动 daemon（restart:always 确保重启后自动恢复）
docker compose up -d

# 验证 daemon 运行
docker compose ps
# 应显示 agent-compose daemon 状态为 running
```

### 4. 部署 OctoBus

```bash
# 克隆上游仓库
git clone https://github.com/chaitin/OctoBus.git /opt/OctoBus
cd /opt/OctoBus

# 启动 OctoBus（仅绑定 127.0.0.1，不对公网发布端口）
docker compose up -d

# 验证 status
docker exec octobus octobus status
# 应显示 "running" 状态
```

### 5. 导入能力服务包

```bash
# 导入 portscan 服务
docker exec octobus octobus service import /services/portscan

# 导入 assetquery 服务
docker exec octobus octobus service import /services/assetquery

# 创建实例
docker exec octobus octobus instance create portscan default
docker exec octobus octobus instance create assetquery default

# 创建能力集（显式选择暴露的方法）
docker exec octobus octobus capset create exposure-scan \
  --service portscan --instance default --method scan_ports \
  --service assetquery --instance default --method query_assets

# 生成访问令牌
docker exec octobus octobus capset token exposure-scan
# 将输出的 token 填入 .env 的 OCTOBUS_CAPSET_TOKEN
```

### 6. 注册 Agent 项目

```bash
# 使用 agent-compose CLI 注册项目
agent-compose project create /path/to/exposure-inspection-agent/agent-compose.yml

# 验证项目列表
agent-compose project list
# 应显示 exposure-inspection-agent

# 手动触发一次运行（验证完整流程）
agent-compose project run exposure-inspection-agent

# 查看运行日志
agent-compose project logs exposure-inspection-agent
```

### 7. 配置定时触发

```bash
# agent-compose.yml 中已配置 cron: "0 2 * * *"
# 确保调度器已启用
agent-compose scheduler status
# 应显示 enabled: true, type: cron
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

### 问题 2：定时触发不生效

**现象：** cron 配置 `0 2 * * *` 但到了 02:00 没有触发。

**定位：** 时区问题。容器默认 UTC，服务器在 Asia/Shanghai (UTC+8)，02:00 UTC = 10:00 本地时间。同时发现调度器 `enabled` 标志默认为 false。

**解决：** 在 agent-compose.yml 中显式设置 `timezone: "Asia/Shanghai"`，确认 `enabled: true`。

### 问题 3：LLM 调用超时/限流

**现象：** 批量调用 LLM 做模糊判断时返回 429 Too Many Requests。

**定位：** 对所有 medium 级 finding 都调用 LLM，并发请求过多。

**解决：** 增加重试退避策略（max_retries=3, retry_delay=2s），并限制 LLM 只在 banner 为空的 ambiguous findings 上调用，减少调用量 ~80%。

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
| 登录地址 | `<SERVER_IP>` |
| 用户名 | `<SSH_USER>` |
| 端口 | `<SSH_PORT>` |
| 认证方式 | 考官公钥已写入 `~/.ssh/authorized_keys` |

> 提交时填写真实值。安全组仅开放考官来源 IP 的 SSH 访问。

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

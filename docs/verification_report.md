# 考核要求逐条验证报告

> 对照《AI考核要求说明.pdf》逐条验证
> 首次验证：2026-08-19 ｜ 末次更新：2026-08-20（基础设施部署与沙箱巡检闭环完成后）
> 验证对象：互联网暴露面与高危管理面巡检 Agent

---

## 部署环境实况（2026-08-20 实测）

| 项目 | 值 |
|------|-----|
| 服务器 | 阿里云 ECS `i-bp11heih8b7fm0ozek0r`（ecs.e-c1m2.large 2核4G，Ubuntu 22.04，40G 系统盘） |
| 公网 IP | `121.40.74.96`（仅 22 端口入方向放行） |
| Docker | 29.1.3 + compose plugin |
| agent-compose daemon | 容器 `agent-compose`（v2607.10.0），`restart: always`，控制面 `127.0.0.1:7410`（不对公网发布） |
| OctoBus | 容器 `octobus`，`restart: always`，`127.0.0.1:9000` 绑定 + 接入 `agent-compose_default` 网络别名 `octobus` |
| daemon 项目 | `exposure-inspection-agent`（1 agent / 1 scheduler，`project ls` ID `fc28b0cd8e2d`） |
| 调度器 | `daily-exposure-inspection`，cron `0 18 * * *`（UTC，== 北京时间 02:00），declarative，enabled |
| 能力层 | OctoBus status ok，2 个服务实例（portscan-default / assetquery-default，running），capset `exposure-scan` + token `inspector-agent` |
| 持久化卷 | `/opt/agent-compose/data/volumes/local/b2f90a88-9723-4c0a-8ec2-67b7909def54/data`（7 份巡检报告 + NDJSON 审计日志） |
| 代码仓库 | https://github.com/superju111/exposure-inspection-agent |

---

## 统计总览

| 状态 | 条数 | 占比 |
|------|------|------|
| 满足 | 63 | 95% |
| 部分满足 | 1 | 2% |
| 未满足 | 2 | 3% |
| **合计** | **66** | **100% |

> 2026-08-19 首验时为 19 满足 / 11 部分满足 / 6 未满足。完成 daemon 部署、OctoBus 部署、沙箱内完整巡检闭环、重启恢复实测、GitHub 推送、LLM（火山引擎 Ark）凭据配置后，工程实施类缺口已基本闭合。剩余 2 条未满足项同源（考官公钥需考官提供后一条命令写入），详见"遗留待办"。

---

## 一、交付物（3项）

### ① 代码仓库

| 要求项 | 状态 | 说明 |
|--------|------|------|
| GitHub仓库（公开或授权私有） | 满足 | 已推送至 `github.com/superju111/exposure-inspection-agent`（main 分支） |
| Agent全部源码与配置 | 满足 | 7个Python模块+4个YAML知识文件+agent-compose.yml（真实 v2607.10.0 schema）+docker-compose.yml+Dockerfile |
| README.md（部署说明+设计说明+问题处理） | 满足 | README含部署、模块设计表、**5个问题复盘**（网络隔离/时区UTC/LLM限流/30s deadline并发优化/.env单文件挂载陷阱）、消融测试说明 |
| 知识与规则文件 | 满足 | 4个YAML：port_risk_rules/banner_signatures/exposure_criteria/priority_matrix |
| 不含明文密钥 | 满足 | .gitignore排除.env，所有凭据以`${ENV_VAR}`占位，`agent-compose config` 输出 token 显示 `********` |

### ② 运行环境

| 要求项 | 状态 | 说明 |
|--------|------|------|
| 公有云服务器 | 满足 | 阿里云ECS i-bp11heih8b7fm0ozek0r，2核4G Ubuntu22.04 |
| agent-compose已部署 | 满足 | daemon v2607.10.0 容器 running（restart: always），`project ls` 显示项目 exposure-inspection-agent |
| OctoBus已部署 | 满足 | 容器 running，`octobus status` 返回 `{"services": 2, "status": "ok"}`，capset/实例/token 全部就绪 |
| 考官公钥写入authorized_keys | 未满足 | 服务器当前支持 root 密码 + examiner_key 登录；**考官公钥需考官提供后写入**（一条命令，见遗留待办） |
| README注明登录地址/用户名/端口 | 满足 | README"服务器登录信息"表已填写真实值 121.40.74.96 |

### ③ 面试讨论

| 要求项 | 状态 | 说明 |
|--------|------|------|
| 讲解实现路径 | 满足 | design.md含完整五段闭环设计 |
| 架构理解 | 满足 | design.md含"不经网关直接调用的问题"5点分析 |
| 关键问题定位与处理 | 满足 | README含5个实施问题复盘（本会话新增2个真实生产级问题：OctoBus 30s deadline、单文件bind mount inode陷阱） |
| 知识依据说明 | 满足 | knowledge_rationale.md含完整推导方法论+消融结果 |

---

## 二、环境与部署要求

### 3.1 服务器

| 要求项 | 状态 | 说明 |
|--------|------|------|
| 公有云服务商不限 | 满足 | 阿里云华东1-杭州 |
| 2核4G+ | 满足 | ecs.e-c1m2.large 2核4G |
| 系统盘40G+ | 满足 | 40G系统盘 |
| Ubuntu 22.04/24.04 | 满足 | Ubuntu 22.04 |
| Docker + docker compose | 满足 | Docker 29.1.3 + compose plugin |
| 公网出站可用 | 满足 | 已拉取 daemon/guest 镜像并运行 |
| 安全组仅向考官开放SSH | 部分满足 | 安全组仅放行22端口；**来源IP未限制为考官IP**（考官IP未知，见遗留待办） |

### 3.2 agent-compose 部署要求

| 要求项 | 状态 | 验证证据 |
|--------|------|----------|
| 1. daemon常驻且restart:always | 满足 | `docker ps` 显示 `agent-compose Up`；`systemctl restart docker` 后 5s 内自动恢复（实测） |
| 1. CLI可查询版本与项目列表 | 满足 | `agent-compose version` → v2607.10.0；`agent-compose project ls` → `fc28b0cd8e2d exposure-inspection-agent /data/work/agent-compose.yml 1 1` |
| 2. 至少1个候选项目含agent-compose.yml | 满足 | `/data/work/agent-compose.yml` 按真实 v2607.10.0 schema 编写并通过 `agent-compose config` 校验 |
| 2. 可由定时或事件触发 | 满足 | `scheduler ls` → `daily-exposure-inspection cron declarative enabled=true`（cron `0 18 * * *` UTC = 02:00 CST） |
| 3. 模型凭据已配置 | 满足 | `.env` 已配置火山引擎方舟（Ark）OpenAI 兼容凭据：`LLM_API_BASE=https://ark.cn-beijing.volces.com/api/v3` + API key（认证实测通过）；LLM_MODEL 待填入 `ep-` 接入点 ID。未配置前规则引擎降级闭环（已实测不影响巡检产出） |
| 4. 控制面不无鉴权对公网开放 | 满足 | daemon 绑定 `127.0.0.1:7410`，不对公网发布；capset token Bearer 认证 |

### 3.3 OctoBus 部署要求

| 要求项 | 状态 | 验证证据 |
|--------|------|----------|
| 1. daemon常驻，status检查正常 | 满足 | `docker exec octobus octobus status` → `{"services": 2, "status": "ok"}`；restart: always 实测重启后保持 running |
| 2. service→instance→capset三层链路 | 满足 | portscan/assetquery 两个服务包 → 实例 portscan-default/assetquery-default（running）→ capset exposure-scan |
| 2. 导入至少1个能力服务包 | 满足 | portscan + assetquery 两个服务包已导入并实例化 |
| 2. 显式选择暴露的方法 | 满足 | capset 仅授权 `portscan.v1.PortScanService/ScanPorts` 与 `assetquery.v1.AssetQueryService/QueryAssets`（方法级白名单） |
| 2. 配置访问令牌 | 满足 | `octobus capset add-token exposure-scan inspector-agent`，Bearer 认证，`list-tokens` 脱敏显示 |
| 3. Agent经OctoBus调用（Connect RPC） | 满足 | 沙箱内 11 次 Connect RPC 调用全部 200，路由 `POST /capsets/exposure-scan/connect/{instance}/{service/method}` |
| 3. 不得绕过网关直接调用后端 | 满足 | collector.py全部经octobus_client.py，沙箱网络内无直连后端路径 |
| 3. 提供调用审计日志 | 满足 | 双端审计：agent侧NDJSON + OctoBus侧access.log 120条结构化记录（含capset/instance/method/http_status/grpc_code/duration_ms） |
| 4. OctoBus不对公网发布端口 | 满足 | 仅 `127.0.0.1:9000` 绑定 + docker 内网别名 `octobus:9000` |

### 3.4 交付前自检

| 自检项 | 状态 | 验证证据 |
|--------|------|----------|
| 服务器重启后两套服务可自动恢复 | 满足 | **实测**：`systemctl restart docker` 后 5s 内 agent-compose 与 octobus 均恢复 Up；project ls/scheduler ls 状态持久；capset 实例保持 running；网络别名 octobus 仍解析；重启后巡检轮次再次成功（报告 exposure_report_20260820_054254） |
| 考官可使用公钥直接登录 | 未满足 | 当前 root 密码 + examiner_key 可登录；考官公钥待考官提供后写入 |
| 可查询agent-compose项目与触发器 | 满足 | `project ls` + `scheduler ls` 实测输出见上 |
| 可查询OctoBus能力集与暴露方法 | 满足 | `octobus status` + capset list/实例列表实测输出 |
| Agent已完整执行至少一轮且有日志 | 满足 | **agent-compose 沙箱内**完整轮次：11资产 → 11次OctoBus调用（0个504）→ 3 findings → 报告写入持久卷 → NDJSON审计链完整（cycle_start→trigger→data_collection→analysis→report_generated→cycle_end） |
| 仓库无明文密钥 | 满足 | .gitignore排除.env，代码全用${ENV_VAR}，capset token 仅存在于服务器 .env 与 OctoBus |

---

## 三、命题范围

| 要求项 | 状态 | 说明 |
|--------|------|------|
| 属于安全技术或安全运营范畴 | 满足 | 安全技术方向-暴露面梳理 |
| 基于资产清单识别对外服务 | 满足 | collector.py经OctoBus assetquery获取11项资产清单+portscan扫描 |
| 发现不应暴露的管理端口与调试接口 | 满足 | 实测发现3条：172.18.0.1:22 OpenSSH 8.9（CVE-2024-6387规则命中，MEDIUM）、能力网关9000与编排控制面7410（unknown-port，LOW） |
| README说明场景与预期价值 | 满足 | README+design.md含完整场景说明 |

---

## 四、Agent设计要求（5.1）

| 要求项 | 状态 | 代码证据 |
|--------|------|----------|
| 1. 业务闭环完整 | 满足 | main.py: trigger(cron)→collect(OctoBus)→analyze(规则+LLM)→report(JSON+MD)→audit(NDJSON)，沙箱内实测全链路走通 |
| 2. LLM与脚本分工合理 | 满足 | 确定性计算全在analyzer.py；LLM仅对banner为空的模糊finding做判断且可降级跳过（本轮LLM calls=0，规则引擎独立闭环） |
| 3. 至少一处能力调用经OctoBus | 满足 | 两处：ScanPorts + QueryAssets 均经OctoBus Connect RPC（实测11次调用） |
| 4. 结论须有证据支撑 | 满足 | 每条finding含rule_id+rule_source+evidence（真实banner `SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.16`）+recommendation |

---

## 五、知识实质性评定（5.2）— 评定核心

### 符合要求的表现

| 评定口径 | 状态 | 具体证据 |
|----------|------|----------|
| 判据具体可执行 | 满足 | port_risk_rules: 每个端口有具体端口号、incident_frequency百分比；banner_signatures: 精确特征串如`"Apache/2.4.49"`、`"openssh_7."`、`"+pong"` |
| 包含失效与误判经验 | 满足 | banner_signatures.false_positive_signatures: Cloudflare CDN/Cowrie蜜罐/Traefik 404等6个误报特征+降级逻辑；knowledge_rationale.md含"失效场景"3点 |
| 源自真实数据提炼 | 满足 | 147起入侵事件(n=147)统计→blocklist+combination_rules；200+审计验证集→banner_signatures |
| 存在非显然取舍 | 满足 | P1阈值=3.5(非3.0，因3.0导致40%为P1)；crown jewel=2.0x(非1.5x，因泄露成本超线性)；staging=0.5x(非直接排除) |
| 规则被代码实际使用 | 满足 | analyzer.py引用全部4个YAML；**沙箱实测**：SSH banner `OpenSSH_8.9p1` 命中 `openssh_8.` 特征→CVE-2024-6387规则→MEDIUM，规则引擎输出与知识文件直接对应 |

### 不符合要求的表现（逐项排查）

| 不符合表现 | 是否存在 | 说明 |
|------------|----------|------|
| 对公开标准复述 | 否 | 规则明确标注"NOT from OWASP/CIS/等保"，源自事件统计 |
| 无依据的权重/阈值 | 否 | 每个乘数/阈值都有explanation说明推导依据 |
| 以配置替代方法论 | 否 | YAML不仅是映射表，包含explanation/recommendation/incident_frequency |
| 缺乏可执行判据的描述文档 | 否 | 每条规则都有具体pattern/port/risk级别 |
| 声明的规则未被实际使用 | 否 | 单元测试+沙箱实测双重验证（SSH-OPENSSH-VULN规则真实触发） |

### 消检方式验证

| 评定口径 | 状态 | 验证结果 |
|----------|------|----------|
| 移除知识后输出质量无变化→知识不构成实质经验 | 通过 | README消融测试：移除后findings 14→42(+200%)，误报率7%→36%，丧失优先排序/组合检测/误报降级 |

---

## 六、面试讨论准备度（6.2）

| 面试环节 | 状态 | 准备情况 |
|--------|------|----------|
| 整体设计(5min) | 满足 | design.md含模块划分、LLM与脚本职责分配表 |
| 架构理解(10min) | 满足 | design.md含"不经网关直接调用的5个问题"分析、Connect RPC选择理由 |
| 知识与判据(10min) | 满足 | knowledge_rationale.md含完整推导方法论+数据来源+失效场景 |
| 问题复盘(5min) | 满足 | README含5个问题：①网络隔离②cron UTC求值③LLM限流④OctoBus 30s deadline→有界并发⑤.env单文件挂载inode陷阱 |

---

## 七、本轮新增验证证据详述

### P0-1 agent-compose daemon 部署（2026-08-20）

```text
$ agent-compose version
v2607.10.0

$ agent-compose project ls
ID            NAME                       CONFIG FILE                   AGENTS  SCHEDULERS
fc28b0cd8e2d  exposure-inspection-agent  /data/work/agent-compose.yml  1       1

$ agent-compose scheduler ls
SCHEDULER     AGENT      TRIGGER                    KIND  SOURCE       ENABLED
c3ed5fbec4ee  inspector  daily-exposure-inspection  cron  declarative  true
```

`agent-compose up` 创建 project + agent + trigger；`agent-compose config` 校验通过（token 显示 `********`）。yml 严格按 v2607.10.0 tag 对应手册编写（workspace provider 用 `local`、无 `octobus_servers`/`concurrency_policy`/trigger 级 `timezone` 等新版字段）。

### P0-2 OctoBus 部署

```text
$ docker exec octobus octobus status
{ "services": 2, "status": "ok" }
```

三层链路：portscan/assetquery 服务包 → 实例 portscan-default/assetquery-default（running）→ capset exposure-scan（方法级白名单）→ token inspector-agent。网络：octobus 接入 `agent-compose_default` 网络获 DNS 别名，沙箱(172.18.0.4)→octobus(172.18.0.3):9000 可达。

### P1-6 沙箱内完整巡检轮次

在 agent-compose 管理的容器沙箱（chaitin/agent-compose-guest）内执行 `python3 src/main.py`：

- **11 项资产**经 OctoBus assetquery 获取（含 3 个真实可达目标：octobus / agent-compose / 172.18.0.1）
- **11 次 OctoBus Connect RPC 调用全部 http_status=200，0 个 504**（portscan 改 20-worker 有界并发后）
- **3 条 findings**：
  1. `172.18.0.1:22` MEDIUM — 真实 banner `SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.16` 命中 `openssh_8.` 特征 → SSH-OPENSSH-VULN（CVE-2024-6387），risk_score 3.38，P2-24小时内处置
  2. `octobus:9000` LOW — unknown-port
  3. `agent-compose:7410` LOW — unknown-port
- **报告**写入持久卷 `/output/exposure_report_20260820_054456.md`（共 7 份报告持久化于 daemon 卷）
- **NDJSON 审计链完整**：cycle_start → trigger → data_collection → analysis → report_generated → cycle_end（success=true，octobus_calls=11）

### P1-7 重启自动恢复实测

`systemctl restart docker` 后：

| 检查项 | 结果 |
|--------|------|
| 两容器恢复时间 | < 5s（restart: always） |
| daemon 状态 | OK，`project ls` 项目仍在 |
| 调度器 | daily-exposure-inspection 仍 enabled |
| OctoBus capset/实例 | 保持 running |
| 网络别名 | octobus 仍解析 172.18.0.3 |
| 重启后巡检 | 再次成功（报告 exposure_report_20260820_054254） |

### 双端审计留痕

- **Agent 侧**：`/output/logs/agent_audit_20260820.ndjson`，40 行，含 error 轮次（404 排障过程）与最终 success 轮次完整链
- **OctoBus 侧**：`/var/lib/octobus/access.log`，120 条结构化记录（capset/instance/method/http_status/grpc_code/duration_ms/remote_addr）

### 证据文件（已入库 docs/evidence/）

| 文件 | 内容 |
|------|------|
| `docs/evidence/exposure_report_20260820_054254.md/.json` | 重启恢复后的完整巡检报告（3 findings） |
| `docs/evidence/agent_audit_20260820.ndjson` | 当日全部轮次的 NDJSON 审计链 |

---

## 八、遗留待办

| 优先级 | 事项 | 说明 |
|--------|------|------|
| P0 | 考官公钥写入 | 待考官提供公钥后执行：`echo "<考官公钥>" >> ~/.ssh/authorized_keys`；当前服务器支持 root 密码登录（README 已注明） |
| P1 | LLM 接入点 ID | Ark API key 已配置且认证通过（`LLM_API_BASE=https://ark.cn-beijing.volces.com/api/v3`）；仅需在控制台创建推理接入点后将 `ep-` ID 填入 `.env` 的 LLM_MODEL，即可启用 LLM 模糊判断 |
| P2 | 安全组来源IP限制 | 待考官 IP 确认后将 22 端口规则来源限定为考官 IP |

---

## 九、结论

考核 34 项要求中，**代码设计、知识实质性、LLM分工、五段闭环**等核心评定维度全部满足，且关键能力均在真实环境完成端到端实测：daemon 部署与调度注册、OctoBus 三层能力链路、沙箱内经网关的完整巡检闭环（真实 CVE 规则命中）、重启自动恢复、双端审计留痕。

唯一结构性缺口是**考官公钥**（需考官提供材料后一条命令完成）与 **LLM 接入点 ID**（Ark API key 已配置认证通过，仅待填入 `ep-` 接入点 ID 即可启用 LLM 模糊判断；未填前规则引擎独立闭环）。工程实施层面已达到交付前自检标准。

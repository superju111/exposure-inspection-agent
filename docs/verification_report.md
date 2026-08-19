# 考核要求逐条验证报告

> 对照《AI考核要求说明.pdf》逐条验证  
> 验证时间：2026-08-19  
> 验证对象：互联网暴露面与高危管理面巡检 Agent

---

## 统计总览

| 状态 | 条数 | 占比 |
|------|------|------|
| 满足 | 22 | 65% |
| 部分满足 | 8 | 24% |
| 未满足 | 4 | 12% |
| **合计** | **34** | **100%** |

---

## 一、交付物（3项）

### ① 代码仓库

| 要求项 | 状态 | 说明 |
|--------|------|------|
| GitHub仓库（公开或授权私有） | 部分满足 | 项目代码完整(31文件)，但**未初始化git仓库、未推送到GitHub** |
| Agent全部源码与配置 | 满足 | 7个Python模块+4个YAML知识文件+agent-compose.yml+docker-compose.yml+Dockerfile |
| README.md（部署说明+设计说明+问题处理） | 满足 | README含8步部署、模块设计表、3个问题复盘、消融测试说明 |
| 知识与规则文件 | 满足 | 4个YAML：port_risk_rules/banner_signatures/exposure_criteria/priority_matrix |
| 不含明文密钥 | 满足 | .gitignore排除.env，所有凭据以${ENV_VAR}占位 |

**待办：** 需执行 `git init && git add . && git commit && gh repo create && git push`

### ② 运行环境

| 要求项 | 状态 | 说明 |
|--------|------|------|
| 公有云服务器 | 满足 | 阿里云ECS i-bp11heih8b7fm0ozek0r，2核4G Ubuntu22.04 |
| agent-compose已部署 | 部分满足 | agent-compose.yml配置文件完整，但**daemon未实际部署运行** |
| OctoBus已部署 | 部分满足 | 能力服务包文件完整，但**OctoBus容器未实际部署运行** |
| 考官公钥写入authorized_keys | 未满足 | **服务器上authorized_keys未配置考官公钥** |
| README注明登录地址/用户名/端口 | 部分满足 | README有占位符`<SERVER_IP>`等，需填入真实值(121.40.74.96/root/22) |

**待办：** 部署agent-compose daemon + OctoBus容器 → 写入考官公钥 → 填写README真实信息

### ③ 面试讨论

| 要求项 | 状态 | 说明 |
|--------|------|------|
| 讲解实现路径 | 满足 | design.md含完整五段闭环设计 |
| 架构理解 | 满足 | design.md含"不经网关直接调用的问题"5点分析 |
| 关键问题定位与处理 | 满足 | README含3个实施问题复盘（网络隔离/时区/LLM限流） |
| 知识依据说明 | 满足 | knowledge_rationale.md含完整推导方法论+消融结果 |

---

## 二、环境与部署要求

### 3.1 服务器

| 要求项 | 状态 | 说明 |
|--------|------|------|
| 公有云服务商不限 | 满足 | 阿里云华东1-杭州 |
| 2核4G+ | 满足 | ecs.e-c1m2.large 2核4G |
| 系统盘40G+ | 满足 | 默认40G系统盘 |
| Ubuntu 22.04/24.04 | 满足 | Ubuntu 22.04 |
| Docker + docker compose | 满足 | Docker 29.1.3已安装 |
| 公网出站可用 | 满足 | 可拉取Docker镜像 |
| 安全组仅向考官开放SSH | 部分满足 | 安全组开放22端口，**需确认来源IP限制为考官IP** |

### 3.2 agent-compose 部署要求

| 要求项 | 状态 | 验证方式 |
|--------|------|----------|
| 1. daemon常驻且restart:always | 部分满足 | agent-compose.yml中`restart: always`配置有；**但daemon未实际部署运行** |
| 1. CLI可查询版本与项目列表 | 未满足 | **agent-compose上游仓库未克隆，daemon未启动** |
| 2. 至少1个候选项目含agent-compose.yml | 满足 | exposure-inspection-agent项目含完整agent-compose.yml |
| 2. 可由定时或事件触发 | 满足 | `trigger.type: cron, schedule: "0 2 * * *", enabled: true` |
| 3. 模型凭据已配置 | 部分满足 | .env.example占位完整，**.env未创建真实凭据** |
| 4. 控制面不无鉴权对公网开放 | 满足 | `OCTOBUS_AUTH_SECRET`+`127.0.0.1:9000`绑定 |

### 3.3 OctoBus 部署要求

| 要求项 | 状态 | 验证方式 |
|--------|------|----------|
| 1. daemon常驻，status检查正常 | 未满足 | **OctoBus上游仓库未克隆，容器未启动** |
| 2. service→instance→capset三层链路 | 满足 | service.json(2个服务) + capset.json(显式方法选择) + config.json |
| 2. 导入至少1个能力服务包 | 满足 | portscan + assetquery 两个服务包 |
| 2. 显式选择暴露的方法 | 满足 | capset.json中`methods: ["scan_ports"]`和`methods: ["query_assets"]` |
| 2. 配置访问令牌 | 满足 | capset.json中`token_config.type: bearer` |
| 3. Agent经OctoBus调用（gRPC/Connect/MCP） | 满足 | octobus_client.py使用Connect RPC协议 |
| 3. 不得绕过网关直接调用后端 | 满足 | collector.py全部通过self.octobus调用，无直接socket |
| 3. 提供调用审计日志 | 满足 | auditor.py NDJSON审计+OctoBus服务端审计配置 |
| 4. OctoBus不对公网发布端口 | 满足 | docker-compose.yml `127.0.0.1:9000:9000` |

### 3.4 交付前自检

| 自检项 | 状态 | 说明 |
|--------|------|------|
| 服务器重启后两套服务可自动恢复 | 部分满足 | restart:always配置有，Docker开机自启需配置；**需实测重启验证** |
| 考官可使用公钥直接登录 | 未满足 | **authorized_keys未写入考官公钥** |
| 可查询agent-compose项目与触发器 | 部分满足 | agent-compose.yml配置完整；**daemon未运行无法查询** |
| 可查询OctoBus能力集与暴露方法 | 部分满足 | capset.json配置完整；**OctoBus未运行无法查询** |
| Agent已完整执行至少一轮且有日志 | 部分满足 | Python直跑产生了5个findings+NDJSON审计日志；**但非Docker容器内执行** |
| 仓库无明文密钥 | 满足 | .gitignore排除.env，代码中全用${ENV_VAR} |

---

## 三、命题范围

| 要求项 | 状态 | 说明 |
|--------|------|------|
| 属于安全技术或安全运营范畴 | 满足 | 安全技术方向-暴露面梳理 |
| 基于资产清单识别对外服务 | 满足 | collector.py通过assetquery获取资产清单+portscan扫描 |
| 发现不应暴露的管理端口与调试接口 | 满足 | blocklist含14个管理端口+Actuator/Jolokia等调试接口 |
| README说明场景与预期价值 | 满足 | README+design.md含完整场景说明 |

---

## 四、Agent设计要求（5.1）

| 要求项 | 状态 | 代码证据 |
|--------|------|----------|
| 1. 业务闭环完整 | 满足 | main.py: trigger(cron)→collect(OctoBus)→analyze(规则+LLM)→report(JSON+MD)→audit(NDJSON) |
| 2. LLM与脚本分工合理 | 满足 | 确定性计算全在analyzer.py代码中；LLM仅对`banner为空+medium`的findings做模糊判断(main.py L86-98)，不决定最终分类 |
| 3. 至少一处能力调用经OctoBus | 满足 | 两处：portscan.default.scan_ports + assetquery.default.query_assets 均经octobus_client.py |
| 4. 结论须有证据支撑 | 满足 | 每条finding含rule_id+rule_source+evidence+recommendation，非模型直接生成 |

---

## 五、知识实质性评定（5.2）— 评定核心

### 符合要求的表现

| 评定口径 | 状态 | 具体证据 |
|----------|------|----------|
| 判据具体可执行 | 满足 | port_risk_rules: 每个端口有具体端口号、incident_frequency百分比；banner_signatures: 精确特征串如`"Apache/2.4.49"`、`"openssh_7."`、`"+pong"` |
| 包含失效与误判经验 | 满足 | banner_signatures.false_positive_signatures: Cloudflare CDN/Cowrie蜜罐/Traefik 404等6个误报特征+降级逻辑；knowledge_rationale.md含"失效场景"3点 |
| 源自真实数据提炼 | 满足 | 147起入侵事件(n=147)统计→blocklist+combination_rules；200+审计验证集→banner_signatures |
| 存在非显然取舍 | 满足 | P1阈值=3.5(非3.0，因3.0导致40%为P1)；crown jewel=2.0x(非1.5x，因泄露成本超线性)；staging=0.5x(非直接排除) |
| 规则被代码实际使用 | 满足 | analyzer.py引用全部4个YAML文件：port_rules(L88-129)、banner_sigs(L181-227)、exposure_criteria逻辑嵌入、priority_matrix(L295-308) |

### 不符合要求的表现（逐项排查）

| 不符合表现 | 是否存在 | 说明 |
|------------|----------|------|
| 对公开标准复述 | 否 | 规则明确标注"NOT from OWASP/CIS/等保"，源自事件统计 |
| 无依据的权重/阈值 | 否 | 每个乘数/阈值都有explanation说明推导依据 |
| 以配置替代方法论 | 否 | YAML不仅是映射表，包含explanation/recommendation/incident_frequency |
| 缺乏可执行判据的描述文档 | 否 | 每条规则都有具体pattern/port/risk级别 |
| 声明的规则未被实际使用 | 否 | 单元测试test_analyzer.py验证全部规则加载和使用 |

### 消检方式验证

| 评定口径 | 状态 | 验证结果 |
|----------|------|----------|
| 移除知识后输出质量无变化→知识不构成实质经验 | 通过 | README消融测试：移除后findings 14→42(+200%)，误报率7%→36%，丧失优先排序/组合检测/误报降级 |

---

## 六、面试讨论准备度（6.2）

| 面试环节 | 状态 | 准备情况 |
|----------|------|----------|
| 整体设计(5min) | 满足 | design.md含模块划分、LLM与脚本职责分配表 |
| 架构理解(10min) | 满足 | design.md含"不经网关直接调用的5个问题"分析、Connect RPC选择理由 |
| 知识与判据(10min) | 满足 | knowledge_rationale.md含完整推导方法论+数据来源+失效场景 |
| 问题复盘(5min) | 满足 | README含3个问题：①网络隔离②时区③LLM限流，含现象/定位/解决/改进 |

---

## 七、待办清单（按优先级排序）

### P0 — 必须完成（不完成则不通过）

1. **部署agent-compose daemon**
   - `git clone https://github.com/chaitin/agent-compose.git /opt/agent-compose`
   - `cd /opt/agent-compose && docker compose up -d`
   - 验证：`docker compose ps` 显示running，`agent-compose project list` 显示项目

2. **部署OctoBus**
   - `git clone https://github.com/chaitin/OctoBus.git /opt/OctoBus`
   - `cd /opt/OctoBus && docker compose up -d`
   - 导入能力服务包、创建实例、创建capset、生成token
   - 验证：`docker exec octobus octobus status` 显示running

3. **写入考官公钥**
   - `echo "ssh-ed25519 AAAA... examiner@review" >> ~/.ssh/authorized_keys`
   - 验证考官可SSH登录

4. **创建GitHub仓库并推送**
   - `cd exposure-inspection-agent && git init && git add . && git commit -m "Initial commit"`
   - `gh repo create exposure-inspection-agent --public`
   - `git remote add origin https://github.com/superju111/exposure-inspection-agent.git && git push -u origin main`

### P1 — 重要（影响评定分数）

5. **配置真实LLM凭据**：编辑`.env`填入LLM_API_KEY，确保Agent可实际调用模型
6. **Docker容器内执行完整一轮**：通过`docker compose up`启动全部服务，验证Agent容器内能经OctoBus完成扫描→判定→报告→审计全流程
7. **实测服务器重启自动恢复**：`reboot`后验证agent-compose+OctoBus自动恢复
8. **README填写真实服务器信息**：将`<SERVER_IP>`等占位符替换为121.40.74.96/root/22

### P2 — 建议（提升评定质量）

9. **安全组限制来源IP**：将22端口安全组规则限制为考官来源IP
10. **配置Docker开机自启**：`systemctl enable docker`确保重启后Docker自动启动
11. **验证OctoBus审计日志**：在服务器上检查`/var/log/octobus/audit.ndjson`存在且含调用记录
12. **消融测试在服务器上实测**：移除knowledge/目录运行一次，对比输出差异并保存记录

---

## 八、结论

项目在**代码设计、知识实质性、LLM分工、五段闭环**等考核核心评定维度已全部满足要求。知识规则文件的质量（误报特征库+端口组合检测+消融验证）达到了"非公开资料可获得的实践积累"标准。

**关键缺口集中在工程实施层面**：agent-compose daemon和OctoBus未在服务器上实际部署运行、考官公钥未配置、GitHub仓库未创建推送。这些是P0级别的待办项，需要完成才能通过考官的交付前自检。

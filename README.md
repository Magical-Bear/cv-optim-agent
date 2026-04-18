# CV Optimizer Agent

基于 LangGraph 多智能体的简历优化平台。用户上传简历与目标 JD，系统自动分析匹配度、生成优化建议，用户确认后输出优化版简历并支持导出。

---

## 功能概览

- **简历输入**：支持文本粘贴、PDF 上传、Word 上传（自动解析为纯文本）
- **智能分析**：并行提取简历与 JD 关键词，生成匹配报告（得分、亮点、缺口）
- **人机协作**：用户可逐条勾选建议、直接编辑改写文案、补充额外说明
- **简历生成**：基于用户选择重写简历，输出结构化 Markdown
- **多格式导出**：下载 `.md` 文件或渲染后的 `.pdf` 文件（支持中文字体）

---

## 技术架构

### 后端

| 层级 | 技术选型 |
|------|----------|
| Web 框架 | FastAPI + lifespan 依赖注入，全异步 |
| Agent 编排 | LangGraph (StateGraph + MemorySaver) |
| LLM 调用 | LangChain V1.0 + langchain-openai（对接 DeepSeek） |
| 文档解析 | pdfplumber（PDF）、python-docx（Word） |
| PDF 导出 | WeasyPrint + fonts-noto-cjk |
| 配置管理 | pydantic-settings，环境变量读取 |
| 会话管理 | 内存 dict + asyncio 定时 TTL 清理，无数据库 |
| 包管理 | uv |

### 前端

| 层级 | 技术选型 |
|------|----------|
| 框架 | Vue 3 (Composition API) + Vite |
| UI 组件库 | Element Plus |
| 状态管理 | Pinia |
| Markdown 预览 | marked.js |
| HTTP 请求 | axios |

### 部署

- 单容器多阶段 Dockerfile（Node 20 构建前端 → Python 3.11 运行时）
- FastAPI StaticFiles 挂载前端 `dist`，单端口 `8000` 对外
- GitHub Actions CI 验证 `docker build` 成功

---

## LangGraph 智能体设计

```
START
  ├──[Send]──▶ resume_extractor (LLM)  ──┐
  └──[Send]──▶ jd_extractor    (LLM)  ──┤
                                          ▼
                                      matcher (LLM)
                                          │
                                      suggester (LLM)
                                          │
                                    interrupt() ◀── 等待用户确认
                                          │
                                      rewriter (LLM)
                                          │
                                         END
```

### 节点说明

| 节点 | 职责 | LLM | Tool |
|------|------|-----|------|
| `resume_extractor` | 从简历提取技能、关键词、角色标签 | ✓ | `extract_keywords` |
| `jd_extractor` | 从 JD 提取必备/加分技能 | ✓ | `extract_keywords` |
| `matcher` | 对比双方关键词，输出得分、亮点、缺口 | ✓ | `score_skill_match` |
| `suggester` | 生成 5-8 条带优先级的具体改写建议 | ✓ | — |
| `rewriter` | 按用户选择的建议重写简历，输出 Markdown | ✓ | — |

### Human-in-the-Loop

`suggester` 节点完成后，图调用 `interrupt(suggestions)` 暂停。FastAPI 将 `config`（含 `thread_id`）存入 session。

`POST /api/confirm` 被调用时，后端用 `graph.invoke(Command(resume=feedback), config)` 恢复执行，图从中断点继续进入 `rewriter`。

### 并行 Fan-out

`resume_extractor` 与 `jd_extractor` 通过 `Send()` 并行启动，两者结果通过 State 上的 reducer 合并后传入 `matcher`，缩短整体分析耗时。

---

## API 路由

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/upload` | 上传 PDF/Word，返回解析后的纯文本 |
| `POST` | `/api/analyze` | 提交简历+JD，启动 Agent，返回 `session_id`、匹配报告、建议列表 |
| `POST` | `/api/confirm` | 提交用户选择的建议及补充说明，恢复 Agent，返回优化后简历 |
| `GET` | `/api/export/{session_id}` | 导出简历，`?format=md` 或 `?format=pdf` |

---

## 前端页面流程

```
StepUpload  →  StepReview  →  StepResult
   │               │               │
粘贴/上传      勾选/编辑建议    Markdown预览
简历 + JD      补充额外说明    下载 MD / PDF
   │               │
/api/analyze  /api/confirm
```

- **StepUpload**：支持文件上传（调 `/api/upload` 解析）或直接粘贴文本；JD 单独文本框输入
- **StepReview**：展示匹配得分进度条、亮点列表、缺口列表；每条建议卡片可勾选、可编辑改写文案；底部额外补充输入框
- **StepResult**：渲染优化后简历 Markdown；两个下载按钮分别触发 MD/PDF 导出

---

## 环境变量

复制 `.env.example` 并填写：

```bash
cp backend/.env.example backend/.env
```

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `DEEPSEEK_API_KEY` | ✓ | — | DeepSeek API Key |
| `DEEPSEEK_BASE_URL` | | `https://api.deepseek.com` | API 基础地址 |
| `DEEPSEEK_MODEL` | | `deepseek-chat` | 模型名称 |
| `SESSION_TTL_MINUTES` | | `30` | 会话过期时间（分钟） |
| `MAX_UPLOAD_SIZE_MB` | | `10` | 最大上传文件大小 |

---

## 快速启动

### 方式一：Docker（推荐）

```bash
git clone <repo-url>
cd cv-optim-agent

# 配置环境变量
cp backend/.env.example backend/.env
# 编辑 backend/.env，填写 DEEPSEEK_API_KEY

# 构建镜像
docker build -t cv-optim .

# 启动服务
docker run -p 8000:8000 --env-file backend/.env cv-optim
```

访问 [http://localhost:8000](http://localhost:8000)

### 方式二：docker-compose

```bash
cp backend/.env.example backend/.env
# 填写 DEEPSEEK_API_KEY

docker compose up --build
```

### 方式三：本地开发

**后端：**
```bash
cd backend
uv sync
cp .env.example .env
# 填写 DEEPSEEK_API_KEY
uv run uvicorn app.main:app --reload --port 8000
```

**前端：**
```bash
cd frontend
npm install
npm run dev
# 访问 http://localhost:5173（代理到后端 8000）
```

---

## 验收流程

面试官可按以下步骤完整体验功能：

```
1. docker build → docker run（见上方快速启动）
2. 打开 http://localhost:8000
3. 粘贴简历文本（或上传 PDF/Word）
4. 粘贴目标职位 JD
5. 点击「开始分析」
6. 查看匹配报告：得分、亮点、技能缺口
7. 勾选/编辑优化建议，填写补充说明
8. 点击「确认生成」
9. 预览优化后简历，下载 MD 或 PDF
```

---

## 项目结构

```
cv-optim-agent/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI 入口，lifespan，StaticFiles
│   │   ├── config.py         # pydantic-settings 配置
│   │   ├── session.py        # 内存会话 + TTL 清理
│   │   ├── routers/
│   │   │   └── api.py        # 4 条 API 路由
│   │   ├── agents/
│   │   │   ├── graph.py      # LangGraph StateGraph + MemorySaver
│   │   │   ├── nodes.py      # 5 个节点函数 + Prompt
│   │   │   ├── state.py      # AgentState TypedDict + Pydantic 模型
│   │   │   └── tools.py      # LangChain @tool 工具函数
│   │   └── utils/
│   │       ├── parser.py     # PDF/Word/文本解析
│   │       └── exporter.py   # MD/PDF 导出
│   ├── pyproject.toml
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── main.js
│   │   ├── App.vue
│   │   ├── api/index.js      # axios 封装
│   │   └── views/
│   │       ├── StepUpload.vue
│   │       ├── StepReview.vue
│   │       └── StepResult.vue
│   ├── package.json
│   └── vite.config.js
├── Dockerfile                # 多阶段构建
├── docker-compose.yml
├── .github/workflows/ci.yml  # Docker build CI
└── README.md
```

---

## 设计意图

**为什么用 LangGraph？**
将分析流程建模为有状态图，天然支持人机协作（HITL）中断点。相比线性 Prompt 链，图结构使每个节点职责单一、可独立调试，也更符合「多智能体协作」的评估要求。

**为什么双轨并行提取？**
简历提取和 JD 提取完全独立，并行运行缩短约 40-50% 的等待时间，同时在架构上体现了 Fan-out/Fan-in 的多 Agent 协作模式。

**为什么用内存 Session 而不是数据库？**
本任务是单次会话场景（分析→确认→导出），不需要历史查询。内存 dict + asyncio 定时清理零依赖、零配置，Docker 单容器部署更简洁，TTL 30 分钟覆盖正常使用场景。

**为什么单容器？**
面试官验收成本最低：一条 `docker run` 命令，一个端口，不需要 compose 也能跑。前端 `dist` 由 FastAPI StaticFiles 直接服务，无需 Nginx。

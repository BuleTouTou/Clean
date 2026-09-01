# 房源数据清洗工具

## 1. 项目简介

房源数据清洗工具是一个完全在本机运行的轻量级 Web 应用，用于将业务人员导出的房源数据整理成符合北京房源系统要求的出售或出租 Excel 文件。

工具以楼盘字典、栋座/单元字典和导入模板为准，提供“自动匹配 + 人工确认 + 可追溯导出”的处理流程。原始数据不会上传到外部服务。

## 2. 目标与边界

### 2.1 目标

- 降低房源数据导入前的人工整理成本。
- 统一小区、行政区、商圈、期名、栋幢和单元的写法。
- 保留自动修改依据，便于复核和追责。
- 将确认过的映射和匹配规则保存下来，供后续批次参考。

### 2.2 边界

- 工具只处理本地文件，不负责连接远程房源系统或执行最终导入。
- 低置信度的小区、栋座、单元匹配必须人工确认，不会自动猜测。
- 缺少基础字典或导入模板时，不能创建清洗任务。
- `.xls` 文件依赖本机 LibreOffice 转换；推荐使用 `.xlsx`。

## 3. 主要功能

1. **批次类型**：支持出售房源和出租房源两种模板。
2. **文件识别**：支持 CSV、XLS、XLSX，自动识别工作表、表头行和数据范围。
3. **字段映射**：根据完全匹配、同义词、历史规则和名称相似度提供映射建议，用户最终确认。
4. **楼盘校准**：结合楼盘名、别名、期名和“几号院”等信息匹配楼盘字典。
5. **栋座/单元校准**：在已确认楼盘范围内匹配标准栋座和单元；冲突项进入人工审核。
6. **数据清洗**：拆分户型字段中的房、厅、厨、卫、阳台；规范日期和文本字段；缺失等级时按稳定规则补齐。
7. **审计与异常**：将字段级修改依据和阻断异常详情保存到清洗报告中，供历史记录查看。
8. **规则快照**：每次导出都会保存本批次实际使用的字段映射、小区匹配和栋座匹配规则，历史报告页面可以直接查看。
9. **两种导出模式**：导出全部记录，或仅导出没有阻断异常的记录。
10. **账号与权限**：管理员分配普通用户账号和初始密码；普通用户首次登录必须修改密码，只能查看自己的任务和历史清洗报告，管理员可以查看全部用户和全部报告，并按用户账号或姓名筛选报告。
11. **小区与栋座联合复核**：使用栋座字典中的期名关系辅助确认标准小区；同一原始小区合并展示，只有候选期名能安全覆盖全部栋座时才允许一键匹配，冲突栋座保留逐项确认。

## 4. 技术选型与迁移说明

- **后端采用 FastAPI**：提供类型化请求校验、自动 OpenAPI 文档和 ASGI 并发模型。生产启动入口为 `backend.app:app`，由 Uvicorn 承载。
- **持久化采用 PostgreSQL + MinIO**：PostgreSQL 保存历史报告与已确认规则，MinIO 保存原始上传文件和最终 Excel。SQLite 仅保留为直接运行和单元测试的兼容回退，不作为容器部署数据库。
- **前端采用 TypeScript + Vite**：页面入口和 API 类型定义位于 `frontend/src/`，Vite 将 TypeScript、CSS 和 HTML 构建到 `frontend/dist/`，后端只负责托管构建产物。
- **样式采用 Tailwind CSS 4**：通过官方 `@tailwindcss/vite` 插件集成，入口文件使用 Tailwind 4 的 `@import "tailwindcss"`，不再使用 Tailwind 3 的 PostCSS 配置或 `@tailwind base/components/utilities` 指令。
- **前端采用文件路由**：使用 `unplugin-vue-router` 根据 `frontend/src/pages/` 自动生成 Vue Router 路由。页面按文件组织，`App.vue` 只负责全局布局和路由出口。
- **接口代码使用 Worma 生成**：Worma（`wormajs`）是 Alova 生态当前的 OpenAPI 生成工具。它读取 FastAPI 的 OpenAPI 文档，并生成 Alova 调用函数和 TypeScript 类型；不要再手写一份与后端接口重复的类型定义。
- **请求状态使用 TanStack Query Vue**：`useQuery` 管理服务状态和历史报告查询，`useMutation` 管理创建任务、上传、审核和导出等有副作用操作；导出成功后通过 query invalidation 刷新历史报告列表。
- **代码边界**：清洗算法集中在 `backend/core.py`，新功能应优先放入 `backend/` 包；前端源码位于 `frontend/`，`frontend/dist/` 仅是构建时生成的临时产物，不提交到 Git，也不要直接编辑。

## 5. 后端包结构

当前测试全部针对后端 API 和清洗核心，因此归入 `backend/tests/`。如果未来增加前端组件测试或跨前后端端到端测试，再单独建立顶层 `tests/` 或 `e2e/` 目录。

```text
backend/
├── __init__.py       # 包入口
├── app.py            # FastAPI 应用、请求模型、API 路由和静态文件挂载
├── auth.py           # bcrypt 密码、登录会话和用户管理
├── core.py           # 文件处理、匹配、清洗和导出核心逻辑
├── db.py             # PostgreSQL/SQLAlchemy 数据访问
├── migrations/       # Alembic 数据库迁移
├── export_openapi.py # 导出 OpenAPI 规范供 Worma 使用
└── tests/             # 后端测试
```

`core.py` 当前仍是一个过渡中的核心模块，后续建议按以下边界继续拆分：

```text
backend/
├── api/              # 路由和 Pydantic 请求/响应模型
├── services/         # 文件读取、楼盘匹配、清洗和导出服务
├── repositories/     # 字典、规则和任务状态的读写
├── config.py         # 路径和环境变量配置
└── app.py            # 应用组装和启动生命周期
```

## 6. 处理流程

```text
选择出售/出租
      ↓
上传 CSV/XLS/XLSX
      ↓
选择工作表并确认表头
      ↓
确认字段映射
      ↓
审核无法唯一匹配的楼盘
      ↓
审核无法唯一匹配的栋座/单元
      ↓
设置统一委托日期
      ↓
导出 Excel，并将报告、规则、异常和审计信息保存到数据库
```

楼盘审核会按“原始小区”合并显示，并在组内列出本批次涉及的原始栋座。系统使用 `楼盘 + 期名 + 座栋` 联合判断：栋座唯一对应某一期名时自动确认；同一栋座对应多个期名时必须人工确认。候选覆盖全部栋座且不存在冲突时可以“一键匹配全部”，只能覆盖部分栋座时仅应用到兼容项，剩余项继续保留为待确认。规则最终按“原始小区 + 原始栋座”保存，因此同一小区的不同栋座可以导出不同期名。

## 7. 运行环境

### 7.1 OrbStack / Docker 本地部署（推荐）

项目只构建一个业务镜像；PostgreSQL 和 MinIO 使用官方镜像，由 `compose.yaml` 编排为三个独立容器：

```text
app (Vue + FastAPI) → postgres
                  └→ minio
```

首次启动：

```bash
cp .env.example .env
# 修改 .env 中的 PostgreSQL、MinIO 和管理员初始密码
docker compose up --build -d --wait
```

访问地址：应用 `http://localhost:8765`，MinIO 控制台 `http://localhost:9001`，PostgreSQL `localhost:5432`。

首次启动会根据 `.env` 中的 `ADMIN_USERNAME`、`ADMIN_INITIAL_PASSWORD` 和 `ADMIN_NAME` 创建管理员。管理员登录后可在“用户管理”中分配普通用户账号、姓名和初始密码；普通用户首次登录后会被强制进入修改密码页面。管理员已存在时，修改环境变量不会自动重置其密码。

```bash
docker compose ps
docker compose logs -f app
docker compose down  # 停止服务但保留数据
```

不要随意执行 `docker compose down -v`，该命令会一并删除 PostgreSQL 和 MinIO 的本地数据卷。

### 7.2 直接运行开发环境

- macOS、Linux 或 Windows 10/11
- [uv](https://docs.astral.sh/uv/)（负责 Python 版本、虚拟环境和依赖管理）
- Python 3.12（由 `backend/.python-version` 固定；项目兼容 Python 3.10–3.13）
- Python 依赖：见 `backend/pyproject.toml`
- Bun 1.4+（Vite 前端的安装、开发和构建运行时）
- 读取旧版 `.xls`：需要安装 LibreOffice，并确保 `soffice` 在 PATH 中

安装 uv：

macOS/Linux：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Windows PowerShell：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

安装依赖并准备 Python：

```bash
uv sync --project backend
```

`uv sync --project backend` 会读取 `backend/.python-version` 和 `backend/pyproject.toml`，自动安装 Python 3.12（本机没有时会下载 uv 管理的版本）、在 `backend/.venv/` 创建虚拟环境并安装后端依赖。日常运行不需要手动激活虚拟环境。

首次使用还需要准备前端构建产物：

```bash
cd frontend
bun install
bun run build
cd ..
```

## 8. 基础文件规范

以下文件必须放在项目根目录的 `resources/` 文件夹中。文件名需要完全一致；如文件包含真实业务数据，请按仓库的数据安全策略决定是否提交 Git：

| 文件 | 用途 | 最低要求 |
| --- | --- | --- |
| `北京楼盘字典.xlsx` | 小区、别名、行政区、商圈和期名字典 | 首行包含 `楼盘`、`别名`、`行政区`、`商圈`、`期名` |
| `北京-单元楼盘字典.xlsx` | 楼盘下的标准栋座和单元字典 | 首行包含 `楼盘`、`座栋`、`单元` |
| `售房数据导入模版.xlsx` | 出售房源输出模板 | 包含名为 `房源` 的工作表 |
| `租房数据导入模版 .xlsx` | 出租房源输出模板 | 包含名为 `房源` 的工作表 |

模板第一行必须是完整表头，不能存在空列。程序会在模板最后追加 `未匹配原因` 列。

## 9. 部署启动

本项目面向上线部署，不再提供 `start.bat`、`start.sh` 或 `start.command` 等命令行启动脚本。服务启动、停止、重启和健康检查统一交给部署平台或进程管理器（例如 Docker、systemd、Supervisor、Kubernetes 或云平台托管服务）。

- 后端 ASGI 应用入口：`backend.app:app`，由部署平台配置 Uvicorn/Gunicorn 等 ASGI Server 承载。
- 前端构建产物：部署前由 `bun run build` 生成 `frontend/dist/`，再由后端静态文件服务、Nginx 或对象存储/CDN 托管；该目录不提交到 Git。
- 前端开发依赖和构建运行时：Bun；生产部署需要在构建阶段生成并发布 `frontend/dist/`。
- 端口、进程数、日志、反向代理和 HTTPS 证书均属于部署配置，不写入仓库启动脚本。

如果部署平台需要填写进程启动命令，请从项目根目录使用 Python 模块方式启动：

```bash
uv run --project backend python -m uvicorn backend.app:app --host 0.0.0.0 --port 8765
```

使用 `python -m uvicorn` 可以确保调用的是 `backend` 项目虚拟环境中的 Uvicorn；不要在根目录直接执行 `uv run uvicorn`，因为根目录不再包含 Python 项目配置。

## 10. 配置项

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DATABASE_URL` | 本地 SQLite 兼容地址 | 容器环境必须设置为 PostgreSQL，例如 `postgresql+psycopg://user:password@postgres:5432/housing_cleaner` |
| `WORK_DIR` | `data/` | 上传和导出过程中的临时工作目录；容器中使用 `/tmp/housing-cleaner` |
| `UV_PYTHON` | `backend/.python-version` | 临时覆盖 uv 使用的 Python 解释器 |
| `MINIO_ENABLED` | `false` | 是否启用 MinIO 文件存储 |
| `MINIO_ENDPOINT` | 无 | MinIO 服务地址，例如 `http://localhost:9000` |
| `MINIO_ACCESS_KEY` / `MINIO_USERNAME` | 无 | MinIO Access Key；兼容旧变量名 `MINIO_USERNAME` |
| `MINIO_SECRET_KEY` / `MINIO_PASSWORD` | 无 | MinIO Secret Key；兼容旧变量名 `MINIO_PASSWORD` |
| `MINIO_BUCKET` | 无 | 存放清洗文件的 Bucket，必须由部署环境提供 |
| `MINIO_PUBLIC_ENDPOINT` | 同 `MINIO_ENDPOINT` | 数据库中 OSS URL 使用的可访问地址 |
| `ADMIN_USERNAME` | `admin` | 首次启动时创建的管理员账号 |
| `ADMIN_INITIAL_PASSWORD` | 无 | 首次启动管理员密码，至少 8 位；必须通过 `.env` 或部署平台 Secret 提供 |
| `ADMIN_NAME` | `系统管理员` | 管理员姓名 |
| `SESSION_DAYS` | `7` | 登录会话有效天数，范围 1–30 天 |
| `SESSION_COOKIE_SECURE` | `false` | HTTPS 生产环境必须设为 `true`，使登录 Cookie 仅通过 HTTPS 传输 |

开发环境可以复制根目录的 `.env.example` 为 `.env`，再填写 PostgreSQL、MinIO 和管理员凭据。`.env` 已加入 Git 忽略规则，正式环境应通过部署平台的 Secret 注入配置，并启用 HTTPS 与 `SESSION_COOKIE_SECURE=true`。用户密码使用 bcrypt 哈希保存，登录令牌只以 SHA-256 摘要入库并通过 HttpOnly Cookie 传输，接口不会返回密码或密码哈希。当前项目约定使用 Bucket `clean`；清洗报告、异常详情、审计记录和规则快照保存为 PostgreSQL `JSONB`。浏览器下载统一经过 FastAPI 转发，不暴露容器内部的 `http://minio:9000` 地址。

数据库中的任务开始时间、完成时间和审计操作时间统一保存为带 `Z` 后缀的 UTC ISO 8601 字符串（例如 `2026-08-30T16:18:30Z`）。前端展示时通过浏览器 `Intl.DateTimeFormat` 转换为北京时间（`Asia/Shanghai`），不依赖访问者电脑的本地时区。

## 11. 目录约定

```text
.
├── backend/                  # FastAPI 后端包
│   ├── app.py                # ASGI 应用和 API 路由
│   ├── auth.py               # 用户、密码与会话认证
│   ├── core.py               # 文件处理、匹配、清洗和导出核心逻辑
│   ├── db.py                 # SQLAlchemy 数据访问和模型
│   ├── migrations/           # Alembic PostgreSQL 迁移
│   ├── export_openapi.py     # 导出 OpenAPI 规范供 Worma 使用
│   ├── pyproject.toml        # uv 项目配置和依赖声明
│   ├── uv.lock               # 后端依赖锁定文件
│   ├── .python-version       # 默认 Python 版本（3.12）
│   ├── requirements.txt      # 兼容传统 pip 的依赖清单
│   ├── tests/                # 后端自动化测试
│   │   ├── test_smoke.py
│   │   └── test_real_data.py
│   └── __init__.py
├── frontend/                 # TypeScript 前端源码和类型检查配置
│   ├── index.html             # Vite 页面入口
│   ├── package.json          # 前端开发依赖和脚本
│   ├── tsconfig.json         # TypeScript 编译约束
│   ├── worma.config.ts       # OpenAPI → Alova 代码生成配置
│   ├── src/layouts/           # 全局布局
│   ├── src/pages/             # 文件路由页面（文件名即路由）
│   │   ├── index.vue          # /
│   │   └── reports/index.vue  # /reports
│   ├── src/api.ts            # 现有业务兼容层（生成代码稳定后逐步替换）
│   ├── src/generated/       # Worma 生成的 Alova 调用代码（不要手工编辑）
│   ├── src/main.ts           # TypeScript 入口
│   ├── src/assets/            # 全局资源和 Tailwind CSS 入口
│   │   └── tailwind.css
├── resources/                # 楼盘字典和导入模板（业务资源目录）
│   ├── 北京楼盘字典.xlsx
│   ├── 北京-单元楼盘字典.xlsx
│   ├── 售房数据导入模版.xlsx
│   └── 租房数据导入模版 .xlsx
├── Dockerfile                # Vue + FastAPI 业务镜像
├── compose.yaml              # app、PostgreSQL、MinIO 本地编排
├── data/                     # 旧 SQLite、规则和直接运行兼容数据（Git 忽略）
└── outputs/                  # 旧版本本地导出兼容目录（Git 忽略）
```

首次执行 `uv sync --project backend` 后会使用 `backend/uv.lock`。依赖版本稳定后，建议将该锁文件一并提交，以保证不同机器使用相同版本的后端依赖。

## 12. 输出文件规范

MinIO 启用时，每次任务的文件会上传到 `clean/housing-cleaner/users/<用户账号>/<任务 ID>/`，不同用户拥有独立的对象目录；MinIO 未启用时才会在 `WORK_DIR/outputs/<任务 ID>/` 下生成回退文件：

- `售房清洗导入_时间戳.xlsx` 或 `租房清洗导入_时间戳.xlsx`：最终导入文件。
- `清洗报告.json`：MinIO 未启用的兼容模式下生成；容器模式下报告内容直接保存到 PostgreSQL `JSONB`，其中包含异常详情、字段级审计记录和清洗规则快照。

导出的 Excel 会保留模板样式，从第 2 行开始写入数据；编号、电话、工号、代码等文本字段按文本格式写出，避免前导零丢失。

## 13. 本地接口（开发参考）

前端通过 `backend.app:app` 提供的 FastAPI 本地接口工作：

| 接口 | 方法 | 作用 |
| --- | --- | --- |
| `/api/status` | GET | 检查基础文件和当前任务数量 |
| `/api/task` | POST | 创建出售/出租清洗批次 |
| `/api/upload` | POST | 上传并识别源文件 |
| `/api/select-sheet` | POST | 读取指定工作表和表头 |
| `/api/mapping` | POST | 提交字段映射并执行楼盘匹配 |
| `/api/review` | POST | 保存楼盘人工确认结果 |
| `/api/building-review` | POST | 生成栋座审核项 |
| `/api/building-confirm` | POST | 保存栋座确认和委托日期 |
| `/api/export` | POST | 生成导出文件 |
| `/api/reports` | GET | 分页查询历史清洗报告 |
| `/api/reports/{report_id}` | GET | 查询单条历史清洗报告 |

历史报告页面默认每页显示 10 条，可切换为 20、30 或 50 条；接口的 `pageSize` 默认值也是 10。

FastAPI 同时自动提供 OpenAPI 文档：

- `/openapi.json`：机器可读的 OpenAPI 规范。
- `/docs`：Swagger UI 交互式文档。

### 13.1 使用 Worma 生成前端 API

前端使用 [Worma](https://worma.js.org)（当前包名 `wormajs`，官方命令为 `worma gen`）从后端 OpenAPI 文档生成 Alova 调用代码。生成配置位于 `frontend/worma.config.ts`，输出目录为 `frontend/src/generated/`。

```bash
cd frontend
bun install
bun run api:gen
```

`api:gen` 会先执行 `backend.export_openapi` 刷新临时 OpenAPI 文件，再运行 `worma gen -p .`。生成结果可以直接被 Vue 业务代码 import；生成目录中的文件不要手工修改，业务封装放在 `frontend/src/services/`。

如果后端已经启动，也可以直接访问 `http://127.0.0.1:8765/openapi.json` 检查接口规范。Worma 生成器本身支持 Bun、Node.js、Deno 运行时；本项目统一使用 Bun 执行前端脚本。

这些接口只绑定到 `127.0.0.1`，不应直接暴露到公网。

## 14. 测试与验收

基础语法检查：

```bash
uv run --project backend python -m py_compile backend/core.py backend/app.py backend/tests/test_smoke.py backend/tests/test_real_data.py
```

前端依赖安装和 TypeScript 检查：

```bash
cd frontend
bun install
bun run check
```

前端生产构建（会清空并重新生成 `frontend/dist/`）：

```bash
cd frontend
bun run build
```

本地前端开发服务器（API 自动代理到 `127.0.0.1:8765`）：

```bash
cd frontend
bun run dev
```

冒烟测试：

```bash
uv run --project backend pytest backend/tests/test_smoke.py
```

真实文件测试：

```bash
uv run --project backend python backend/tests/test_real_data.py /path/to/source.xlsx
```

运行完整测试前，必须先准备第 8 节列出的四个基础 Excel 文件。

## 15. 数据安全与提交规范

- 不要将真实房源数据、楼盘字典、导入模板、`data/` 或 `outputs/` 提交到 Git。
- 共享测试数据时，应先脱敏业主姓名、联系方式、房源编号等字段。
- 修改清洗规则时，应同步检查历史报告中的审计记录和异常详情，避免静默改变历史结果。
- 变更模板表头后，应新建清洗批次，不要复用旧任务。
- 容器模式下，可复用规则保存到 PostgreSQL `app_settings`；每次导出使用的规则快照仍会写入对应历史报告。旧 `data/rules.json` 仅供非容器兼容模式读取。

## 16. 常见问题

后续上线和小牛看房系统对接方案见：[后续优化点](./docs/后续优化点.md)。

### 提示“缺少基础文件”

确认四个字典/模板文件已放在项目根目录，且文件名、空格和扩展名完全一致。

### 服务没有启动

请检查部署平台或进程管理器中的 ASGI 服务配置、日志和健康检查；仓库不再提供本地命令行启动脚本。

### `.xls` 无法读取

安装 LibreOffice 并确认终端可以执行 `soffice --version`，或先将文件另存为 `.xlsx`。

### 导出结果包含“未匹配原因”

这是预期行为。请在界面中完成楼盘、栋座或单元审核，或使用“仅导出无阻断异常数据”过滤异常记录。

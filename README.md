# 个人记账 API

使用 Python 和 FastAPI 开发的个人记账后端，支持用户认证、
账单管理和月度收支统计。

## 已实现功能

- 用户注册、登录及数据库会话认证；浏览器通过 HttpOnly Cookie 保持登录，支持服务端退出撤销。
- 创建、查询、修改、删除账单。
- 按分类、月份筛选账单，支持分页查询。
- 按月份统计收入、支出和结余。
- 用户只能访问自己的账单。
- 使用 Alembic 管理数据库结构变更。
- 请求日志：记录请求编号、方法、路径、状态码及处理耗时。

金额以整数“分”保存，例如 2500 表示 25.00 元。

保持登录的配置、代码阅读顺序和验收步骤见 [保持登录完整学习与验收](doc/保持登录完整学习与验收.md)。本地 HTTP 需要显式设置 `SESSION_COOKIE_SECURE=false`；公网 HTTPS 使用 `true`。

## 技术栈

- Python 3.10（当前已验证版本为 3.10.22）
- FastAPI、Pydantic
- SQLAlchemy、SQLite
- Alembic
- PyJWT、pwdlib / Argon2
- pytest

## 本地启动

以下命令适用于 Windows PowerShell，请在项目根目录执行。

### 1. 创建环境并安装依赖

确认当前 Python 版本：

```powershell
python --version
```

创建虚拟环境：

```powershell
python -m venv .venv
```

安装运行和测试依赖：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

检查依赖：

```powershell
.\.venv\Scripts\python.exe -m pip check
```

### 2. 配置环境变量

首次配置时，将 `.env.example` 复制为 `.env`。
如果已经存在 `.env`，请保留原配置。

生成 JWT 密钥：

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
```

将生成的值填入 `.env`：

```dotenv
JWT_SECRET=替换为上一步生成的密钥
ACCESS_TOKEN_EXPIRE_MINUTES=30
DATABASE_PATH=expenses.db
```

配置说明：

| 配置项 | 含义 |
|---|---|
| JWT_SECRET | 历史 JWT 工具配置，暂仍要求至少 32 字符；当前登录使用数据库会话 |
| ACCESS_TOKEN_EXPIRE_MINUTES | Token 有效期，单位为分钟，默认 30 |
| DATABASE_PATH | SQLite 数据库路径，默认 expenses.db |

相对数据库路径以项目根目录为基准。

系统环境变量优先于 `.env` 中的同名配置。
当前登录凭证统一通过数据库会话验证，旧 JWT 已不被接受。JWT 配置暂为历史安全工具保留；更换该密钥不会撤销数据库会话，撤销需走会话逻辑。

不要将 `.env` 或真实密钥提交到 Git。

### 3. 初始化或升级数据库

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

对于全新的数据库，该命令会按顺序执行迁移并创建表。

查看当前迁移版本：

```powershell
.\.venv\Scripts\python.exe -m alembic current
```

首次安装使用 Alembic 建表，无须再执行 `init_db.py`。

已有数据库升级前应先备份。
早期练习数据库的迁移和账单归属处理见 `doc/第四阶段技术文档.md`。

### 4. 启动开发服务

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

浏览器访问：

- 首页：http://127.0.0.1:8000/
- 接口文档：http://127.0.0.1:8000/docs

`--reload` 用于本地开发，修改代码后自动重启服务。

## 第一次调用接口

在 `/docs` 中依次完成：

1. 调用 `POST /auth/register` 注册用户。
2. 调用 `POST /auth/login`，获取 `access_token`。
3. 点击页面上的 `Authorize`，填入 access_token 的值。
4. 调用 `GET /auth/me`，确认当前用户。
5. 调用 `POST /transactions` 创建账单。
6. 查询账单列表和月份统计。

创建账单的请求体示例：

```json
{
  "kind": "expense",
  "amount_cents": 2500,
  "category": "餐饮",
  "occurred_on": "2026-10-10",
  "note": "午饭"
}
```

登录接口返回 Token 后，仍需在 Authorize 中设置它。
切换账号时，应替换 Authorize 中原来的 Token。

Swagger 的退出授权操作只是停止发送 Token，
不会让已经签发的 Token 在服务端立即失效。

## 运行测试

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

当前共有 58 个测试用例，覆盖认证、用户隔离、登录限流、
账单读写与非法输入、分页、月份边界、跨年、闰年、空月份统计，以及密码长度边界和密码校验错误不回显输入。

测试使用临时数据库及测试密钥，不使用日常记账数据库。

## 项目结构

```text
expense-tracker/
├── main.py                  # 应用入口
├── config.py                # 配置读取与校验
├── db.py                    # 数据库连接与会话依赖
├── models.py                # 数据库模型
├── schemas.py               # 请求与响应模型
├── security.py              # 密码哈希、Token 签发与验证
├── dependencies.py          # 当前用户认证依赖
├── request_logging.py       # 请求日志中间件
├── routers/
│   ├── auth.py              # 注册、登录、当前用户
│   ├── transactions.py      # 账单接口
│   └── statistics.py        # 统计接口
├── alembic/                 # 数据库迁移
├── tests/                   # 自动化测试
├── doc/                     # 阶段技术文档
├── .env.example             # 配置模板
├── requirements.txt         # 运行依赖
└── requirements-dev.txt     # 开发与测试依赖
```

## 日志与常见问题

应用日志输出到标准输出/错误流。直接运行时在终端查看；
Docker 部署时由 local 日志驱动收集和轮转，可通过 `docker compose logs` 查看。

应用请求日志包含 request_id。
正常返回的响应中，可通过 `X-Request-ID` 响应头关联日志。

- **401**：检查是否授权、Token 是否过期、签名密钥是否变化。
- **404**：检查接口地址；账单可能不存在，或不属于当前用户。
- **422**：查看响应中的 detail，确认字段类型、日期及金额是否合法。
- **no such table**：检查是否执行迁移，以及数据库路径是否正确。
- **修改 .env 后没有生效**：手动重启服务，并检查是否有同名系统环境变量覆盖。
- **端口已被占用**：确认旧服务是否退出，或使用其他端口启动。

## 登录限流

登录接口使用按来源 IP 计数的固定窗口限流：

- 从该来源首次请求开始计算，每 60 秒最多允许 5 次登录尝试。
- 成功和失败的登录均计数；未通过请求体校验的请求不计数。
- 超限返回 429，响应头 Retry-After 表示需要等待的秒数。
- 窗口到期后恢复额度。
- 限流检查位于查询用户和验证密码之前。

当前参数在 routers/auth.py 创建 LoginRateLimiter 时设置，
尚未通过环境变量配置。

计数保存在应用进程内存中，重启后清空，多进程或多容器之间
不共享额度。共用公网 IP 的用户共享额度。

当前版本适用于单进程、小规模使用。反向代理部署时，
还需要配置可信代理范围并验证来源 IP。

## 认证与错误响应

- 注册密码长度为 7～128 个字符，登录输入允许 1～128 个字符。
- 重复注册返回 409：“用户名已存在”，不会覆盖原账号。
- 登录用户名不存在时返回 401：“用户名不存在，请先注册”。
- 密码错误时返回 401：“密码错误”。
- 登录超限返回 429，并通过 Retry-After 告知等待秒数。
- 请求校验错误返回 422，仅保留 loc、msg、type，不返回原始 input。

登录提示明确区分用户名不存在与密码错误，这是当前产品选择。


## 当前范围

目前完成了本地容器部署，登录限流基础版及 58 个自动化测试已通过本地验收。
登录限流通过 PR #3 合入，认证提示、校验错误响应和业务边界测试通过 PR #4 合入 dev（合并提交 0fb9d98）。此前 CI 已验证测试、空库迁移和镜像构建；本次文档整理未独立查询 PR #4 的 Checks 结果。

本地数据库恢复、容器备份导出和镜像发布回退已验收；
Windows 备份导入独立容器的练习按学习者决定暂缓，恢复验收移至服务器阶段，届时直接使用服务器备份验证隔离恢复。

服务器与域名已购买，Docker/Compose 和容器运行验收已完成，后端在服务器本机 /health 返回 ok（学习者反馈）。Vue 前端功能已实现，业务已通过 PR #5 合入，前端镜像已完成 SSH 隧道部署验收（学习者反馈）；备案仍在审批，当前收尾部署分支。

前后端业务联调、服务器数据持久化复验、HTTPS、代理后的来源 IP 验证、
定期备份与生产恢复验收等工作仍待完成。

手动备份恢复结果见 [服务器手动备份恢复验收记录](doc/服务器手动备份恢复验收记录.md)。

阶段进度见 [项目分阶段开发清单](doc/项目分阶段开发清单.md)，
接下来的学习安排见 [后续学习清单](doc/后续学习清单.md)，
工程化总结见 [第五阶段技术文档](doc/第五阶段技术文档.md)。

## Vue 前端开发（进行中）

frontend/ 使用 Vue 3、TypeScript、Vite、Vue Router、Vitest 和 fetch，已实现注册登录、退出、路由保护、账单增删改查、月份/分类筛选、分页和全月收支统计。
Token 仅保存在内存，刷新后需重新登录。开发代理将 /api 转发到本地 127.0.0.1:8000；服务器 Nginx 已实现 /api 反向代理，当前通过 SSH 隧道访问。
当前 34 个前端测试、TypeScript 检查和生产构建通过助手本地实跑。前端 CI 已配置，远端结果待 PR 核验；手机、键盘及双账号完整人工验收结果待记录。
服务器本机后端 /health 已通过验收（学习者反馈），域名已购买、备案审批中。
前后端业务联调、数据持久化复验和正式 HTTPS 发布仍待完成。

- [前端开发清单](doc/前端开发清单.md)：功能与交付状态。
- [前端学习清单](doc/前端学习清单.md)：逐课目标、第一课完整操作和验收。

部署记录与回退步骤见 [前端部署与回退记录](doc/前端部署与回退记录.md)。

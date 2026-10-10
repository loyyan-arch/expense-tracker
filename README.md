# 个人记账 API

使用 Python 和 FastAPI 开发的个人记账后端，支持用户认证、
账单管理和月度收支统计。

## 已实现功能

- 用户注册、登录及 JWT 身份认证。
- 创建、查询、修改、删除账单。
- 按分类、月份筛选账单，支持分页查询。
- 按月份统计收入、支出和结余。
- 用户只能访问自己的账单。
- 使用 Alembic 管理数据库结构变更。
- 请求日志：记录请求编号、方法、路径、状态码及处理耗时。

金额以整数“分”保存，例如 2500 表示 25.00 元。

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
| JWT_SECRET | JWT 签名密钥，至少 32 个字符 |
| ACCESS_TOKEN_EXPIRE_MINUTES | Token 有效期，单位为分钟，默认 30 |
| DATABASE_PATH | SQLite 数据库路径，默认 expenses.db |

相对数据库路径以项目根目录为基准。

系统环境变量优先于 `.env` 中的同名配置。
更换 JWT 密钥后，旧密钥签发的 Token 将无法通过验证。

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

目前共有 14 个测试用例，覆盖未登录访问、
部分无效 Token 场景和用户数据隔离等行为。

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

日志当前输出到终端，没有配置本地日志文件。

应用请求日志包含 request_id。
正常返回的响应中，可通过 `X-Request-ID` 响应头关联日志。

- **401**：检查是否授权、Token 是否过期、签名密钥是否变化。
- **404**：检查接口地址；账单可能不存在，或不属于当前用户。
- **422**：查看响应中的 detail，确认字段类型、日期及金额是否合法。
- **no such table**：检查是否执行迁移，以及数据库路径是否正确。
- **修改 .env 后没有生效**：手动重启服务，并检查是否有同名系统环境变量覆盖。
- **端口已被占用**：确认旧服务是否退出，或使用其他端口启动。

## 当前范围

目前完成了本地运行和自动化测试验证。
生产部署、HTTPS、登录限流、备份恢复演练等工作仍待完成。
# 个人记账前端

Vue 3 + TypeScript + Vite + Vue Router，使用 fetch 调用 FastAPI。

已实现注册、登录、退出、页面保护、账单增删改查、月份与分类筛选、分页和全月统计。Token 只保存在内存，刷新页面需要重新登录；退出清理前端状态，不撤销已签发的 JWT。

## 本地启动

Node 版本要求见 package.json，CI 使用 Node 24。首次安装或复现锁定依赖时，在 frontend 目录执行：

```sh
npm ci
npm run dev
```

另开终端，在项目根目录和已配置的 Python 环境中启动后端：

```sh
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

后端需要完成项目根 README 中的环境变量和数据库迁移配置。浏览器打开 Vite 输出的 Local 地址。开发代理将 /api 转发到 http://127.0.0.1:8000，并去掉 /api 前缀。

## 验证

```sh
npm run test:unit -- --run
npm run build
```

本次分支收尾实跑 5 个测试文件、34 个测试通过，类型检查和构建通过。组件测试使用模拟接口；手机、键盘和双账号真实业务验收需单独执行。

金额以元输入、以整数分提交；账单每页展示 10 条，请求 11 条判断是否存在下一页。月度统计包含所选月份的全部分类和分页；清空月份时不显示单月统计。

## 发布状态

构建产物位于 dist/，不提交 Git；node_modules/ 同样忽略，package-lock.json 需要提交。

GitHub 前端工作流执行 npm ci、测试和构建，远端结果需在 PR 中核验。当前尚未部署前端。生产环境需要静态服务器、history 路由回退及 /api 反向代理；Vite dev/preview 不作为生产服务器。

完整学习与交付状态见 ../doc/前端学习清单.md 和 ../doc/前端开发清单.md。

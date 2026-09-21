# 接口测试执行微服务

Flask + unittest。Django 传入前端已保存的接口/用例/数据，本服务发 HTTP、断言、写日志和报告。

```bash
python wsgi.py
```

默认 `http://127.0.0.1:8003`，健康检查 `GET /health`，执行 `POST /api/run`。

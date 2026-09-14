# AI Testcase Service

Flask 微服务，负责 AI 测试用例生成的 RAG 与六步流水线能力：

1. 文档解析（pdf/docx 图文分离）
2. 图片交互理解（vision，可降级跳过）
3. 功能点提取（JSON）
4. 项目知识库需求关联（RAG）
5. 测试方向拆分（业务/功能/其他）
6. 流式生成测试用例（SSE）

Django（`backend/`）作为 BFF 网关，负责鉴权、业务 CRUD 与用例落库；前端 API 不变。

## 目录结构

```
ai-testcase-service/
├── app/
│   ├── api/           # HTTP 路由
│   ├── clients/       # LLM / Embedding / Rerank / Vision 客户端
│   ├── models/        # SQLAlchemy KB 模型
│   ├── prompts/       # 各步骤 Prompt 模板
│   ├── services/      # ingest / generator / pipeline 业务逻辑
│   └── utils/         # 分块、相似度、JSON 解析
├── tests/
├── wsgi.py
└── requirements.txt
```

## 环境变量

复制 `.env.example` 为 `.env` 并配置：

| 变量 | 说明 |
|------|------|
| `DATABASE_URL` | 与 Django 共享的 MySQL 连接 |
| `AI_SERVICE_INTERNAL_TOKEN` | 内部鉴权 Token，需与 Django `AI_SERVICE_INTERNAL_TOKEN` 一致 |
| `PORT` | 默认 8002 |

Django 侧需配置：

```bash
AI_SERVICE_BASE_URL=http://127.0.0.1:8002
AI_SERVICE_INTERNAL_TOKEN=dev-internal-token
```

## 本地启动

```bash
# 1. 微服务
cd ai-testcase-service
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 编辑 DATABASE_URL 与 TOKEN
python wsgi.py

# 2. Django BFF
cd ../backend
source venv/bin/activate
export AI_SERVICE_BASE_URL=http://127.0.0.1:8002
export AI_SERVICE_INTERNAL_TOKEN=dev-internal-token
python manage.py runserver 8001

# 3. 前端
cd ../frontend
npm run serve
```

## Internal API

### POST /internal/v1/ingest

Headers: `X-Internal-Token`, `X-User-Id`

### POST /internal/v1/generate/stream

Headers: `X-Internal-Token`, `X-User-Id`

请求体示例：

```json
{
  "query": "请生成完整功能测试用例",
  "requirement_kb_id": 12,
  "testcase_kb_id": 5,
  "file_path": "/abs/path/to/doc.docx",
  "pipeline": true,
  "llm_config": {},
  "vision_config": {},
  "embedding_config": {},
  "rerank_config": {}
}
```

- `pipeline=true`（默认）：走六步流水线
- `pipeline=false`：回退旧版双库 RAG 直接生成

返回 SSE 事件：

| response_type | 说明 |
|---------------|------|
| `pipeline` | 各步骤进度（document_load / image_analyze / feature_extract / kb_match / direction_split / testcase_generate） |
| `feature_points` | 功能点 JSON 数组 |
| `matched_requirements` | 每个功能点的 KB 关联结果 |
| `test_directions` | 测试方向拆分结果 |
| `references` | 检索引用 |
| `answer` | 流式用例内容 |
| `error` | 错误信息 |

### GET /health

健康检查

## 部署说明

- Django 与微服务需能访问同一 `file_path`（开发环境同机；Docker 部署需共享 `media/` volume）
- 未配置视觉模型时，Step2 自动跳过并在 `pipeline` 事件中提示

## 测试

```bash
cd ai-testcase-service
python -m unittest discover -s tests -v
```

```bash
cd backend
python manage.py test functional_test
```

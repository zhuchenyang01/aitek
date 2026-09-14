# AItek 自研 RAG 框架（无 LangChain）

按图片流程实现：需求文档图文分离 → 视觉转写 → 纯文本 → 分块向量 / 功能点抽取 → FAISS+jsonl → 关联检索 → rerank → LLM 增强。

## 目录

```text
rag/
  config.py
  utils/          # timing 装饰器、相似度(math/numpy)
  loaders/        # PDF/Word 图文分离
  models/         # LLM / Vision / Embedding / Rerank
  pipeline/       # step1 ~ step9（每步可单独看）
  store/          # FAISS、jsonl、md
  examples/run_pipeline.py
  data/           # 运行产物
```

## 安装

```bash
cd rag
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

建议在**项目根目录**设置 `PYTHONPATH` 后运行（或直接用下面命令，脚本已自动加路径）：

```bash
export DEEPSEEK_API_KEY=你的密钥   # 可选；无密钥时 embedding/LLM/vision 会降级本地演示
python examples/run_pipeline.py
# 或指定文档
python examples/run_pipeline.py --doc /path/to/req.pdf
```

## 环境变量

| 变量 | 说明 |
|------|------|
| `DEEPSEEK_API_KEY` | 对话模型（功能点抽取 / LLM 增强） |
| `EMBEDDING_API_KEY` / `EMBEDDING_BASE_URL` / `EMBEDDING_MODEL` | 向量模型。默认本机 Ollama：`http://127.0.0.1:11434/v1` + `bge-m3:latest`（1024 维，无需 Key） |
| `VISION_API_KEY` / `VISION_MODEL` | 视觉转文字 |
| `RERANK_API_KEY` / `RERANK_BASE_URL` | 专用 rerank；不配则本地余弦重排 |
| `EMBEDDING_BATCH_SIZE` / `EMBEDDING_CONCURRENCY` | 批量大小与并发数 |

## 步骤说明

1. `step1_parse_document`：读 PDF/Word，分离文字与图片  
2. `step2_vision_to_text`：图片 → 文字（提示词约束无噪音）  
3. `step3_merge_pure_text`：合并纯文本 `data/pure_text.md`  
4. `step4_chunk_and_embed`：分块转向量 → `data/chunks.jsonl`  
5. `step5_extract_features`：对话模型提炼模块/功能点  
6. `step6_feature_embed_store`：功能点向量 → FAISS `[id,vector]` + jsonl `[id,功能点,向量]`  
7. `step7_associate_retrieve`：循环功能点做关联检索  
8. `step8_rerank`：重排  
9. `step9_llm_enhance`：LLM 增强输出  

每步带 `@timed` 打印耗时。

## 单独验证工具

```bash
python -m rag.utils.timing
python -m rag.utils.similarity
```

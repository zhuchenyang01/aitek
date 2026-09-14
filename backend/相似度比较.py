import numpy as np
import faiss
import time
import pandas as pd
import matplotlib.pyplot as plt
from docx import Document
from sentence_transformers import SentenceTransformer

# 解决中文显示问题
plt.rcParams["font.sans-serif"] = ["SimHei", "Arial Unicode MS", "PingFang SC", "Heiti SC"]
plt.rcParams["axes.unicode_minus"] = False

# ===================== 1.读取docx文档 =====================
def read_docx(file_path):
    doc = Document(file_path)
    paragraphs = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if len(text) > 1:  # 过滤掉空段落和过短的段落
            paragraphs.append(text)
    return paragraphs

docx_path = "/Users/zhuchenyang/AITEK_艾泰克/backend/长银需求--B端投保.docx"
# ---------------------------------------------------------------------------

texts = read_docx(docx_path)
print(f"读取docx完成，有效段落数量：{len(texts)}")

if len(texts) == 0:
    raise Exception("文档没有读取到任何有效文本！")

print("\n====读取到的段落====")
for i, p in enumerate(texts):
    print(f"[{i+1}] {p}")

# 使用多语言中文友好模型
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

# 文档段落转向量
database = model.encode(texts).astype(np.float32)
n_samples = database.shape[0]
dim = database.shape[1]

# 查询数量：如果样本很少，就少抽几个查询
n_query = min(50, len(texts))
np.random.seed(42)
query_idx = np.random.choice(range(len(texts)), size=n_query, replace=False)
query_texts = [texts[i] for i in query_idx]
query_set = model.encode(query_texts).astype(np.float32)

print(f"\n向量库大小={n_samples}, 查询数量={n_query}, 向量维度={dim}")

# 向量归一化，用于余弦相似度
def normalize(x):
    return x / np.linalg.norm(x, axis=1, keepdims=True)

db_norm = normalize(database)
q_norm = normalize(query_set)

# ===================== 2.原生numpy实现 =====================
class NativeSim:
    @staticmethod
    def euclidean_l2(a, b):
        return np.sqrt(np.sum((a - b) ** 2, axis=-1))

    @staticmethod
    def cosine(a_norm, b_norm):
        return np.dot(a_norm, b_norm.T)


def native_search(db, qs, topk, sim_func=None, is_small_better=True):
    m = qs.shape[0]
    res_ids = []
    res_scores = []
    t0 = time.time()
    for q in qs:
        scores = sim_func(db, q)
        if is_small_better:
            idx = np.argsort(scores)[:topk]
        else:
            idx = np.argsort(-scores)[:topk]
        res_ids.append(idx)
        res_scores.append(scores[idx])
    cost = time.time() - t0
    return np.array(res_ids), np.array(res_scores), cost

# ===================== 3.FAISS实现 =====================
def faiss_search(db, qs, topk, metric=faiss.METRIC_L2):
    index = faiss.IndexFlat(dim, metric)
    index.add(db)
    t0 = time.time()
    scores, ids = index.search(qs, topk)
    cost = time.time() - t0
    return ids, scores, cost

# ===================== 4.召回率计算 =====================
def calc_recall(pred_ids, gt_ids):
    total = 0.0
    for p, g in zip(pred_ids, gt_ids):
        hit = len(set(p) & set(g))
        total += hit / len(g)
    return total / len(pred_ids)


# ----------------------运行实验----------------------
top_k = min(5, n_samples)

# GroundTruth：原生余弦相似度结果
gt_ids, gt_scores, _ = native_search(db_norm, q_norm, topk=top_k, sim_func=NativeSim.cosine, is_small_better=False)

exp_result = []

# 原生算法
native_tests = [
    ("原生_L2", NativeSim.euclidean_l2, database, query_set, True),
    ("原生_余弦", NativeSim.cosine, db_norm, q_norm, False),
]

for name, func, db_data, q_data, small_better in native_tests:
    pred_ids, pred_scores, t_cost = native_search(db_data, q_data, topk=top_k, sim_func=func, is_small_better=small_better)
    recall = calc_recall(pred_ids, gt_ids)
    exp_result.append({
        "algorithm": name,
        "lib": "native_python",
        "time_s": round(t_cost, 4),
        f"recall@{top_k}": round(recall, 4),
        "topk": top_k
    })

# FAISS算法
faiss_tests = [
    ("Faiss_L2", faiss.METRIC_L2, database, query_set),
    ("Faiss_余弦", faiss.METRIC_INNER_PRODUCT, db_norm, q_norm),
]

for name, metric, db_data, q_data in faiss_tests:
    pred_ids, pred_scores, t_cost = faiss_search(db_data, q_data, topk=top_k, metric=metric)
    recall = calc_recall(pred_ids, gt_ids)
    exp_result.append({
        "algorithm": name,
        "lib": "faiss",
        "time_s": round(t_cost, 4),
        f"recall@{top_k}": round(recall, 4),
        "topk": top_k
    })

df_report = pd.DataFrame(exp_result)
print("="*75)
print("【余弦相似度 & L2欧式距离 实验结果】")
print(df_report.to_string(index=False))
print("="*75)

# ===================== 5.打印每个查询的检索结果 =====================
print("\n====查询与原生余弦检索结果====")
for query_idx in range(n_query):
    print(f"\n查询 {query_idx+1}：{query_texts[query_idx]}")
    top_ids = gt_ids[query_idx]
    top_scores = gt_scores[query_idx]
    for rank, (doc_id, score) in enumerate(zip(top_ids, top_scores)):
        print(f"  结果{rank+1}：相似度={score:.4f}，内容={texts[doc_id]}")

# ===================== 6.画更清晰的图 =====================
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

# 耗时图
ax1.bar(df_report["algorithm"], df_report["time_s"], color="#4C78A8")
ax1.set_title("检索总耗时", fontsize=14)
ax1.set_ylabel("时间 / 秒", fontsize=12)
ax1.set_xlabel("算法", fontsize=12)
ax1.tick_params(axis='x', rotation=30, labelsize=11)
ax1.grid(axis='y', linestyle='--', alpha=0.5)

ax1.set_ylim(0, 0.002)  # 设置y轴范围，便于显示数值
# 柱子上显示数值
for bar in ax1.patches:
    h = bar.get_height()
    ax1.text(bar.get_x()+bar.get_width()/2, h, f"{h:.6f}", ha="center", va="bottom", fontsize=8)

# 召回率图
recall_col = f"recall@{top_k}"
ax2.bar(df_report["algorithm"], df_report[recall_col], color="#F5B800")
ax2.set_title(f"{recall_col} 召回率", fontsize=14)
ax2.set_ylabel("召回率", fontsize=12)
ax2.set_xlabel("算法", fontsize=12)
ax2.tick_params(axis='x', rotation=30, labelsize=11)
ax2.grid(axis='y', linestyle='--', alpha=0.5)

plt.tight_layout()
plt.savefig("cos_l2_docx_result.png", dpi=150)
plt.show()

# ===================== 7.生成Markdown报告 =====================
md_text = rf"""# 余弦相似度与L2欧式距离对比实验报告

## 1.实验环境
- numpy版本：{np.__version__}
- faiss版本：{faiss.__version__}
- Embedding模型：paraphrase-multilingual-MiniLM-L12-v2
- 文档来源：{docx_path}
- 向量库样本数：{n_samples}
- 查询向量数量：{n_query}
- 向量维度：{dim}
- TopK：{top_k}

## 2.实验说明
本次实验使用真实docx文档读取段落，并通过Embedding模型生成文本向量，对比两种向量相似度计算方式：

1. **L2欧式距离**  
   距离越小，表示向量越接近。  
   公式：

$$

$$

2. **余弦相似度**  
   余弦值越大，表示向量方向越接近。  
   公式：



Faiss没有直接提供余弦相似度接口，因此采用标准做法：

> 先对向量做L2归一化，再使用内积 `METRIC_INNER_PRODUCT`，此时内积等价于余弦相似度。

## 3.实验结果
{df_report.to_markdown(index=False)}

## 4.结果分析

### 4.1 性能分析
从耗时结果可以看出，原生numpy实现由于是循环暴力检索，速度较慢。  
Faiss底层使用C++实现，索引和搜索经过优化，相同条件下检索速度明显更快。

### 4.2 召回率分析
本次实验以“原生numpy余弦相似度Top{top_k}”作为真值。

- **原生余弦**作为真值，召回率最高；
- **Faiss余弦**在向量归一化后使用内积，结果应与原生余弦接近；
- **L2欧式距离**和余弦相似度的数学定义不同，因此召回率不一定高。

### 4.3 方法对比

| 方法 | 特点 | 适合场景 |
|---|---|---|
| L2欧式距离 | 同时考虑向量方向和模长 | 图像特征、数值特征、模长有物理意义的数据 |
| 余弦相似度 | 只考虑向量方向，不受模长影响 | 文本Embedding、语义检索、问答匹配 |

## 5.结论
如果你的目标是做文档语义检索，优先使用：

> **余弦相似度 + 文本Embedding向量归一化**

如果你的数据是图像特征或数值特征，且模长具有实际含义，可以优先使用：

> **L2欧式距离**

## 6.输出文件
- `cos_l2_docx_result.png`：实验结果柱状图  
- `余弦_L2_docx实验报告.md`：完整实验报告  
"""

with open("余弦_L2_docx实验报告.md", "w", encoding="utf-8") as f:
    f.write(md_text)

print("\n✅输出完成：cos_l2_docx_result.png、余弦_L2_docx实验报告.md")
print("\n📌使用的查询文本：")
for idx, t in enumerate(query_texts):
    print(f"【查询{idx+1}】{t}")
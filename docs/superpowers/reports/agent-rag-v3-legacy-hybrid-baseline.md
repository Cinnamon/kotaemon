# V3 完整方案相对旧式混合召回基线

## 实验口径

- 冻结语料：22 份文档、80 道审核题、139 个证据锚点；所有实验共用同一快照、gold 和本地模型指纹。
- 固定分块基线：`TokenSplitter`，1024 tokens，overlap 256；共 473 chunks。
- 检索基线：SQLite FTS5 全文检索 top-20 在前，BGE-M3 向量 top-20 追加在后；按 chunk ID 稳定去重，最多 40 个候选；不使用 RRF、reranker、query enrichment 或 evidence expansion。
- 向量结果直接回放冻结 V3 dense-only arm 中相同模型、相同分块方式的 top-20 ID；全文候选在本机 SQLite FTS5 上重新检索。这样复用同一向量结果，不做重复 embedding 推理。
- 结构分块桥接组使用同一个 `get_chunk_strategy` registry，回退分块参数仍是 1024/256；该组用于单独看 chunking 的影响，共生成 538 chunks。
- Hit@5、Recall@5、MRR@5 是 80 道题上的宏平均，按前 5 个不同来源文档计分。Wrong-scope@5 是所有有范围标注题目的错误来源数 / 实际返回的不同来源数之和，保留每组分子和分母。

旧方案的合并顺序与 Kotaemon V3 前的 lexical-first ID 去重语义一致。受控补测使用当前本地 SQLite FTS5 backend，因此不声称逐字节复刻历史生产全文检索引擎；模型、gold、向量候选和评分口径则与已冻结 V3 结果绑定。

## 结果

| 阶段 | Hit@5 | Recall@5 | MRR@5 | Wrong-scope@5 |
|---|---:|---:|---:|---:|
| 固定 Token + 全文优先合并（baseline） | 79/80 = **98.75%** | **96.04%** | **0.6575** | 21/336 = **6.25%** |
| Registry 分块 + 全文优先合并（chunking bridge） | 78/80 = 97.50% | 94.17% | 0.6856 | 17/338 = 5.03% |
| + Weighted RRF | 80/80 = 100.00% | 99.58% | 0.8515 | 13/338 = 3.85% |
| + Cross-Encoder ReRanker | 80/80 = 100.00% | 99.58% | 0.9344 | 9/338 = 2.66% |
| + Query enrichment | 80/80 = 100.00% | 99.58% | 0.9354 | 11/349 = 3.15% |
| + Evidence expansion（完整 V3） | 80/80 = **100.00%** | **99.58%** | **0.9354** | **11/349 = 3.15%** |

### 完整 V3 相对固定 Token baseline

| 指标 | baseline | 完整 V3 | 变化 |
|---|---:|---:|---:|
| Hit@5 | 98.75% | 100.00% | **+1.25 个百分点**（多命中 1 道题） |
| Recall@5 | 96.04% | 99.58% | **+3.54 个百分点** |
| MRR@5 | 0.6575 | 0.9354 | **+0.2779**（相对提升约 42.27%） |
| Wrong-scope@5 | 6.25%（21/336） | 3.15%（11/349） | **下降 3.10 个百分点**，错误来源数减少 10 |

### 分阶段变化

以下变化均为当前阶段减去上一阶段；率的差值用百分点，MRR 用 0–1 原值差。

| 改动 | Hit@5 | Recall@5 | MRR@5 | Wrong-scope@5 | 观察 |
|---|---:|---:|---:|---:|---|
| Token baseline → Registry 分块 | -1.25 pp | -1.88 pp | +0.0281 | -1.22 pp | MRR 和范围错误率改善，但 Hit/Recall 略降；本组数据不支持“分块单独提升所有指标”。 |
| 全文优先拼接 → Weighted RRF | +2.50 pp | +5.42 pp | +0.1658 | -1.18 pp | 本次最大单步提升；候选池覆盖相同，主要提升发生在候选排序。 |
| 加 Cross-Encoder ReRanker | 0.00 pp | 0.00 pp | +0.0829 | -1.18 pp | 提升相关来源在 top-5 中的前置程度，并减少范围外来源。 |
| 加 Query enrichment | 0.00 pp | 0.00 pp | +0.0010 | +0.49 pp | MRR 仅小幅提高，Wrong-scope 反而上升；当前数据不能把它描述成全面收益。 |
| 加 Evidence expansion | 0.00 pp | 0.00 pp | 0.0000 | 0.00 pp | 不改变检索排序指标；主要用于补充生成上下文。 |

旧式 hybrid 和完整 V3 的 candidate Recall@40 都是 **108/109 = 99.08%**。这说明在该 gold 上，V3 相对基线的 top-5 Recall/MRR 改善主要来自更好的融合与排序，而不是扩大 40 个候选的来源覆盖。Wrong-scope 的 pooled denominator 随返回的不同来源数量变化，所以同时报告了原始分子/分母。

完整 V3 的 final-context anchor coverage 为 **109/139 = 78.42%**（unresolved 0）。旧式基线没有运行 V3 context packing，因此该项没有可比 baseline；不把它写成提升值。答案支持率、引用准确率和生成质量也不在这次检索补测范围内。

## 复现与审核

从仓库根目录执行以下命令。数据、模型和逐题 chunk ID 留在 Git 忽略的本地目录；提交到仓库的只有本聚合报告。

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --package ktem python -m kotaemon.indices.knowledge.evaluation.local_cli supplemental-baseline \
  --local-root libs/kotaemon/tests/fixtures/knowledge_eval/local \
  --snapshot libs/kotaemon/tests/fixtures/knowledge_eval/local/snapshots/v2 \
  --embedding-model-dir libs/kotaemon/tests/fixtures/knowledge_eval/local/models/bge-m3 \
  --reranker-model-dir libs/kotaemon/tests/fixtures/knowledge_eval/local/models/bge-reranker-v2-m3 \
  --reference-artifact-dir libs/kotaemon/tests/fixtures/knowledge_eval/local/runs/v3-combination-checkpointed-repacked \
  --artifact-dir libs/kotaemon/tests/fixtures/knowledge_eval/local/runs/supplemental-legacy-hybrid-v2
```

- 本次机器可读聚合结果位于本机 Git 忽略目录 `libs/kotaemon/tests/fixtures/knowledge_eval/local/runs/supplemental-legacy-hybrid-v2/report.json`。
- 本地逐题 route/merge chunk ID 位于 `libs/kotaemon/tests/fixtures/knowledge_eval/local/runs/supplemental-legacy-hybrid-v2/private-results.json`；该文件不提交到 Git。
- 对照的完整 V3 验证报告：[agent-rag-pipeline-v3-validation.md](agent-rag-pipeline-v3-validation.md)

补测程序会验证 approved snapshot、80 个 query ID、V3 run checkpoint、所有 reference artifact SHA-256、模型 manifest、候选 cutoff 与分块配置后才评分。该结果为固定 mini corpus 上的描述性指标，没有做统计显著性检验，不外推为生产语料效果。

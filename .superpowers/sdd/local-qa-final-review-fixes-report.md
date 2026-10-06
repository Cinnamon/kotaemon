# Local QA Final Review Corrections

Base: `41ab7ed7b60122422aacab9a70ee29d689cd5879`

## Changes

- Updated both K=2 Zhang trace references in `agent-retrieval-evaluation-k2.json` to the K=2 trace artifact. The K=5 evaluation and trace remain unchanged.
- Reworded the Local QA privacy note to describe the question and retrieved evidence cards sent over loopback HTTP to Ollama, the answer returned to the UI, and the workbench's snapshot/trace-file write behavior. It makes no claim about Ollama process memory or retention.
- `IndexPipeline.stream` now rejects caller `knowledge_metadata` containing `file_id`, `document_id`, or `collection_name` before path lookup, source storage, reader loading, or indexing. Tests also cover allowed custom metadata reaching chunks and Source.note, and trusted reader-provided `document_id` normalization.
- Updated the design and implementation plan with the reserved identity-key rule.

## Verification

TDD RED, before the implementation change:

```text
uv run pytest libs/ktem/ktem_tests/test_knowledge_indexing.py -q
3 failed, 11 passed
```

The three expected failures were the reserved-key cases, each reporting that `ValueError` was not raised. All other ingestion tests passed.

After implementation:

```text
uv run black libs/ktem/ktem/index/file/pipelines.py libs/ktem/ktem_tests/test_knowledge_indexing.py
# All done! 1 file reformatted, 1 file left unchanged.

uv run pytest libs/ktem/ktem_tests/test_knowledge_indexing.py libs/kotaemon/tests/test_splitter.py libs/kotaemon/tests/test_indexing_retrieval.py -q
# 17 passed, 4 warnings in 6.74s
```

The four warnings are existing `PydanticDeprecatedSince20` warnings from `kotaemon/embeddings/openai.py` using `dict()`.

The K=2/K=5 artifact check was run as a one-shot JSON assertion:

```python
import json
from pathlib import Path

repo = Path.cwd()
artifacts = repo / "docs/superpowers/reports/artifacts"
k2_evaluation = json.loads(
    (artifacts / "agent-retrieval-evaluation-k2.json").read_text(encoding="utf-8")
)
k5_evaluation = json.loads(
    (artifacts / "agent-retrieval-evaluation.json").read_text(encoding="utf-8")
)
zhang = next(
    item for item in k2_evaluation["planned_observations"]
    if item["id"] == "zhang-internship"
)
k2_trace_ref = zhang["trace_artifact_path"]
assert k2_evaluation["trace_artifact"] == k2_trace_ref
k2_trace_path = repo / k2_trace_ref
assert k2_trace_path.is_file(), k2_trace_path
k2_trace = json.loads(k2_trace_path.read_text(encoding="utf-8"))
assert k2_trace["candidate_k"] == 2, k2_trace["candidate_k"]
k5_trace_ref = k5_evaluation["trace_artifact"]
assert k2_trace_ref != k5_trace_ref
k5_trace_path = repo / k5_trace_ref
assert k5_trace_path.is_file(), k5_trace_path
k5_trace = json.loads(k5_trace_path.read_text(encoding="utf-8"))
assert k5_trace["candidate_k"] == 5, k5_trace["candidate_k"]
print(
    "PASS: K=2 Zhang references resolve to the distinct K=2 trace; "
    "K=5 trace remains candidate_k=5."
)
```

Result: `PASS: K=2 Zhang references resolve to the distinct K=2 trace; K=5 trace remains candidate_k=5.`

No Ollama process or network request was used. The scoped retrieval tests created two Chroma output directories named from the patched `Embeddings.create` mock; both were verified to contain only test-generated Chroma files and removed.

## Doc-only wording follow-up

At follow-up HEAD `56af37b3`, narrowed the generation-flow sentence in `docs/local-qa-playground.md` to match `answer_question`: only a non-empty question with retrieved evidence is sent to Ollama; only a successful generation returns an answer; empty input, no evidence, and generation failure are described as their actual bypass/error outcomes. Kept the snapshot/own-trace no-write and Ollama retention-scope statements.

Validation: reviewed the wording against the `answer_question` branches and ran `git diff --check` successfully. No tests were rerun for this documentation-only change, and no Ollama or network request was made.

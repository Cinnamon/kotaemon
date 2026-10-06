"""Fixed combination and leave-one-component-out experiment arms."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

SOURCE_K = 5

CANDIDATE_K = 20

MAX_FUSED_CANDIDATES = 40

MAX_QUERY_VARIANTS = 3


def get_arm_configurations() -> dict[str, dict[str, Any]]:
    """Return fresh, explicit cumulative and leave-one-component-out arms."""
    components = {
        "chunking_mode": "token",
        "lexical_rrf": False,
        "reranker": False,
        "query_enrichment": False,
        "evidence_expansion": False,
    }
    arms: dict[str, dict[str, Any]] = {}

    def add(name: str, *, comparison: str, changes: Mapping[str, Any], **extra):
        nonlocal components
        components = {**components, **changes}
        arms[name] = {
            "comparison": comparison,
            "components": dict(components),
            "candidate_k_per_route": CANDIDATE_K,
            "max_fused_candidates": MAX_FUSED_CANDIDATES,
            "source_k": SOURCE_K,
            "seed_budget": {
                "model_context": 32768,
                "output_reserve": 2048,
                "format_reserve": 256,
                "counter": "local_qwen_tokenizer_or_utf8_byte_estimate",
            },
            "coupled_dependencies": [],
            **extra,
        }

    arms["dense_baseline"] = {
        "comparison": "baseline",
        "components": dict(components),
        "candidate_k_per_route": CANDIDATE_K,
        "max_fused_candidates": MAX_FUSED_CANDIDATES,
        "source_k": SOURCE_K,
        "seed_budget": {
            "model_context": 32768,
            "output_reserve": 2048,
            "format_reserve": 256,
            "counter": "local_qwen_tokenizer_or_utf8_byte_estimate",
        },
        "coupled_dependencies": [],
    }
    add(
        "registry_chunking",
        comparison="incremental",
        changes={"chunking_mode": "registry"},
    )
    add("registry_lexical_rrf", comparison="incremental", changes={"lexical_rrf": True})
    add("registry_reranking", comparison="incremental", changes={"reranker": True})
    add(
        "registry_enrichment",
        comparison="incremental",
        changes={"query_enrichment": True},
    )
    add(
        "registry_expansion",
        comparison="combined",
        changes={"evidence_expansion": True},
    )

    final_components = dict(components)
    ablations = {
        "ablation_no_chunking": ("chunking_mode", "token", []),
        "ablation_dense_only": ("lexical_rrf", False, []),
        "ablation_no_reranker": (
            "reranker",
            False,
            ["expansion_score_gate_unavailable"],
        ),
        "ablation_no_enrichment": ("query_enrichment", False, []),
        "ablation_no_expansion": ("evidence_expansion", False, []),
    }
    for name, (component, value, dependencies) in ablations.items():
        arms[name] = {
            "comparison": "leave_one_component_out",
            "ablation_of": "registry_expansion",
            "components": {**final_components, component: value},
            "candidate_k_per_route": CANDIDATE_K,
            "max_fused_candidates": MAX_FUSED_CANDIDATES,
            "source_k": SOURCE_K,
            "seed_budget": dict(arms["registry_expansion"]["seed_budget"]),
            "coupled_dependencies": list(dependencies),
        }
    return arms

"""Public entry points for fixed combination and conversation evaluation.

Fixture validation, per-query execution, arm definitions, and artifact formats
live in focused modules. This module re-exports the stable API and the small set
of established private helpers used by the evaluation regression tests.
"""

from .combination_arms import (
    CANDIDATE_K,
    MAX_FUSED_CANDIDATES,
    MAX_QUERY_VARIANTS,
    SOURCE_K,
    get_arm_configurations,
)
from .combination_artifacts import (
    CombinationArmReport,
    CombinationReport,
    _canonical_json,
    _fingerprint,
    _sha256,
    read_generation_inputs,
)
from .combination_runner import (
    repack_completed_combination_experiment,
    run_combination_experiment,
)
from .combination_runtime import (
    _search_case,
    _verify_zero_invariants,
)
from .source_metrics import score_candidate_recall
from .conversation_fixtures import (
    ConversationAnchor,
    ConversationCase,
    ConversationFixture,
    ConversationTurn,
    SimpleCase,
    _reject_label_leaking_source_metadata,
    _validate_conversation_fixture_snapshot,
    _validate_snapshot_constraints,
    load_conversation_fixture,
    validate_conversation_fixture_sources,
)

__all__ = [
    "CANDIDATE_K",
    "MAX_FUSED_CANDIDATES",
    "MAX_QUERY_VARIANTS",
    "SOURCE_K",
    "CombinationArmReport",
    "CombinationReport",
    "ConversationAnchor",
    "ConversationCase",
    "ConversationFixture",
    "ConversationTurn",
    "SimpleCase",
    "get_arm_configurations",
    "load_conversation_fixture",
    "read_generation_inputs",
    "repack_completed_combination_experiment",
    "run_combination_experiment",
    "score_candidate_recall",
    "validate_conversation_fixture_sources",
    "_canonical_json",
    "_fingerprint",
    "_reject_label_leaking_source_metadata",
    "_search_case",
    "_sha256",
    "_validate_conversation_fixture_snapshot",
    "_validate_snapshot_constraints",
    "_verify_zero_invariants",
]

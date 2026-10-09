"""CHAI backend package initialization and runtime compatibility layer."""
import sys
from collections import defaultdict

# 1. Ensure langchain.debug compatibility across langchain_core versions
try:
    import langchain
    if not hasattr(langchain, "debug"):
        langchain.debug = False
except ImportError:
    pass

# 2. Ensure langgraph 0.0.x / langgraph-checkpoint 4.x compatibility
try:
    import langgraph.checkpoint.base

    _orig_empty = langgraph.checkpoint.base.empty_checkpoint
    _orig_copy = langgraph.checkpoint.base.copy_checkpoint

    def _make_seen(d):
        res = defaultdict(lambda: defaultdict(int))
        if d:
            for k, v in d.items():
                res[k] = defaultdict(int, v)
        return res

    def _patched_empty_checkpoint():
        cp = _orig_empty()
        cp["channel_versions"] = defaultdict(int, cp.get("channel_versions", {}))
        cp["versions_seen"] = _make_seen(cp.get("versions_seen", {}))
        return cp

    def _patched_copy_checkpoint(checkpoint):
        cp = _orig_copy(checkpoint)
        cp["channel_versions"] = defaultdict(int, cp.get("channel_versions", {}))
        cp["versions_seen"] = _make_seen(cp.get("versions_seen", {}))
        return cp

    langgraph.checkpoint.base.empty_checkpoint = _patched_empty_checkpoint
    langgraph.checkpoint.base.copy_checkpoint = _patched_copy_checkpoint
except (ImportError, AttributeError):
    pass

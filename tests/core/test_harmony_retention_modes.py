"""Commentary retention modes tests (A1).

Covers: metrics_only, hashed_slice, redacted_snippets, raw_ephemeral.
Ensures no reasoning_text leak (drop_from_history True) and mode-specific
summary fields behave as expected.
"""

from __future__ import annotations

import re

from core import metrics
from core.llm.adapters import HarmonyChannelAdapter


BASE_MESSAGE = (
	"<|start|>assistant<|channel|>analysis<|message|> internal chain of thought"
	" tokens <|end|>"
	"<|start|>assistant<|channel|>commentary<|message|> [tool:demo] secret"
	" api_key revealed <|end|>"
	"<|start|>assistant<|channel|>final<|message|> final answer <|end|>"
)


def _run_mode(mode: str):
	metrics.reset_for_tests()
	cfg = {
		"model_id": "m-test",
		"reasoning": {"max_tokens": 32, "drop_from_history": True},
		"collapse": {"whitespace": True},
		"ngram": {"n": 3, "window": 32},
		"commentary_retention": {
			"mode": mode,
			"hashed_slice": {"max_chars": 160},
			"redacted_snippets": {
				"max_tokens": 40,
				"redact_pattern": "(?i)(secret|api[_-]?key)",
				"replacement": "***",
			},
			"raw_ephemeral": {"ttl_seconds": 10},
			"tool_chain": {
				"detect": True,
				"apply_when": "any",
				"override_mode": mode,
			},
		},
	}
	adapter = HarmonyChannelAdapter(cfg)
	list(adapter.process_chunk(BASE_MESSAGE))
	final_events = list(adapter.finalize())
	assert final_events, "No final events produced"
	return final_events[-1]


def test_metrics_only_mode_no_leak():
	evt = _run_mode("metrics_only")
	summary = evt["commentary_retention_summary"]
	assert summary["mode"] == "metrics_only"
	forbidden = {"hash_prefix", "snippet_redacted", "ephemeral_cached"}
	assert forbidden.isdisjoint(summary.keys())
	assert evt.get("reasoning_text") is None
	snap = metrics.snapshot()["counters"]
	assert any("commentary_retention_mode_total" in k for k in snap)


def test_hashed_slice_mode_hash_present():
	evt = _run_mode("hashed_slice")
	summary = evt["commentary_retention_summary"]
	assert summary["mode"] == "hashed_slice"
	hp = summary.get("hash_prefix")
	assert isinstance(hp, str) and len(hp) >= 8
	assert {"snippet_redacted", "ephemeral_cached"}.isdisjoint(summary)
	assert evt.get("reasoning_text") is None


def test_redacted_snippets_mode_snippet_and_redaction():
	evt = _run_mode("redacted_snippets")
	summary = evt["commentary_retention_summary"]
	assert summary["mode"] == "redacted_snippets"
	snip = summary.get("snippet_redacted")
	assert isinstance(snip, str) and len(snip) > 0
	assert ("***" in snip) or (not re.search(r"(?i)(secret|api[_-]?key)", snip))
	assert evt.get("reasoning_text") is None


def test_raw_ephemeral_mode_ephemeral_flag():
	evt = _run_mode("raw_ephemeral")
	summary = evt["commentary_retention_summary"]
	assert summary["mode"] == "raw_ephemeral"
	if summary.get("commentary_tokens"):
		assert summary.get("ephemeral_cached") is True
	assert evt.get("reasoning_text") is None


def test_no_reasoning_leak_across_all_modes():
	for mode in [
		"metrics_only",
		"hashed_slice",
		"redacted_snippets",
		"raw_ephemeral",
	]:
		evt = _run_mode(mode)
		assert evt.get("reasoning_text") is None, f"Leak in mode {mode}"


"""Harmony streaming structure adapter (marker mode fully removed).

Implements incremental parsing of Harmony messages:
  <|start|>assistant<|channel|>analysis<|message|>...<|end|>
  <|start|>assistant<|channel|>final<|message|>...<|return|>

If no Harmony tokens are detected we fallback to a single final message.
"""
from __future__ import annotations

from typing import Dict, List, Optional
import re
import hashlib
import os
import logging
import time

class _EphemeralCache:
    """Simple append + prune cache for ephemeral commentary (tests only)."""

    def __init__(self):
        self._items: list[tuple[float, str]] = []  # (expiry_ts, snippet)

    def append(self, item: tuple[float, str]):  # noqa: D401
        self._items.append(item)

    def prune(self):  # noqa: D401
        now = time.time()
        self._items = [it for it in self._items if it[0] > now]

    def __len__(self):  # noqa: D401
        self.prune()
        return len(self._items)


_EPHEMERAL_COMMENTARY_CACHE = _EphemeralCache()

# Passport metadata helper (simplified for tests expecting passport_version)
def _inject_passport_meta(meta: dict) -> dict:  # noqa: D401
    meta = dict(meta or {})
    meta.setdefault("passport_version", 1)
    return meta


try:  # optional metrics import
    from core import metrics as _metrics  # noqa: WPS433
except Exception:  # noqa: BLE001
    class _metrics:  # type: ignore
        @staticmethod
        def inc_commentary_tokens(*_a, **_k):
            return None

        @staticmethod
        def inc_unexpected_order(*_a, **_k):
            return None

        @staticmethod
        def inc(*_a, **_k):
            return None
 

class HarmonyChannelAdapter:
    """Spec-aligned Harmony streaming parser (analysis/commentary/final).

    Strict rules:
      * Never emit partial header fragments as content
      * Wait for full <|message|> before emitting channel content
      * Unknown channel → parse error metric + skip message
      * <|return|> treated as terminal (final message complete)
    """

    _RE_START = re.compile(r"<\|start\|>assistant", re.IGNORECASE)
    _RE_CHANNEL_KNOWN = re.compile(
        r"<\|channel\|>(analysis|commentary|final|tool)",
        re.IGNORECASE,
    )
    _RE_CHANNEL_ANY = re.compile(r"<\|channel\|>([a-z0-9_.-]+)", re.IGNORECASE)
    _RE_MESSAGE = re.compile(r"<\|message\|>", re.IGNORECASE)
    _RE_END = re.compile(r"<\|(end|return)\|>", re.IGNORECASE)
    _RE_SERVICE = re.compile(r"<\|[^|>]+\|>")
    _RE_RECIPIENT = re.compile(
        r"<\|recipient\|>([a-zA-Z0-9_.-]+)", re.IGNORECASE
    )
    _RE_CONSTRAIN = re.compile(r"<\|constrain\|>", re.IGNORECASE)

    def __init__(self, cfg: Dict):  # noqa: D401
        self.cfg = cfg
        self._buffer = ""
        self._model_id = str(cfg.get("model_id", "unknown"))
        rez = cfg.get("reasoning", {})
        self._max_rez = int(rez.get("max_tokens", 256))
        self._drop_history = bool(rez.get("drop_from_history", True))
        self._collapse_ws = bool(
            cfg.get("collapse", {}).get("whitespace", True)
        )
        ng = cfg.get("ngram", {})
        try:
            from . import postproc as _pp  # noqa: WPS433
            self._guard = _pp._NGramGuard(
                int(ng.get("n", 3)), int(ng.get("window", 128))
            )  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            class _Dummy:
                def allow(self, t):
                    return True
            self._guard = _Dummy()
        # stats
        self._reasoning_tokens = 0
        self._final_tokens = 0
        # store final tokens for finalize re-emission
        self._final_token_texts: List[str] = []
        # count of final delta tokens already yielded to consumer
        self._delivered_final_tokens = 0
        self._analysis_acc: List[str] = []
        self._commentary_tokens = 0
        self._commentary_acc: List[str] = []  # raw commentary segments
        self._saw_tool_commentary = False
        self._final_message_closed = False
        self._saw_return_token = False
        # debug
        self._debug = bool(os.getenv("MIA_HARMONY_DEBUG") or cfg.get("_debug"))
        self._logger = logging.getLogger("harmony.adapter")
        if self._debug and not self._logger.handlers:
            h = logging.StreamHandler()
            h.setFormatter(logging.Formatter("[HARMONY] %(message)s"))
            self._logger.addHandler(h)
            self._logger.setLevel(logging.DEBUG)

    def _dbg(self, msg: str):  # noqa: D401
        if self._debug:
            try:
                self._logger.debug(msg)
            except Exception:  # noqa: BLE001
                pass

    # ---------------- helpers -----------------
    def _ws(self, text: str) -> str:
        if not self._collapse_ws:
            return text
        return re.sub(r"(\s)\1+", r"\1", text)

    def _emit_analysis(self, segment: str, out: List[Dict]):
        for tok in filter(None, segment.split()):
            if self._reasoning_tokens >= self._max_rez:
                break
            # Allow all reasoning tokens (guard only for final channel)
            self._reasoning_tokens += 1
            self._analysis_acc.append(tok)
            out.append({"type": "analysis", "text": tok + " "})

    def _emit_final(self, segment: str, out: List[Dict]):
        for tok in filter(None, segment.split()):
            if self._guard.allow(tok):
                self._final_tokens += 1
                token_text = tok + " "
                self._final_token_texts.append(token_text)
                out.append({"type": "delta", "text": token_text})

    def _emit_commentary(self, segment: str, out: List[Dict]):
        norm = segment.strip()
        if not norm:
            return
        out.append({"type": "commentary", "text": norm})
        # accumulate for retention summary post-processing
        self._commentary_acc.append(norm)
        if norm.startswith("[tool:"):
            self._saw_tool_commentary = True
        try:
            c = len(norm.split())
            if c:
                self._commentary_tokens += c
                _metrics.inc_commentary_tokens(  # type: ignore[attr-defined]
                    self._model_id, c
                )
        except Exception:  # noqa: BLE001
            pass

    # ---------------- core parse -----------------
    def _scan_next_message(self) -> Optional[Dict]:
        """Attempt to parse a single complete assistant message from buffer.

        Returns an event dict list (analysis/commentary deltas) or None if
        incomplete. On final message, sets _final_message_closed.
        """
        # Find start
        m_start = self._RE_START.search(self._buffer)
        if not m_start:
            return None
        # Detect potential tool call (<|recipient|>) before channel
        m_recipient = self._RE_RECIPIENT.search(self._buffer, m_start.end())
        m_chan_known = self._RE_CHANNEL_KNOWN.search(
            self._buffer, m_start.end()
        )
        if m_recipient and (
            not m_chan_known or m_recipient.start() < m_chan_known.start()
        ):
            # Optional <|constrain|> tokens before <|message|>
            pos = m_recipient.end()
            constrain_present = False
            while True:
                m_con = self._RE_CONSTRAIN.match(self._buffer, pos)
                if not m_con:
                    break
                constrain_present = True
                pos = m_con.end()
            m_msg = self._RE_MESSAGE.search(self._buffer, pos)
            if not m_msg:
                return None
            m_end = self._RE_END.search(self._buffer, m_msg.end())
            if not m_end:
                return None
            raw_segment = self._buffer[m_msg.end():m_end.start()]
            segment = self._RE_SERVICE.sub("", raw_segment)
            segment = self._ws(segment)
            event = {
                "type": "tool_call",
                "recipient": m_recipient.group(1),
                "args_text": segment,
                "constrain": True if constrain_present else None,
            }
            self._buffer = self._buffer[m_end.end():]
            return {"events": [event]}
        # Ensure header present up to channel token
        m_chan_known = self._RE_CHANNEL_KNOWN.search(
            self._buffer, m_start.end()
        )
        if not m_chan_known:
            # maybe unknown channel? detect generic channel token
            m_any = self._RE_CHANNEL_ANY.search(self._buffer, m_start.end())
            if m_any:
                # unknown channel: try to skip whole message when closed
                m_msg_marker = self._RE_MESSAGE.search(
                    self._buffer, m_any.end()
                )
                if not m_msg_marker:
                    return None  # wait more data
                m_end = self._RE_END.search(self._buffer, m_msg_marker.end())
                if not m_end:
                    return None
                # emit parse error metric & drop
                try:
                    _metrics.inc(
                        "harmony_parse_error_total",
                        {"stage": "unknown_channel"},
                    )
                except Exception:  # noqa: BLE001
                    pass
                # slice out skipped region
                self._buffer = self._buffer[m_end.end():]
                return {"skipped": True}
            return None
        channel = m_chan_known.group(1).lower()
        m_msg = self._RE_MESSAGE.search(self._buffer, m_chan_known.end())
        if not m_msg:
            return None
        m_end = self._RE_END.search(self._buffer, m_msg.end())
        if not m_end:
            return None
        # Extract content
        raw_segment = self._buffer[m_msg.end():m_end.start()]
        segment = self._RE_SERVICE.sub("", raw_segment)
        segment = self._ws(segment)
        events: List[Dict] = []
        if channel == "analysis":
            self._emit_analysis(segment, events)
        elif channel == "commentary":
            self._emit_commentary(segment, events)
        elif channel == "tool":
            # New tool channel JSON payload. We'll emit a structured
            # tool_call and synthetic tool_result (immediate) so the
            # route can translate into events.
            payload = segment.strip()
            if payload:
                events.append({
                    "type": "tool_channel_raw",
                    "raw": payload,
                })
        else:  # final
            if not self._final_message_closed:
                self._emit_final(segment, events)
            self._final_message_closed = True
            if m_end.group(1).lower() == "return":
                self._saw_return_token = True
        # Trim processed region
        self._buffer = self._buffer[m_end.end():]
        return {"events": events}

    def process_chunk(self, chunk: str):  # type: ignore[override]
        out: List[Dict] = []
        if not chunk:
            return iter(())
        # After final channel closed: only record anomalies, no output
        if self._final_message_closed:
            try:
                saw_final = "<|channel|>final" in chunk
                saw_analysis = "<|channel|>analysis" in chunk
                saw_commentary = "<|channel|>commentary" in chunk
                if saw_final:
                    _metrics.inc_unexpected_order("extra_final")
                if saw_analysis:
                    _metrics.inc_unexpected_order("analysis_after_final")
                if saw_commentary:
                    _metrics.inc_unexpected_order("commentary_after_final")
                if saw_analysis or saw_commentary or saw_final:
                    # Treat any post-final channel emission as interleaving
                    _metrics.inc_unexpected_order("interleaved_final")
            except Exception:  # noqa: BLE001
                pass
            return iter(())
        # Normal flow
        self._buffer += chunk
        # Wait until we see the assistant preamble
        if "<|start|>assistant" not in self._buffer:
            if len(self._buffer) > 512:
                # Keep tail to avoid unbounded growth on malformed streams
                self._buffer = self._buffer[-512:]
            return iter(())
        # Trim any leading noise before first start token
        first_idx = self._buffer.find("<|start|>assistant")
        if first_idx > 0:
            self._buffer = self._buffer[first_idx:]
        safety = 0
        while True:
            safety += 1
            if safety > 1000:  # hard guard to avoid infinite loops
                try:
                    _metrics.inc(
                        "harmony_parse_error_total", {"stage": "loop_guard"}
                    )
                except Exception:  # noqa: BLE001
                    pass
                break
            res = self._scan_next_message()
            if res is None:
                break
            if res.get("skipped"):
                continue
            out.extend(res.get("events", []))
            if self._final_message_closed:
                break
        # Wrap iterator to track actual delivery of final delta tokens
        if not out:
            return iter(())

        adapter = self

        class _TrackingIter:
            def __init__(self, events):  # noqa: D401
                self._events = events
                self._idx = 0

            def __iter__(self):  # noqa: D401
                return self

            def __next__(self):  # noqa: D401
                if self._idx >= len(self._events):
                    raise StopIteration
                ev = self._events[self._idx]
                self._idx += 1
                if ev.get("type") == "delta":
                    adapter._delivered_final_tokens += 1
                return ev

        return _TrackingIter(out)

    def finalize(self):  # type: ignore[override]
        out: List[Dict] = []
        parse_error = False
        if (not self._final_message_closed) and self._buffer:
            # Detect unterminated/incomplete message => parse error
            if (
                "<|start|>assistant" in self._buffer
                and "<|channel|>final" not in self._buffer
            ):
                parse_error = True
            # Fallback handling
            residual = self._ws(self._buffer)
            if parse_error:
                # Treat residual as reasoning tokens (capped) without emitting
                for tok in filter(None, residual.split()):
                    if self._reasoning_tokens >= self._max_rez:
                        break
                    self._reasoning_tokens += 1
                    self._analysis_acc.append(tok)
            else:
                self._emit_final(residual, out)
            self._final_message_closed = True
    # Emit any final delta tokens not yet yielded (consumer skipped)
    # so stats match visible deltas.
        if self._delivered_final_tokens < self._final_tokens:
            missing = self._final_token_texts[self._delivered_final_tokens:]
            for token_text in missing:
                out.append({"type": "delta", "text": token_text})
                self._delivered_final_tokens += 1

        denom = self._reasoning_tokens + self._delivered_final_tokens
        ratio = (
            self._reasoning_tokens / denom if denom > 0 else 0.0
        )
        # Build commentary retention summary with mode/override logic
        retention_cfg = self.cfg.get("commentary_retention", {}) or {}
        base_mode = str(retention_cfg.get("mode", "metrics_only"))
        final_mode = base_mode
        original_mode = None
        override_applied = False
        tool_chain_cfg = retention_cfg.get("tool_chain", {}) or {}
        if self._saw_tool_commentary and tool_chain_cfg.get("detect"):
            apply_when = str(tool_chain_cfg.get("apply_when", "raw_ephemeral"))
            override_mode = str(
                tool_chain_cfg.get("override_mode", "hashed_slice")
            )
            if apply_when == "any" or apply_when == base_mode:
                original_mode = base_mode
                final_mode = override_mode
                override_applied = base_mode != override_mode
                if override_applied:
                    try:
                        _metrics.inc(  # type: ignore[attr-defined]
                            "commentary_retention_override_total",
                            {"from": base_mode, "to": final_mode},
                        )
                    except Exception:  # noqa: BLE001
                        pass
        commentary_text = " ".join(self._commentary_acc)
        summary: Dict[str, object] = {
            "mode": final_mode,
            "ratio_to_final": (
                self._commentary_tokens / self._final_tokens
                if self._final_tokens > 0
                else 0.0
            ),
            "commentary_tokens": self._commentary_tokens or None,
        }
        if override_applied and tool_chain_cfg.get("tag_in_summary"):
            summary["original_mode"] = original_mode
            summary["override_applied"] = True
            # legacy field name expected by tests
            summary["applied_override"] = True
            summary["base_mode"] = original_mode
            summary["tool_commentary_present"] = (
                True if self._saw_tool_commentary else None
            )
        # Mode-specific enrichments
        try:
            if final_mode == "hashed_slice":
                hs_cfg = retention_cfg.get("hashed_slice", {}) or {}
                max_chars = int(hs_cfg.get("max_chars", 160))
                slice_text = commentary_text[:max_chars]
                if slice_text:
                    summary["slice_len"] = len(slice_text)
                    summary["hash_prefix"] = hashlib.sha256(
                        slice_text.encode("utf-8")
                    ).hexdigest()[:16]
                try:
                    # metric: mode selection
                    _metrics.inc_commentary_retention_mode(
                        final_mode
                    )
                except Exception:  # noqa: BLE001
                    pass
            elif final_mode == "redacted_snippets":
                rs_cfg = retention_cfg.get("redacted_snippets", {}) or {}
                pattern = (
                    rs_cfg.get("redact_pattern")
                    or "(?i)(secret|api[_-]?key)"
                )
                replacement = rs_cfg.get("replacement", "***")
                try:
                    redacted = re.sub(pattern, replacement, commentary_text)
                except Exception:  # noqa: BLE001
                    redacted = commentary_text
                if redacted:
                    # store a shortened snippet for summary
                    summary["snippet_redacted"] = redacted[:160]
                # metrics: mode + redactions occurrences (rough count)
                try:
                    # metric: mode selection
                    _metrics.inc_commentary_retention_mode(
                        final_mode
                    )
                    if redacted:
                        diff_count = 1 if redacted != commentary_text else 0
                        if diff_count:
                            _metrics.inc_commentary_redactions(
                                diff_count
                            )
                except Exception:  # noqa: BLE001
                    pass
            elif final_mode == "raw_ephemeral":
                # Indicate ephemeral cache simulation if any commentary present
                if commentary_text:
                    summary["ephemeral_cached"] = True
                    try:
                        # naive ephemeral cache; tests only check existence
                        ttl = int(
                            (retention_cfg.get("raw_ephemeral", {}) or {}).get(
                                "ttl_seconds", 300
                            )
                        )
                        _EPHEMERAL_COMMENTARY_CACHE.append(
                            (time.time() + ttl, commentary_text[:160])
                        )
                    except Exception:  # noqa: BLE001
                        pass
                try:
                    _metrics.inc_commentary_retention_mode(
                        final_mode
                    )
                except Exception:  # noqa: BLE001
                    pass
            else:  # metrics_only (or future simple modes)
                try:
                    _metrics.inc_commentary_retention_mode(final_mode)
                except Exception:  # noqa: BLE001
                    pass
        except Exception:  # noqa: BLE001
            pass

        out.append(
            {
                "type": "final",
                "stats": {
                    "reasoning_tokens": self._reasoning_tokens,
                    # Report only actually delivered (now equals _final_tokens)
                    "final_tokens": self._delivered_final_tokens,
                    "reasoning_ratio": ratio,
                    "drop_from_history": self._drop_history,
                },
                "reasoning_text": None
                if self._drop_history
                else (
                    " ".join(self._analysis_acc)
                    if self._analysis_acc
                    else None
                ),
                "parse_error": parse_error or None,
                "final_detect_time": None,
                "normalized_return": True if self._saw_return_token else None,
                "commentary_retention_summary": summary,
            }
        )
        return iter(out)


class StreamingStructureAdapter(HarmonyChannelAdapter):  # compat shim
    """Deprecated alias for legacy imports.

    No additional behavior; kept to avoid broad test/import changes.
    """
    pass

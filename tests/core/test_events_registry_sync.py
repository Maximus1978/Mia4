from pathlib import Path

from scripts.generate_events_registry import (
    load_events_module,
    iter_event_classes,
    format_table,
)


def test_generated_events_registry_in_sync():
    mod = load_events_module()
    classes = iter_event_classes(mod)
    generated = format_table(classes).strip().splitlines()
    path = Path("docs/ТЗ/Generated-Events.md")
    # Robust decode: try utf-8 / utf-8-sig / utf-16-le
    raw = path.read_bytes()
    for enc in ("utf-8", "utf-8-sig", "utf-16-le"):
        try:
            current = raw.decode(enc).strip().splitlines()
            break
        except UnicodeDecodeError:
            continue
    else:  # pragma: no cover
        raise AssertionError(
            "Cannot decode Generated-Events.md with known encodings"
        )
    # Ignore first header line and footer line when comparing core rows
    gen_rows = [row for row in generated if row.startswith("| ")]
    cur_rows = [row for row in current if row.startswith("| ")]
    assert gen_rows == cur_rows, "Events registry out of sync. Run generator."

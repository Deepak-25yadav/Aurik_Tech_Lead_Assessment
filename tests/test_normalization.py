import pytest
from datetime import datetime, timezone
from app.services.normalization_service import (
    parse_utc_timestamp,
    normalize_line_id,
    calculate_dedup_hashes,
)

def test_parse_utc_timestamp_epoch_ms():
    # 1776499152000 ms -> 2026-04-18 07:59:12 UTC
    dt = parse_utc_timestamp(1776499152000)
    assert dt.tzinfo is not None
    assert dt.year == 2026
    assert dt.month == 4
    assert dt.day == 18
    assert dt.hour == 7
    assert dt.minute == 59
    assert dt.second == 12

def test_parse_utc_timestamp_iso():
    dt = parse_utc_timestamp("2026-04-18T07:59:12Z")
    assert dt.tzinfo is not None
    assert dt.year == 2026
    assert dt.month == 4
    assert dt.day == 18

def test_parse_utc_timestamp_slash_format():
    dt = parse_utc_timestamp("2026/04/18 08:14:05")
    assert dt.tzinfo is not None
    assert dt.year == 2026
    assert dt.month == 4
    assert dt.hour == 8
    assert dt.minute == 14
    assert dt.second == 5

def test_parse_utc_timestamp_invalid():
    with pytest.raises(ValueError):
        parse_utc_timestamp("bad-ts")

    with pytest.raises(ValueError):
        parse_utc_timestamp("")

    with pytest.raises(ValueError):
        parse_utc_timestamp(None)

def test_normalize_line_id():
    assert normalize_line_id("A") == "LINE-A"
    assert normalize_line_id("LINE-A") == "LINE-A"
    assert normalize_line_id("c") == "LINE-C"
    assert normalize_line_id("Line-E") == "LINE-E"

def test_dedup_hashes_consistency():
    t = datetime(2026, 4, 18, 8, 0, 0, tzinfo=timezone.utc)
    h1_exact, h1_sem = calculate_dedup_hashes("PulseForge", "PF-100", "EQ-001", t, 80.5, 9.2)
    h2_exact, h2_sem = calculate_dedup_hashes("PulseForge", "PF-100", "EQ-001", t, 80.5, 9.2)
    
    assert h1_exact == h2_exact
    assert h1_sem == h2_sem
    
    # Slight float difference within rounding produces same semantic hash
    _, h3_sem = calculate_dedup_hashes("ThermexWatch", "TW-999", "EQ-001", t, 80.52, 9.19)
    assert h1_sem == h3_sem

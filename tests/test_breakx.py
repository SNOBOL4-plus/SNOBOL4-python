# -*- coding: utf-8 -*-
# test_breakx.py — tests for the pure-Python BREAKX implementation
#
# Key semantic difference from BREAK:
#   BREAK  yields once (first break-char position) then stops on backtrack.
#   BREAKX yields at EVERY break-char position, stepping one past each break
#          char on backtrack — mirroring CSNOBOL4 L_BRKX / L_BRKXF logic.
# ------------------------------------------------------------------------------
import pytest
import SNOBOL4python._backend_pure as bp
from SNOBOL4python import GLOBALS, BREAK, BREAKX, σ, SEARCH, MATCH

GLOBALS(globals())

# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------

class Frame:
    """Minimal match-state frame, matching _backend_pure's Ϣ[-1] interface."""
    def __init__(self, subject, pos=0):
        self.subject = subject
        self.pos     = pos
        self.depth   = 0
        self.cstack  = []
        self.vstack  = []
        self.istack  = []
        self.itop    = 0

def collect_break(subject, chars, start=0):
    """Drive BREAK(chars).γ() directly and return list of (slice, pos_after)."""
    bp.Ϣ = [Frame(subject, start)]
    results = []
    for sl in bp.BREAK(chars).γ():
        results.append((sl, bp.Ϣ[0].pos))
    return results, bp.Ϣ[0].pos   # also return final pos after exhaustion

def collect_breakx(subject, chars, start=0):
    """Drive BREAKX(chars).γ() directly and return list of (slice, pos_after)."""
    bp.Ϣ = [Frame(subject, start)]
    results = []
    for sl in bp.BREAKX(chars).γ():
        results.append((sl, bp.Ϣ[0].pos))
    return results, bp.Ϣ[0].pos

# ------------------------------------------------------------------------------
# 1. BREAK yields exactly once
# ------------------------------------------------------------------------------

def test_break_yields_once():
    results, _ = collect_break("aXbXcXd", "X")
    assert len(results) == 1

def test_break_yields_correct_first_span():
    results, _ = collect_break("aXbXcXd", "X")
    sl, pos = results[0]
    assert "aXbXcXd"[sl] == "a"
    assert pos == 1   # cursor left at the X

def test_break_restores_pos_on_exhaustion():
    _, final_pos = collect_break("aXbXcXd", "X")
    assert final_pos == 0   # restored to entry pos

def test_break_fails_when_no_break_char():
    results, final_pos = collect_break("abcdef", "X")
    assert results == []
    # BREAK scans to end without finding a break char and doesn't restore pos
    # (it only restores after a yield, which never happens here)
    assert final_pos == 6

# ------------------------------------------------------------------------------
# 2. BREAKX yields at every break-char position
# ------------------------------------------------------------------------------

def test_breakx_yields_multiple():
    results, _ = collect_breakx("aXbXcXd", "X")
    assert len(results) == 3   # three X's → three yield points

def test_breakx_yields_correct_spans():
    subject = "aXbXcXd"
    results, _ = collect_breakx(subject, "X")
    texts = [subject[sl] for sl, _ in results]
    assert texts == ["a", "b", "c"]

def test_breakx_cursor_at_break_char_after_each_yield():
    subject = "aXbXcXd"
    results, _ = collect_breakx(subject, "X")
    # After each yield the cursor should sit on the X that was the break char
    expected_positions = [1, 3, 5]
    for (sl, pos), expected in zip(results, expected_positions):
        assert pos == expected

def test_breakx_restores_pos_on_exhaustion():
    _, final_pos = collect_breakx("aXbXcXd", "X")
    assert final_pos == 0   # restored to entry pos

def test_breakx_fails_when_no_break_char():
    results, final_pos = collect_breakx("abcdef", "X")
    assert results == []
    assert final_pos == 0

# ------------------------------------------------------------------------------
# 3. BREAK vs BREAKX — explicit contrast
# ------------------------------------------------------------------------------

def test_break_vs_breakx_yield_count():
    subject = "one,two,three,four"
    break_results, _  = collect_break(subject, ",")
    breakx_results, _ = collect_breakx(subject, ",")
    assert len(break_results)  == 1   # BREAK: first comma only
    assert len(breakx_results) == 3   # BREAKX: all three commas

def test_break_vs_breakx_spans():
    subject = "one,two,three,four"
    break_results, _  = collect_break(subject, ",")
    breakx_results, _ = collect_breakx(subject, ",")
    assert subject[break_results[0][0]]  == "one"
    assert [subject[sl] for sl, _ in breakx_results] == ["one", "two", "three"]

# ------------------------------------------------------------------------------
# 4. Edge cases
# ------------------------------------------------------------------------------

def test_breakx_break_char_at_start():
    # break char is at position 0 — first yield should be empty string
    subject = "XaXb"
    results, _ = collect_breakx(subject, "X")
    texts = [subject[sl] for sl, _ in results]
    assert texts == ["", "a"]

def test_breakx_adjacent_break_chars():
    # two break chars in a row: "aXXb"
    subject = "aXXb"
    results, _ = collect_breakx(subject, "X")
    texts = [subject[sl] for sl, _ in results]
    assert texts == ["a", ""]   # second yield is empty (between the two X's)

def test_breakx_break_char_at_end():
    # break char is the last character — yield everything before it, then stop
    subject = "abcX"
    results, _ = collect_breakx(subject, "X")
    texts = [subject[sl] for sl, _ in results]
    assert texts == ["abc"]

def test_breakx_multiple_chars_in_break_set():
    subject = "aXbYcZd"
    results, _ = collect_breakx(subject, "XYZ")
    texts = [subject[sl] for sl, _ in results]
    assert texts == ["a", "b", "c"]

def test_breakx_empty_subject():
    results, final_pos = collect_breakx("", "X")
    assert results == []
    assert final_pos == 0

def test_breakx_non_zero_start_pos():
    # start mid-string; should only see break chars from that point on
    subject = "aXbXcXd"
    results, _ = collect_breakx(subject, "X", start=2)  # start after first X
    texts = [subject[sl] for sl, _ in results]
    assert texts == ["b", "c"]

# ------------------------------------------------------------------------------
# 5. Integration — BREAKX inside a real pattern match
# ------------------------------------------------------------------------------

def test_breakx_in_search_finds_all_tokens():
    """BREAKX('S') + σ('STRING') matches everywhere an S precedes STRING."""
    GLOBALS(globals())
    subject = "xSTRINGySTRINGzSTRING"
    pat = BREAKX('S') % "prefix" + σ('STRING')
    matches = []
    pos = 0
    while True:
        sl = SEARCH(subject[pos:], pat)
        if sl is None:
            break
        matches.append(prefix)
        pos += sl.stop   # advance past the matched STRING
    assert matches == ["x", "y", "z"]

def test_breakx_csv_tokeniser():
    """Classic BREAKX use-case: split CSV by scanning for each comma."""
    GLOBALS(globals())
    subject = "alpha,beta,gamma,delta"
    tokens = []
    pat = BREAKX(',') % "tok" + σ(',')
    pos = 0
    while True:
        sl = SEARCH(subject[pos:], pat)
        if sl is None:
            break
        tokens.append(tok)
        pos += sl.stop   # sl.stop is already past the comma
    tokens.append(subject[pos:])   # final token after last comma
    assert tokens == ["alpha", "beta", "gamma", "delta"]

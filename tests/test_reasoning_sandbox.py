"""
tests/test_reasoning_sandbox.py — Tests for sandbox security and execution.
"""

from financial_text_to_pandas.reasoning.sandbox import run_pandas_sandbox, SecurityViolation
import pandas as pd
import pytest

def test_run_pandas_sandbox_success():
    dfs = {
        "T1": pd.DataFrame({"A": [1, 2], "B": [3, 4]})
    }
    code = """
df = dfs['T1']
total = df['A'].sum()
result = float(total)
"""
    val = run_pandas_sandbox(code, dfs)
    assert val == 3.0

def test_run_pandas_sandbox_blocks_import():
    code = """
import os
result = 1.0
"""
    with pytest.raises(SecurityViolation, match="Imports are not allowed"):
        run_pandas_sandbox(code, {})

def test_run_pandas_sandbox_blocks_exec():
    code = """
exec("print('hello')")
result = 1.0
"""
    with pytest.raises(SecurityViolation, match="Function 'exec' is not allowed"):
        run_pandas_sandbox(code, {})

def test_run_pandas_sandbox_blocks_dunder():
    code = """
cls = result.__class__
result = 1.0
"""
    with pytest.raises(SecurityViolation, match="Dunder access '__class__' is not allowed"):
        run_pandas_sandbox(code, {})

def test_run_pandas_sandbox_requires_result():
    code = "x = 1"
    with pytest.raises(ValueError, match="did not assign a value to 'result'"):
        run_pandas_sandbox(code, {})

def test_run_pandas_sandbox_symbol_map():
    symbol_map = {"NUM_0": 100.0, "NUM_1": 150.0}
    code = "result = NUM_1 - NUM_0"
    val = run_pandas_sandbox(code, {}, symbol_map=symbol_map)
    assert val == 50.0


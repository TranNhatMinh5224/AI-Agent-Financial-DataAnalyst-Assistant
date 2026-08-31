"""
sandbox.py — Safely execute Pandas code with AST restrictions.

Phase 3, Step 8.
"""

from __future__ import annotations

import ast
from typing import Dict, Any, Optional

import pandas as pd

from financial_text_to_pandas.reasoning.tools import parse_vn_number, normalize_unit, safe_get_cell


class SecurityViolation(Exception):
    pass


class SecureASTVisitor(ast.NodeVisitor):
    """AST Visitor to enforce security rules on generated code."""
    
    def visit_Import(self, node):
        raise SecurityViolation("Imports are not allowed in the sandbox.")
        
    def visit_ImportFrom(self, node):
        raise SecurityViolation("Imports are not allowed in the sandbox.")
        
    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            forbidden = {"open", "exec", "eval", "compile", "__import__"}
            if func_name in forbidden:
                raise SecurityViolation(f"Function '{func_name}' is not allowed.")
        self.generic_visit(node)
        
    def visit_Attribute(self, node):
        if node.attr.startswith("__"):
            raise SecurityViolation(f"Dunder access '{node.attr}' is not allowed.")
        self.generic_visit(node)


def clean_code_string(code: str) -> str:
    """Strip markdown code fence blocks if present."""
    code = code.strip()
    if code.startswith("```python"):
        code = code[9:]
    elif code.startswith("```"):
        code = code[3:]
    if code.endswith("```"):
        code = code[:-3]
    return code.strip()


def safe_div(a: float, b: float, default: float = 0.0) -> float:
    """Safe division function to avoid ZeroDivisionError in generated code."""
    try:
        if b == 0 or pd.isna(b):
            return default
        return a / b
    except Exception:
        return default


def run_pandas_sandbox(
    code: str, 
    dfs: Dict[str, pd.DataFrame],
    symbol_map: Optional[Dict[str, float]] = None
) -> Any:
    """Run PoT code in a secure sandbox.
    
    Args:
        code: Python source code.
        dfs: Dictionary of dataframes.
        symbol_map: Optional mapping of symbol names (e.g. NUM_0) to float values for Symbolic Masking.
        
    Returns:
        The value assigned to 'result' in the code.
    """
    cleaned_code = clean_code_string(code)
    try:
        tree = ast.parse(cleaned_code)
    except SyntaxError as e:
        raise ValueError(f"Syntax error in generated code: {e}")
        
    visitor = SecureASTVisitor()
    visitor.visit(tree)
    
    # Safe globals
    sandbox_globals = {
        "__builtins__": {
            "abs": abs,
            "max": max,
            "min": min,
            "sum": sum,
            "round": round,
            "len": len,
            "float": float,
            "int": int,
            "str": str,
            "bool": bool,
            "list": list,
            "dict": dict,
            "set": set,
            "range": range,
            "enumerate": enumerate,
            "zip": zip,
            "isinstance": isinstance,
            "ValueError": ValueError,
            "TypeError": TypeError,
            "KeyError": KeyError,
            "print": print,
        },
        "pd": pd,
        "dfs": dfs,
        "safe_div": safe_div,
        "parse_vn_number": parse_vn_number,
        "normalize_unit": normalize_unit,
        "safe_get_cell": safe_get_cell,
    }
    
    if symbol_map:
        sandbox_globals.update(symbol_map)
    
    sandbox_locals: Dict[str, Any] = {}
    
    # Compile and execute
    compiled = compile(tree, filename="<sandbox>", mode="exec")
    exec(compiled, sandbox_globals, sandbox_locals)
    
    # Result có thể nằm trong locals (thông thường) hoặc globals (edge case với closures)
    result_val = sandbox_locals.get("result", sandbox_globals.get("result", _MISSING))
    if result_val is _MISSING:
        raise ValueError("Generated code did not assign a value to 'result'.")
        
    return result_val


# Sentinel để phân biệt "result = None" với "result không tồn tại"
class _MissingType:
    pass

_MISSING = _MissingType()

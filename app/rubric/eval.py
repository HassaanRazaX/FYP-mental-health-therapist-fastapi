from __future__ import annotations
from typing import Any, Dict, List
import ast

def count_true(items: List[Any]) -> int:
    return sum(1 for x in items if x is True)

ALLOWED_FUNCS = {"count_true": count_true}

class SafeEval(ast.NodeVisitor):
    def __init__(self, names: Dict[str, Any]):
        self.names = names

    def visit(self, node):
        if isinstance(node, ast.Expression):
            return self.visit(node.body)
        if isinstance(node, ast.BoolOp):
            vals = [self.visit(v) for v in node.values]
            if isinstance(node.op, ast.And):
                return all(vals)
            if isinstance(node.op, ast.Or):
                return any(vals)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not self.visit(node.operand)
        if isinstance(node, ast.Compare):
            left = self.visit(node.left)
            ok = True
            for op, comp in zip(node.ops, node.comparators):
                right = self.visit(comp)
                if isinstance(op, ast.Eq):
                    ok = ok and (left == right)
                elif isinstance(op, ast.NotEq):
                    ok = ok and (left != right)
                elif isinstance(op, ast.Gt):
                    ok = ok and (left > right)
                elif isinstance(op, ast.GtE):
                    ok = ok and (left >= right)
                elif isinstance(op, ast.Lt):
                    ok = ok and (left < right)
                elif isinstance(op, ast.LtE):
                    ok = ok and (left <= right)
                else:
                    raise ValueError("Unsupported comparator")
                left = right
            return ok
        if isinstance(node, ast.Name):
            return self.names.get(node.id, None)
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.List):
            return [self.visit(elt) for elt in node.elts]
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ValueError("Unsupported call")
            fn = node.func.id
            if fn not in ALLOWED_FUNCS:
                raise ValueError("Function not allowed")
            args = [self.visit(a) for a in node.args]
            return ALLOWED_FUNCS[fn](*args)
        raise ValueError(f"Unsupported expression: {type(node).__name__}")

def safe_eval(expr: str, names: Dict[str, Any]) -> bool:
    tree = ast.parse(expr, mode="eval")
    return bool(SafeEval(names).visit(tree))

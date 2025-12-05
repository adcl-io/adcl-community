# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Safe Condition Evaluator

Provides AST-based safe evaluation of boolean conditions for workflow engine.
Prevents arbitrary code execution while allowing logical expressions.
"""

import ast
import operator
from typing import Dict, Any


# Allowed operators for safe evaluation
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.And: operator.and_,
    ast.Or: operator.or_,
    ast.Not: operator.not_,
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
    ast.In: lambda x, y: x in y,
    ast.NotIn: lambda x, y: x not in y,
    ast.Is: operator.is_,
    ast.IsNot: operator.is_not,
}


# Allowed functions for safe evaluation
SAFE_FUNCTIONS = {
    'len': len,
    'str': str,
    'int': int,
    'float': float,
    'bool': bool,
    'abs': abs,
    'min': min,
    'max': max,
}


class SafeEvaluator(ast.NodeVisitor):
    """
    AST-based safe evaluator for boolean expressions.

    Restricts evaluation to:
    - Basic arithmetic and comparison operators
    - Logical operators (and, or, not)
    - Safe built-in functions (len, str, int, etc.)
    - Variable references from provided context
    """

    def __init__(self, variables: Dict[str, Any]):
        self.variables = variables

    def visit_Expression(self, node):
        return self.visit(node.body)

    def visit_Constant(self, node):
        # Python 3.8+ uses Constant instead of Num, Str, etc.
        return node.value

    def visit_Name(self, node):
        # Variable reference
        if node.id in self.variables:
            return self.variables[node.id]
        elif node.id in SAFE_FUNCTIONS:
            return SAFE_FUNCTIONS[node.id]
        else:
            raise ValueError(f"Undefined variable: {node.id}")

    def visit_BinOp(self, node):
        # Binary operation (e.g., a + b, x > y)
        left = self.visit(node.left)
        right = self.visit(node.right)
        op_type = type(node.op)

        if op_type not in SAFE_OPERATORS:
            raise ValueError(f"Operator not allowed: {op_type.__name__}")

        return SAFE_OPERATORS[op_type](left, right)

    def visit_UnaryOp(self, node):
        # Unary operation (e.g., not x, -y)
        operand = self.visit(node.operand)
        op_type = type(node.op)

        if op_type not in SAFE_OPERATORS:
            raise ValueError(f"Operator not allowed: {op_type.__name__}")

        return SAFE_OPERATORS[op_type](operand)

    def visit_Compare(self, node):
        # Comparison (e.g., x > 5, a == b)
        left = self.visit(node.left)

        for op, comparator in zip(node.ops, node.comparators):
            right = self.visit(comparator)
            op_type = type(op)

            if op_type not in SAFE_OPERATORS:
                raise ValueError(f"Operator not allowed: {op_type.__name__}")

            result = SAFE_OPERATORS[op_type](left, right)

            if not result:
                return False

            left = right

        return True

    def visit_BoolOp(self, node):
        # Boolean operation (and, or)
        op_type = type(node.op)

        if op_type not in SAFE_OPERATORS:
            raise ValueError(f"Operator not allowed: {op_type.__name__}")

        values = [self.visit(value) for value in node.values]

        if isinstance(node.op, ast.And):
            return all(values)
        elif isinstance(node.op, ast.Or):
            return any(values)
        else:
            raise ValueError(f"Boolean operator not allowed: {op_type.__name__}")

    def visit_Call(self, node):
        # Function call
        func = self.visit(node.func)

        if func not in SAFE_FUNCTIONS.values():
            raise ValueError(f"Function not allowed: {getattr(node.func, 'id', 'unknown')}")

        args = [self.visit(arg) for arg in node.args]
        kwargs = {kw.arg: self.visit(kw.value) for kw in node.keywords}

        return func(*args, **kwargs)

    def generic_visit(self, node):
        raise ValueError(f"AST node type not allowed: {type(node).__name__}")


def evaluate_condition(condition: str, variables: Dict[str, Any]) -> bool:
    """
    Safely evaluate a boolean condition string.

    Args:
        condition: Python expression string (e.g., "var_0 > 5 and var_1")
        variables: Variable context mapping names to values

    Returns:
        Boolean result of evaluation

    Raises:
        ValueError: If condition is invalid or uses unsafe operations
        SyntaxError: If condition has syntax errors

    Examples:
        >>> evaluate_condition("var_0 > 5", {"var_0": 10})
        True
        >>> evaluate_condition("var_0 and len(var_1) > 0", {"var_0": True, "var_1": [1,2,3]})
        True
    """
    try:
        # Parse condition as Python expression
        tree = ast.parse(condition, mode='eval')

        # Evaluate using safe visitor
        evaluator = SafeEvaluator(variables)
        result = evaluator.visit(tree)

        # Ensure result is boolean
        return bool(result)

    except SyntaxError as e:
        raise SyntaxError(f"Invalid condition syntax: {e}")
    except Exception as e:
        raise ValueError(f"Condition evaluation failed: {e}")

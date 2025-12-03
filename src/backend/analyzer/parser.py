# Author: Bradley R. Kinnard — parse first, ask questions later

"""
Python AST parser. Extracts structure before any LLM touches the code.
If it won't parse, we don't waste tokens on it.
"""

import ast
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class ParseError:
    """When code won't parse at all."""
    line: int
    column: int
    message: str


@dataclass
class ImportNode:
    module: str
    names: list[str]  # ["foo", "bar"] or ["*"]
    line: int
    is_from: bool


@dataclass
class FunctionNode:
    name: str
    line: int
    end_line: int
    args: list[str]
    is_async: bool
    decorators: list[str]


@dataclass
class ClassNode:
    name: str
    line: int
    end_line: int
    bases: list[str]
    methods: list[str]


@dataclass
class AssignmentNode:
    targets: list[str]
    line: int
    is_augmented: bool  # +=, -=, etc.
    value_type: str  # "call", "literal", "name", "binop", etc.


@dataclass
class ControlFlowNode:
    kind: Literal["if", "for", "while", "try", "with"]
    line: int
    end_line: int
    is_unreachable: bool  # if False:, if 0:, while False:


@dataclass
class Finding:
    """Pre-LLM structural issue detected by parser alone."""
    kind: str
    message: str
    line: int
    severity: int  # 1-5


@dataclass
class ParseResult:
    """Successful parse. All the structure agents need."""
    imports: list[ImportNode] = field(default_factory=list)
    functions: list[FunctionNode] = field(default_factory=list)
    classes: list[ClassNode] = field(default_factory=list)
    assignments: list[AssignmentNode] = field(default_factory=list)
    control_flow: list[ControlFlowNode] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    lines: int = 0


def _is_always_false(node: ast.expr) -> bool:
    """Check if condition is statically False/0/None/''."""
    if isinstance(node, ast.Constant):
        return not node.value  # False, 0, None, '', []
    if isinstance(node, ast.NameConstant):  # py3.7 compat
        return not node.value
    return False


def _get_name(node: ast.expr) -> str:
    """Extract name from various AST node types."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_get_name(node.value)}.{node.attr}"
    if isinstance(node, ast.Subscript):
        return f"{_get_name(node.value)}[...]"
    if isinstance(node, ast.Starred):
        return f"*{_get_name(node.value)}"
    if isinstance(node, (ast.Tuple, ast.List)):
        return f"({', '.join(_get_name(e) for e in node.elts)})"
    return "?"


def _value_type(node: ast.expr) -> str:
    """Classify the RHS of an assignment."""
    if isinstance(node, ast.Call):
        return "call"
    if isinstance(node, ast.Constant):
        return "literal"
    if isinstance(node, ast.Name):
        return "name"
    if isinstance(node, ast.BinOp):
        return "binop"
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return "collection"
    if isinstance(node, ast.Dict):
        return "dict"
    if isinstance(node, ast.Lambda):
        return "lambda"
    if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
        return "comprehension"
    if isinstance(node, ast.Await):
        return "await"
    return "other"


def parse_python(code: str) -> ParseResult | ParseError:
    """
    Parse Python code, extract structure, flag obvious issues.
    Returns ParseError if code is syntactically broken.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return ParseError(
            line=e.lineno or 1,
            column=e.offset or 0,
            message=str(e.msg) if e.msg else "Syntax error"
        )

    result = ParseResult(lines=code.count('\n') + 1)
    seen_names: dict[str, int] = {}  # name -> first definition line

    for node in ast.walk(tree):
        # imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                result.imports.append(ImportNode(
                    module=alias.name,
                    names=[alias.asname or alias.name],
                    line=node.lineno,
                    is_from=False
                ))

        elif isinstance(node, ast.ImportFrom):
            result.imports.append(ImportNode(
                module=node.module or "",
                names=[a.name for a in node.names],
                line=node.lineno,
                is_from=True
            ))

        # functions
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func = FunctionNode(
                name=node.name,
                line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                args=[a.arg for a in node.args.args],
                is_async=isinstance(node, ast.AsyncFunctionDef),
                decorators=[_get_name(d) for d in node.decorator_list]
            )
            result.functions.append(func)

            # duplicate check
            if node.name in seen_names:
                result.findings.append(Finding(
                    kind="duplicate-definition",
                    message=f"Function `{node.name}` redefined (first on line {seen_names[node.name]})",
                    line=node.lineno,
                    severity=4
                ))
            else:
                seen_names[node.name] = node.lineno

        # classes
        elif isinstance(node, ast.ClassDef):
            methods = [n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            result.classes.append(ClassNode(
                name=node.name,
                line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                bases=[_get_name(b) for b in node.bases],
                methods=methods
            ))

            if node.name in seen_names:
                result.findings.append(Finding(
                    kind="duplicate-definition",
                    message=f"Class `{node.name}` redefined (first on line {seen_names[node.name]})",
                    line=node.lineno,
                    severity=4
                ))
            else:
                seen_names[node.name] = node.lineno

        # assignments
        elif isinstance(node, ast.Assign):
            result.assignments.append(AssignmentNode(
                targets=[_get_name(t) for t in node.targets],
                line=node.lineno,
                is_augmented=False,
                value_type=_value_type(node.value)
            ))

        elif isinstance(node, ast.AugAssign):
            result.assignments.append(AssignmentNode(
                targets=[_get_name(node.target)],
                line=node.lineno,
                is_augmented=True,
                value_type=_value_type(node.value)
            ))

        # control flow
        elif isinstance(node, ast.If):
            unreachable = _is_always_false(node.test)
            result.control_flow.append(ControlFlowNode(
                kind="if",
                line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                is_unreachable=unreachable
            ))
            if unreachable:
                result.findings.append(Finding(
                    kind="unreachable-code",
                    message="if block is always False (dead code)",
                    line=node.lineno,
                    severity=3
                ))

        elif isinstance(node, ast.While):
            unreachable = _is_always_false(node.test)
            result.control_flow.append(ControlFlowNode(
                kind="while",
                line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                is_unreachable=unreachable
            ))
            if unreachable:
                result.findings.append(Finding(
                    kind="unreachable-code",
                    message="while block is always False (never executes)",
                    line=node.lineno,
                    severity=3
                ))

        elif isinstance(node, ast.For):
            result.control_flow.append(ControlFlowNode(
                kind="for",
                line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                is_unreachable=False
            ))

        elif isinstance(node, ast.Try):
            result.control_flow.append(ControlFlowNode(
                kind="try",
                line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                is_unreachable=False
            ))

        elif isinstance(node, ast.With):
            result.control_flow.append(ControlFlowNode(
                kind="with",
                line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                is_unreachable=False
            ))

    return result


def is_parseable(code: str) -> bool:
    """Quick check if code parses. Use before wasting LLM tokens."""
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False

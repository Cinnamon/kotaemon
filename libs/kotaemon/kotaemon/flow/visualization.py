from __future__ import annotations

import ast
import inspect
from collections import defaultdict

IGNORE = (
    ast.Call,
    ast.arguments,
    ast.arg,
    ast.Assign,
    ast.Name,
    ast.Attribute,
    ast.Load,
    ast.keyword,
    ast.Constant,
    ast.Return,
    ast.Dict,
    ast.Subscript,
    ast.JoinedStr,
    ast.If,
    ast.IfExp,
)


def trace_pipelne_run(cls) -> list:
    """Trace the logic flow of a pipeline run

    Args:
        cls: the pipeline class

    Returns:
        list: the logic flow of the pipeline run (suitable for dot)
    """
    tree = ast.parse(inspect.getsource(cls))
    analyzer = PipelineRunTracer()
    analyzer.visit(tree)

    return analyzer.logic_flow


def get_ast_node_name(node) -> str:
    """Get human-readable name of an ast node

    Args:
        node: ast node

    Returns:
        str: human-readable name of the ast node
    """
    if isinstance(node, ast.Attribute):
        return f"{get_ast_node_name(node.value)}.{node.attr}"
    elif isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.FunctionDef):
        return node.name
    elif isinstance(node, ast.arg):
        return node.arg
    elif isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.Call):
        return get_ast_node_name(node.func)
    elif isinstance(node, ast.JoinedStr):
        text = ""
        for value in node.values:
            text += get_ast_node_name(value)
        return text
    elif isinstance(node, ast.FormattedValue):
        return get_ast_node_name(node.value)
    else:
        return node


class PipelineRunTracer(ast.NodeVisitor):
    def __init__(self):
        self.logic_flow = []
        self.in_run = False
        self._stacks: list[dict[str, list]] = [defaultdict(list)]
        self._last_call = None

    def get_creator_of(self, name, default=None):
        """Find the creator of a variable"""
        for idx in range(len(self._stacks) - 1, -1, -1):
            if name in self._stacks[idx]:
                return self._stacks[idx][name]

        return default

    def set_creator_of(self, name, value):
        """Set creator of a value"""
        self._stacks[-1][name] = value

    def stack_begin(self):
        stack: dict[str, list] = defaultdict(list)
        self._stacks.append(stack)
        return stack

    def stack_end(self):
        return self._stacks.pop()

    def visit(self, node):
        if self.in_run:
            if not isinstance(node, IGNORE):
                print(node)
        return super().visit(node)

    def visit_Assign(self, node):
        print(f"{self.indent()}Assign:")

        # TODO: seems Assign doesn't need stack
        self.generic_visit(node)
        for target in node.targets:
            name = get_ast_node_name(target)
            if self._last_call is not None:
                self.set_creator_of(name, self._last_call)
                self._last_call = None

    def visit_Name(self, node):
        print(f"{self.indent()}Name: {get_ast_node_name(node)}")

    def indent(self):
        return " " * len(self._stacks)

    def visit_FunctionDef(self, node):
        if node.name != "run":
            return

        self.in_run = True
        print(f"{self.indent()}Function: {get_ast_node_name(node)}")

        return self.generic_visit(node)

    def visit_Call(self, node):
        if not self.in_run:
            return

        # determine function name
        node_name = get_ast_node_name(node)
        for kw in node.keywords:
            if kw.arg == "_ff_name":
                node_name = get_ast_node_name(kw.value)
                break

        print(f"{self.indent()}Call: {node_name}")

        # determine args relation
        for arg in node.args:
            if isinstance(arg, ast.Call):
                self.visit(arg)
                self.logic_flow.append((self._last_call, node_name))
                self._last_call = None
            elif isinstance(arg, ast.Name):
                from_node = self.get_creator_of(arg.id, "__begin__")
                if isinstance(from_node, str):
                    self.logic_flow.append((from_node, node_name))
                else:
                    for each in from_node:
                        self.logic_flow.append((each, node_name))
            else:
                print("Else condition")

        # determine kwargs relation
        for kw in node.keywords:
            if kw.arg == "_ff_name":
                continue
            if isinstance(arg, ast.Call):
                self.visit(arg)
                self.logic_flow.append((self._last_call, node_name))
                self._last_call = None
            elif isinstance(kw.value, ast.Name):
                from_node = self.get_creator_of(kw.value.id, "__begin__")
                if isinstance(from_node, str):
                    self.logic_flow.append((from_node, node_name))
                else:
                    for each in from_node:
                        self.logic_flow.append((each, node_name))
            else:
                print("Else condition")
        self._last_call = node_name

    def visit_Attribute(self, node):
        print(f"{self.indent()}Attribute: {get_ast_node_name(node)}")
        # return self.generic_visit(node)

    def visit_arg(self, node):
        print(f"{self.indent()}Arg: {get_ast_node_name(node)}")

    def visit_arguments(self, node):
        print(f"{self.indent()}Arguments:")
        self.generic_visit(node)

    def visit_keyword(self, node):
        print(f"{self.indent()}Keyword: {get_ast_node_name(node)}")
        self.generic_visit(node)

    def visit_Load(self, node):
        print(f"{self.indent()}Load: {get_ast_node_name(node)}")
        return self.generic_visit(node)

    def visit_Constant(self, node):
        print(f"{self.indent()}Constant: {get_ast_node_name(node)}")
        return self.generic_visit(node)

    def visit_Return(self, node):
        print(f"{self.indent()}Return: {get_ast_node_name(node)}")
        self.generic_visit(node)

    def visit_Dict(self, node):
        print(f"{self.indent()}Dict: {get_ast_node_name(node)}")
        self.generic_visit(node)

    def visit_Subscript(self, node):
        print(f"{self.indent()}Subscript: {get_ast_node_name(node)}")
        self.generic_visit(node)

    def visit_If(self, node):
        self.generic_visit(node.test)
        self.stack_begin()
        for each in node.body:
            self.visit(each)
        creator1 = self.stack_end()

        self.stack_begin()
        for each in node.orelse:
            self.visit(each)
        creator2 = self.stack_end()

        creator = {}
        creator.update(creator1)
        for key, value in creator2.items():
            if key in creator:
                value1 = [value] if not isinstance(value, list) else value
                value2 = (
                    [creator[key]]
                    if not isinstance(creator[key], list)
                    else creator[key]
                )
                creator[key] = value1 + value2
            else:
                creator[key] = value
        self._stacks[-1].update(creator)

    def report(self):
        for each_from, each_to in self.logic_flow:
            print(f"{each_from} -> {each_to}")

    def visit_IfExp(self, node):
        print(f"{self.indent()}IfExp: {get_ast_node_name(node)}")

        self.visit(node.test)
        test = self._last_call

        last_call = []
        self.visit(node.body)
        if self._last_call is not None:
            if test is not None:
                self.logic_flow.append((test, self._last_call))
            last_call.append(self._last_call)
            self._last_call = None

        self.visit(node.orelse)
        if self._last_call is not None:
            if test is not None:
                self.logic_flow.append((test, self._last_call))
            last_call.append(self._last_call)
            self._last_call = None

        if last_call:
            self._last_call = last_call

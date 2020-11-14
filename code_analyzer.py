import argparse
import ast
import re
import os

from collections import defaultdict


class PepAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.stats: dict[str, dict[int, list]] = {
            "variables": defaultdict(list),
            "parameters": defaultdict(list),
            "is_constant_default": defaultdict(list),
        }

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Store):
            self.stats["variables"][node.lineno].append(node.id)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        for a in node.args.args:
            self.stats["parameters"][node.lineno].append(a.arg)
        for a in node.args.defaults:
            self.stats["is_constant_default"][node.lineno].append(isinstance(a, ast.Constant))
        self.generic_visit(node)

    def get_parameters(self, lineno: int) -> list:
        return self.stats["parameters"][lineno]

    def get_variables(self, lineno: int) -> list:
        return self.stats["variables"][lineno]

    def get_mutable_defaults(self, lineno: int) -> str:
        for param_name, is_default in zip(self.stats["parameters"][lineno], self.stats["is_constant_default"][lineno]):
            if not is_default:
                return param_name
        return ""


def input_path() -> str:
    parser = argparse.ArgumentParser(usage="Static Code Analyzer")
    parser.add_argument("files", help="takes a single file or folder path")
    args = parser.parse_args()
    return args.files


def analyze_pathname(pathname: str):
    if os.path.isfile(pathname):
        return analyze_file(pathname)

    if os.path.isdir(pathname):
        scripts: list = os.listdir(pathname)
        for script in scripts:
            script_path: str = os.path.join(pathname, script)
            analyze_file(script_path)


def analyze_file(filename: str):
    preceding_blank_line_counter: int = 0

    with open(filename) as f:
        tree = ast.parse(f.read())

        pep_analyzer = PepAnalyzer()
        pep_analyzer.visit(tree)

        f.seek(0)
        for i, line in enumerate(f, start=1):
            if line == "\n":
                preceding_blank_line_counter += 1
                continue

            error_source: str = f"{filename}: Line {i}:"

            if len(line) > 79:
                print(error_source, "S001 Too long")

            if re.match(r"(?!^( {4})*[^ ])", line):
                print(error_source, "S002 Indentation is not a multiple of four")

            if re.search(r"^([^#])*;(?!\S)", line):
                print(error_source, "S003 Unnecessary semicolon")

            if re.match(r"[^#]*[^ ]( ?#)", line):
                print(error_source, "S004 At least two spaces before inline comment required")

            if re.search(r"(?i)# *todo", line):
                print(error_source, "S005 TODO found")

            if preceding_blank_line_counter > 2:
                print(error_source, "S006 More than two blank lines used before this line")
            preceding_blank_line_counter = 0

            if re.match(r"^([ ]*(?:class|def) ( )+)", line):
                print(error_source, "S007 Too many spaces after construction_name (def or class)")

            if matches := re.match(r"^(?:[ ]*class (?P<name>\w+))", line):
                if not re.match(r"(?:[A-Z][a-z0-9]+)+", matches["name"]):
                    print(error_source, f'S008 Class name {matches["name"]} should use CamelCase')

            if matches := re.match(r"^(?:[ ]*def (?P<name>\w+))", line):
                if not re.match(r"[a-z_]+", matches["name"]):
                    print(error_source, f'S009 Function name {matches["name"]} should use snake_case')

            for parameter in pep_analyzer.get_parameters(i):
                if not re.match(r"[a-z_]+", parameter):
                    print(error_source, f"S010 Argument name '{parameter}' should be snake_case")
                    break

            for variable in pep_analyzer.get_variables(i):
                if not re.match(r"[a-z_]+", variable):
                    print(error_source, f"S011 Variable '{variable}' in function should be snake_case")
                    break

            if pep_analyzer.get_mutable_defaults(i):
                print(error_source, "S012 Default argument value is mutable")


def main():
    analyze_pathname(input_path())


if __name__ == "__main__":
    main()

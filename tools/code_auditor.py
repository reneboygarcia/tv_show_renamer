import os
import ast
import sys
from collections import defaultdict
from typing import Dict, List, Set, Tuple

class CodeAuditor:
    def __init__(self, project_root: str):
        self.project_root = project_root
        self.class_definitions: Dict[str, List[str]] = defaultdict(list)
        self.function_definitions: Dict[str, List[str]] = defaultdict(list)
        self.imports: Dict[str, Set[str]] = defaultdict(set)
        self.similar_names: Dict[str, List[str]] = defaultdict(list)

    def scan_project(self):
        """Recursively scan Python files in the project."""
        for root, _, files in os.walk(self.project_root):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    self._analyze_file(file_path)

    def _analyze_file(self, file_path: str):
        """Analyze a single Python file for definitions and imports."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read(), filename=file_path)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    self.class_definitions[node.name].append(file_path)
                elif isinstance(node, ast.FunctionDef):
                    self.function_definitions[node.name].append(file_path)
                elif isinstance(node, ast.Import):
                    for name in node.names:
                        self.imports[file_path].add(name.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        self.imports[file_path].add(node.module)

        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")

    def find_duplicates(self) -> Tuple[Dict, Dict]:
        """Find duplicate class and function definitions."""
        duplicate_classes = {name: paths for name, paths in self.class_definitions.items() 
                           if len(paths) > 1}
        duplicate_functions = {name: paths for name, paths in self.function_definitions.items() 
                             if len(paths) > 1}
        return duplicate_classes, duplicate_functions

    def find_similar_names(self, threshold: float = 0.85) -> Dict[str, List[str]]:
        """Find similarly named entities that might indicate redundancy."""
        from difflib import SequenceMatcher

        all_names = list(self.class_definitions.keys()) + list(self.function_definitions.keys())
        
        for i, name1 in enumerate(all_names):
            for name2 in all_names[i+1:]:
                similarity = SequenceMatcher(None, name1.lower(), name2.lower()).ratio()
                if similarity >= threshold:
                    self.similar_names[name1].append(name2)

        return self.similar_names

    def generate_report(self):
        """Generate a comprehensive audit report."""
        duplicate_classes, duplicate_functions = self.find_duplicates()
        similar_names = self.find_similar_names()

        report = ["=== Code Redundancy Audit Report ===\n"]

        if duplicate_classes:
            report.append("\nDuplicate Class Definitions:")
            for class_name, files in duplicate_classes.items():
                report.append(f"\n{class_name} defined in:")
                for file_path in files:
                    report.append(f"  - {os.path.relpath(file_path, self.project_root)}")

        if duplicate_functions:
            report.append("\nDuplicate Function Definitions:")
            for func_name, files in duplicate_functions.items():
                report.append(f"\n{func_name} defined in:")
                for file_path in files:
                    report.append(f"  - {os.path.relpath(file_path, self.project_root)}")

        if similar_names:
            report.append("\nPotentially Similar Names:")
            for name1, similar in similar_names.items():
                if similar:
                    report.append(f"\n{name1} similar to:")
                    for name2 in similar:
                        report.append(f"  - {name2}")

        return "\n".join(report)

def main():
    if len(sys.argv) != 2:
        print("Usage: python code_auditor.py <project_root_path>")
        sys.exit(1)

    project_root = sys.argv[1]
    auditor = CodeAuditor(project_root)
    auditor.scan_project()
    report = auditor.generate_report()
    print(report)

if __name__ == "__main__":
    main()
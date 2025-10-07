"""
Utility Function Detection Service

This module implements a multi-signal static analysis system to identify and rank
functions by their importance in a codebase. The goal is to filter out utility
functions and focus on business-critical logic.

Core Concepts:
--------------
1. **Static Analysis**: Analyzing code without executing it
2. **Multi-Signal Scoring**: Combining multiple heuristics for robustness
3. **Cyclomatic Complexity**: Measures code complexity via decision points
4. **Call Graph Analysis**: Understanding function dependencies
5. **AST Pattern Matching**: Detecting code patterns at the syntax tree level
"""

import ast
import json
import re
from typing import Dict, List, Any, Set, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import math


@dataclass
class FunctionMetrics:
    """Stores all computed metrics for a function"""
    name: str
    file_path: str
    
    # Complexity metrics
    cyclomatic_complexity: int = 0
    lines_of_code: int = 0
    num_parameters: int = 0
    
    # Call graph metrics
    fan_in: int = 0  # How many functions call this one
    fan_out: int = 0  # How many functions this one calls
    
    # Pattern-based signals
    is_getter_setter: bool = False
    is_single_return: bool = False
    is_wrapper: bool = False
    has_trivial_name: bool = False
    is_dunder_method: bool = False
    
    # Content analysis
    stdlib_usage_ratio: float = 0.0
    business_keyword_score: float = 0.0
    
    # Final score (0-1, higher = more important)
    importance_score: float = 0.0


class ComplexityAnalyzer:
    """
    Analyzes code complexity using cyclomatic complexity.
    
    Cyclomatic Complexity: Counts the number of independent paths through code.
    Formula: CC = E - N + 2P where E=edges, N=nodes, P=connected components
    
    In practice: Count decision points (if, for, while, and, or, etc.) + 1
    
    Why it matters:
    - Low complexity (1-5): Simple, often utility functions
    - Medium (6-10): Moderate business logic
    - High (11+): Complex business logic
    """
    
    @staticmethod
    def calculate_complexity(node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity of a function"""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            # Each decision point adds to complexity
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, (ast.BoolOp,)):
                # 'and'/'or' create additional paths
                complexity += len(child.values) - 1
            elif isinstance(child, ast.comprehension):
                complexity += 1
                if child.ifs:
                    complexity += len(child.ifs)
        
        return complexity
    
    @staticmethod
    def count_lines_of_code(node: ast.FunctionDef) -> int:
        """Count actual lines of code (excluding empty lines and docstrings)"""
        if not hasattr(node, 'end_lineno') or not hasattr(node, 'lineno'):
            return 0
        
        # Simple line count (in production, we'd parse actual file)
        return node.end_lineno - node.lineno + 1


class PatternDetector:
    """
    Detects common utility function patterns using AST analysis.
    
    AST (Abstract Syntax Tree): A tree representation of code structure.
    We can inspect the tree to find patterns without executing code.
    """
    
    # Utility function name patterns
    TRIVIAL_PATTERNS = [
        r'^get_\w+$', r'^set_\w+$',  # Getters/setters
        r'^is_\w+$', r'^has_\w+$',    # Boolean checkers
        r'^to_\w+$', r'^from_\w+$',   # Converters
        r'^format_\w+$', r'^parse_\w+$',  # Formatters/parsers
        r'^validate_\w+$', r'^check_\w+$',  # Validators
        r'^build_\w+$', r'^create_\w+$',  # Simple builders
        r'^_\w+_helper$', r'^_\w+_util$',  # Explicitly marked helpers
        r'^\w+_to_\w+$',  # Converters
    ]
    
    # Business logic keywords
    BUSINESS_KEYWORDS = {
        'authenticate', 'authorize', 'login', 'register', 'signup',
        'order', 'payment', 'transaction', 'invoice', 'checkout',
        'request', 'response', 'endpoint', 'route', 'handler',
        'process', 'execute', 'perform', 'handle',
        'model', 'schema', 'entity', 'repository',
    }
    
    @classmethod
    def is_trivial_name(cls, func_name: str) -> bool:
        """Check if function name matches utility patterns"""
        return any(re.match(pattern, func_name) for pattern in cls.TRIVIAL_PATTERNS)
    
    @staticmethod
    def is_getter_setter(node: ast.FunctionDef) -> bool:
        """Detect simple getter/setter patterns"""
        body = node.body
        
        # Skip docstring
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Str):
            body = body[1:]
        
        if len(body) != 1:
            return False
        
        stmt = body[0]
        
        # Getter: return self.attr
        if isinstance(stmt, ast.Return):
            if isinstance(stmt.value, ast.Attribute):
                return True
        
        # Setter: self.attr = value
        if isinstance(stmt, ast.Assign):
            if len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Attribute):
                return True
        
        return False
    
    @staticmethod
    def is_single_return(node: ast.FunctionDef) -> bool:
        """Check if function is just a single return statement"""
        body = node.body
        
        # Skip docstring
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, (ast.Str, ast.Constant)):
            body = body[1:]
        
        return len(body) == 1 and isinstance(body[0], ast.Return)
    
    @staticmethod
    def is_wrapper(node: ast.FunctionDef) -> bool:
        """
        Detect wrapper functions (functions that just call another function).
        
        Pattern: def wrapper(*args, **kwargs): return other_func(*args, **kwargs)
        """
        body = node.body
        
        # Skip docstring
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, (ast.Str, ast.Constant)):
            body = body[1:]
        
        if len(body) != 1 or not isinstance(body[0], ast.Return):
            return False
        
        ret_value = body[0].value
        
        # Check if it's calling another function
        if isinstance(ret_value, ast.Call):
            # Simple wrapper pattern
            return True
        
        return False
    
    @classmethod
    def calculate_business_keyword_score(cls, node: ast.FunctionDef, source: str = "") -> float:
        """
        Calculate how much the function relates to business logic based on keywords.
        Returns a score between 0 and 1.
        """
        func_name_lower = node.name.lower()
        
        # Check function name
        score = 0
        for keyword in cls.BUSINESS_KEYWORDS:
            if keyword in func_name_lower:
                score += 1
        
        # Normalize to 0-1 range
        return min(score / 2.0, 1.0)  # Cap at 1.0


class CallGraphAnalyzer:
    """
    Analyzes function call relationships to compute fan-in and fan-out.
    
    Fan-in: Number of functions that call this function
    Fan-out: Number of functions this function calls
    
    High fan-in often indicates utility functions (many callers)
    High fan-out with low complexity might indicate a coordinator/utility
    """
    
    def __init__(self, graph_data: Dict[str, Any]):
        self.graph_data = graph_data
        self.call_graph = defaultdict(set)  # caller -> {callees}
        self.reverse_graph = defaultdict(set)  # callee -> {callers}
        
        self._build_call_graph()
    
    def _build_call_graph(self):
        """Build call graph from the JSON data"""
        for node in self.graph_data.get('nodes', []):
            node_id = node.get('id', '')
            
            for edge in self.graph_data.get('edges', []):
                if edge.get('source') == node_id:
                    target = edge.get('target', '')
                    self.call_graph[node_id].add(target)
                    self.reverse_graph[target].add(node_id)
    
    def get_fan_in(self, node_id: str) -> int:
        """Get number of callers for a function"""
        return len(self.reverse_graph.get(node_id, set()))
    
    def get_fan_out(self, node_id: str) -> int:
        """Get number of callees from a function"""
        return len(self.call_graph.get(node_id, set()))


class ImportAnalyzer:
    """
    Analyzes import usage to detect stdlib-heavy functions.
    
    Functions that primarily use stdlib modules are more likely to be utilities.
    Business logic typically uses domain-specific modules.
    """
    
    STDLIB_MODULES = {
        'os', 'sys', 'json', 're', 'math', 'random', 'datetime', 'time',
        'collections', 'itertools', 'functools', 'operator', 'string',
        'typing', 'copy', 'pickle', 'struct', 'io', 'pathlib',
        'urllib', 'http', 'hashlib', 'uuid', 'logging', 'warnings',
    }
    
    @classmethod
    def calculate_stdlib_ratio(cls, node: ast.FunctionDef, module_imports: Set[str]) -> float:
        """
        Calculate ratio of stdlib usage in a function.
        Returns value between 0 and 1.
        """
        if not module_imports:
            return 0.0
        
        stdlib_count = sum(1 for module in module_imports if module in cls.STDLIB_MODULES)
        return stdlib_count / len(module_imports) if module_imports else 0.0


class UtilityDetectorService:
    """
    Main service that orchestrates all analysis techniques and computes importance scores.
    
    Scoring Strategy:
    -----------------
    We use a weighted combination of signals. Each signal contributes to determining
    if a function is a utility (low score) or business logic (high score).
    
    Weights are tuned to minimize false positives (marking important code as utility).
    """
    
    def __init__(self):
        self.complexity_analyzer = ComplexityAnalyzer()
        self.pattern_detector = PatternDetector()
    
    def analyze_repository(self, json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Main entry point: Analyze repository and return ranked functions.
        
        Args:
            json_data: Repository structure with nodes and edges
        
        Returns:
            List of functions with metrics and importance scores
        """
        # Build call graph
        call_graph_analyzer = CallGraphAnalyzer(json_data)
        
        results = []
        
        for node in json_data.get('nodes', []):
            if node.get('type') != 'function':
                continue
            
            metrics = self._analyze_function(node, call_graph_analyzer)
            results.append(asdict(metrics))
        
        # Sort by importance score (descending)
        results.sort(key=lambda x: x['importance_score'], reverse=True)
        
        return results
    
    def _analyze_function(self, node: Dict[str, Any], call_graph: CallGraphAnalyzer) -> FunctionMetrics:
        """Analyze a single function and compute all metrics"""
        func_name = node.get('label', 'unknown')
        file_path = node.get('data', {}).get('filePath', '')
        code = node.get('data', {}).get('code', '')
        node_id = node.get('id', '')
        
        # Initialize metrics
        metrics = FunctionMetrics(name=func_name, file_path=file_path)
        
        # Parse code into AST
        try:
            tree = ast.parse(code)
            func_nodes = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
            
            if not func_nodes:
                return metrics
            
            func_node = func_nodes[0]  # Assume first function is the target
            
            # Complexity analysis
            metrics.cyclomatic_complexity = self.complexity_analyzer.calculate_complexity(func_node)
            metrics.lines_of_code = self.complexity_analyzer.count_lines_of_code(func_node)
            metrics.num_parameters = len(func_node.args.args)
            
            # Pattern detection
            metrics.is_getter_setter = self.pattern_detector.is_getter_setter(func_node)
            metrics.is_single_return = self.pattern_detector.is_single_return(func_node)
            metrics.is_wrapper = self.pattern_detector.is_wrapper(func_node)
            metrics.has_trivial_name = self.pattern_detector.is_trivial_name(func_name)
            metrics.is_dunder_method = func_name.startswith('__') and func_name.endswith('__')
            
            # Business logic scoring
            metrics.business_keyword_score = self.pattern_detector.calculate_business_keyword_score(func_node)
            
        except SyntaxError:
            # If we can't parse, treat as unknown (neutral score)
            pass
        
        # Call graph analysis
        metrics.fan_in = call_graph.get_fan_in(node_id)
        metrics.fan_out = call_graph.get_fan_out(node_id)
        
        # Compute importance score
        metrics.importance_score = self._calculate_importance_score(metrics)
        
        return metrics
    
    def _calculate_importance_score(self, metrics: FunctionMetrics) -> float:
        """
        Calculate importance score using weighted multi-signal approach.
        
        Score range: 0 (definitely utility) to 1 (definitely business logic)
        
        Signal Weights:
        ---------------
        1. Complexity (30%): Higher complexity = more important
        2. Patterns (40%): Utility patterns = less important
        3. Call Graph (20%): High fan-in with simple code = utility
        4. Business Keywords (10%): Domain keywords = more important
        
        Why these weights?
        - Pattern detection is most reliable (explicit naming conventions)
        - Complexity is strong signal but can have exceptions (complex utilities exist)
        - Call graph helps but is context-dependent
        - Keywords are weakest signal (naming can be misleading)
        """
        
        score = 0.5  # Start neutral
        
        # --- Complexity Signals (30% weight) ---
        complexity_score = 0.0
        
        # Cyclomatic complexity contribution
        if metrics.cyclomatic_complexity <= 2:
            complexity_score -= 0.3  # Very simple
        elif metrics.cyclomatic_complexity <= 5:
            complexity_score -= 0.1  # Somewhat simple
        elif metrics.cyclomatic_complexity <= 10:
            complexity_score += 0.1  # Moderate complexity
        else:
            complexity_score += 0.3  # Complex, likely important
        
        # Lines of code contribution
        if metrics.lines_of_code <= 5:
            complexity_score -= 0.2
        elif metrics.lines_of_code <= 15:
            complexity_score += 0.0
        else:
            complexity_score += 0.2
        
        score += complexity_score * 0.3  # Apply 30% weight
        
        # --- Pattern Signals (40% weight) ---
        pattern_score = 0.0
        
        if metrics.is_getter_setter:
            pattern_score -= 0.8  # Strong utility signal
        elif metrics.is_single_return:
            pattern_score -= 0.4  # Likely utility
        elif metrics.is_wrapper:
            pattern_score -= 0.6  # Wrapper functions are utilities
        
        if metrics.has_trivial_name:
            pattern_score -= 0.5  # Naming convention suggests utility
        
        if metrics.is_dunder_method:
            # Dunder methods are infrastructure, not business logic
            pattern_score -= 0.3
        
        score += pattern_score * 0.4  # Apply 40% weight
        
        # --- Call Graph Signals (20% weight) ---
        call_graph_score = 0.0
        
        # High fan-in (many callers) + low complexity = utility
        if metrics.fan_in > 5 and metrics.cyclomatic_complexity <= 5:
            call_graph_score -= 0.4
        elif metrics.fan_in > 10:
            call_graph_score -= 0.2
        
        # Very low fan-in might indicate unused or specialized code
        if metrics.fan_in == 0 and metrics.fan_out == 0:
            call_graph_score -= 0.1  # Possibly dead code or entry point
        
        score += call_graph_score * 0.2  # Apply 20% weight
        
        # --- Business Logic Signals (10% weight) ---
        score += metrics.business_keyword_score * 0.1
        
        # Clamp to [0, 1]
        return max(0.0, min(1.0, score))
    
    def filter_by_threshold(self, results: List[Dict[str, Any]], threshold: float = 0.3) -> Dict[str, List[Dict[str, Any]]]:
        """
        Filter functions into utility and important categories.
        
        Args:
            results: List of function metrics
            threshold: Functions below this score are utilities (default: 0.3)
        
        Returns:
            Dictionary with 'utilities' and 'important' lists
        """
        utilities = [r for r in results if r['importance_score'] < threshold]
        important = [r for r in results if r['importance_score'] >= threshold]
        
        return {
            'utilities': utilities,
            'important': important,
            'threshold': threshold,
            'statistics': {
                'total_functions': len(results),
                'utility_count': len(utilities),
                'important_count': len(important),
                'utility_percentage': len(utilities) / len(results) * 100 if results else 0
            }
        }


def main():
    """
    Main entry point for the service.
    Reads JSON from stdin or file and outputs ranked functions.
    """
    import sys
    
    # Read input
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)
    
    # Analyze
    service = UtilityDetectorService()
    results = service.analyze_repository(data)
    
    # Filter and output
    filtered = service.filter_by_threshold(results, threshold=0.3)
    
    print(json.dumps(filtered, indent=2))


if __name__ == '__main__':
    main()


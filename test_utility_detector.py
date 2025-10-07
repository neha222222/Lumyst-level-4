"""
Test Suite for Utility Detector

Demonstrates testing approach and validates core functionality.
"""

import json
from utility_detector import (
    UtilityDetectorService,
    ComplexityAnalyzer,
    PatternDetector,
    CallGraphAnalyzer,
    FunctionMetrics
)


def test_complexity_analyzer():
    """Test cyclomatic complexity calculation"""
    print("Testing ComplexityAnalyzer...")
    
    import ast
    
    # Test 1: Simple function (CC = 1)
    code1 = """
def simple():
    return 42
"""
    tree = ast.parse(code1)
    func = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)][0]
    cc = ComplexityAnalyzer.calculate_complexity(func)
    assert cc == 1, f"Expected CC=1, got {cc}"
    print(f"  ✓ Simple function: CC={cc}")
    
    # Test 2: Function with if statement (CC = 2)
    code2 = """
def with_if(x):
    if x > 0:
        return True
    return False
"""
    tree = ast.parse(code2)
    func = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)][0]
    cc = ComplexityAnalyzer.calculate_complexity(func)
    assert cc == 2, f"Expected CC=2, got {cc}"
    print(f"  ✓ Function with if: CC={cc}")
    
    # Test 3: Complex function (CC = 5)
    code3 = """
def complex_func(x, y):
    if x > 0:
        if y > 0:
            return x + y
        else:
            return x
    elif x < 0:
        return -x
    return 0
"""
    tree = ast.parse(code3)
    func = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)][0]
    cc = ComplexityAnalyzer.calculate_complexity(func)
    assert cc >= 4, f"Expected CC>=4, got {cc}"
    print(f"  ✓ Complex function: CC={cc}")
    
    print("  ✅ ComplexityAnalyzer passed!\n")


def test_pattern_detector():
    """Test pattern detection"""
    print("Testing PatternDetector...")
    
    import ast
    
    # Test 1: Getter/Setter
    code_getter = """
def get_value(self):
    return self.value
"""
    tree = ast.parse(code_getter)
    func = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)][0]
    is_getter = PatternDetector.is_getter_setter(func)
    assert is_getter, "Failed to detect getter"
    print(f"  ✓ Getter detected: {is_getter}")
    
    # Test 2: Trivial naming
    assert PatternDetector.is_trivial_name("get_user") == True
    assert PatternDetector.is_trivial_name("set_value") == True
    assert PatternDetector.is_trivial_name("is_valid") == True
    assert PatternDetector.is_trivial_name("format_date") == True
    assert PatternDetector.is_trivial_name("process_payment") == False
    print(f"  ✓ Trivial name detection working")
    
    # Test 3: Single return
    code_single = """
def add(a, b):
    return a + b
"""
    tree = ast.parse(code_single)
    func = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)][0]
    is_single = PatternDetector.is_single_return(func)
    assert is_single, "Failed to detect single return"
    print(f"  ✓ Single return detected: {is_single}")
    
    print("  ✅ PatternDetector passed!\n")


def test_scoring_system():
    """Test the scoring algorithm"""
    print("Testing Scoring System...")
    
    service = UtilityDetectorService()
    
    # Test case 1: Obvious utility (getter)
    mock_data_utility = {
        'nodes': [{
            'id': 'test1',
            'type': 'function',
            'label': 'get_value',
            'data': {
                'code': 'def get_value(self):\n    return self.value',
                'filePath': 'utils.py'
            }
        }],
        'edges': []
    }
    
    results = service.analyze_repository(mock_data_utility)
    score = results[0]['importance_score']
    assert score < 0.3, f"Utility function scored too high: {score}"
    print(f"  ✓ Utility function score: {score:.3f} (< 0.3)")
    
    # Test case 2: Complex business logic
    mock_data_important = {
        'nodes': [{
            'id': 'test2',
            'type': 'function',
            'label': 'process_payment',
            'data': {
                'code': '''def process_payment(amount, method, customer):
    if amount <= 0:
        raise ValueError("Invalid amount")
    
    if method == "credit":
        if customer.credit_valid():
            return charge_credit(amount)
        else:
            return False
    elif method == "debit":
        return charge_debit(amount)
    else:
        raise ValueError("Unknown method")
''',
                'filePath': 'payment.py'
            }
        }],
        'edges': []
    }
    
    results = service.analyze_repository(mock_data_important)
    score = results[0]['importance_score']
    assert score >= 0.3, f"Important function scored too low: {score}"
    print(f"  ✓ Important function score: {score:.3f} (>= 0.3)")
    
    print("  ✅ Scoring system passed!\n")


def test_end_to_end():
    """Test complete workflow"""
    print("Testing End-to-End Workflow...")
    
    # Create mock data with various function types
    mock_data = {
        'nodes': [
            {
                'id': 'util1',
                'type': 'function',
                'label': 'get_name',
                'data': {
                    'code': 'def get_name(self):\n    return self.name',
                    'filePath': 'models.py'
                }
            },
            {
                'id': 'util2',
                'type': 'function',
                'label': 'format_date',
                'data': {
                    'code': 'def format_date(date):\n    return date.strftime("%Y-%m-%d")',
                    'filePath': 'utils.py'
                }
            },
            {
                'id': 'important1',
                'type': 'function',
                'label': 'authenticate_user',
                'data': {
                    'code': '''def authenticate_user(username, password):
    user = find_user(username)
    if not user:
        return None
    if verify_password(password, user.hash):
        create_session(user)
        return user
    return None
''',
                    'filePath': 'auth.py'
                }
            }
        ],
        'edges': []
    }
    
    service = UtilityDetectorService()
    results = service.analyze_repository(mock_data)
    filtered = service.filter_by_threshold(results, threshold=0.3)
    
    print(f"  ✓ Analyzed {len(results)} functions")
    print(f"  ✓ Utilities: {filtered['statistics']['utility_count']}")
    print(f"  ✓ Important: {filtered['statistics']['important_count']}")
    
    # Verify expected counts
    assert filtered['statistics']['utility_count'] >= 2, "Should detect at least 2 utilities"
    assert filtered['statistics']['important_count'] >= 1, "Should detect at least 1 important function"
    
    print("  ✅ End-to-end test passed!\n")


def test_edge_cases():
    """Test edge cases and error handling"""
    print("Testing Edge Cases...")
    
    service = UtilityDetectorService()
    
    # Test 1: Empty input
    empty_data = {'nodes': [], 'edges': []}
    results = service.analyze_repository(empty_data)
    assert len(results) == 0, "Empty input should return empty results"
    print("  ✓ Empty input handled")
    
    # Test 2: Malformed code
    bad_code_data = {
        'nodes': [{
            'id': 'bad1',
            'type': 'function',
            'label': 'broken',
            'data': {
                'code': 'def broken syntax error(',
                'filePath': 'bad.py'
            }
        }],
        'edges': []
    }
    results = service.analyze_repository(bad_code_data)
    assert len(results) == 1, "Should still return result for malformed code"
    print("  ✓ Malformed code handled gracefully")
    
    # Test 3: Missing fields
    minimal_data = {
        'nodes': [{
            'id': 'min1',
            'type': 'function',
            'label': 'minimal',
            'data': {}
        }],
        'edges': []
    }
    results = service.analyze_repository(minimal_data)
    assert len(results) == 1, "Should handle minimal data"
    print("  ✓ Missing fields handled")
    
    print("  ✅ Edge cases passed!\n")


def test_performance():
    """Test performance on realistic data"""
    print("Testing Performance...")
    
    import time
    
    # Generate mock data with 100 functions
    large_data = {
        'nodes': [
            {
                'id': f'func{i}',
                'type': 'function',
                'label': f'function_{i}',
                'data': {
                    'code': f'def function_{i}():\n    return {i}',
                    'filePath': f'module{i % 10}.py'
                }
            }
            for i in range(100)
        ],
        'edges': []
    }
    
    service = UtilityDetectorService()
    
    start = time.time()
    results = service.analyze_repository(large_data)
    elapsed = time.time() - start
    
    functions_per_sec = len(results) / elapsed if elapsed > 0 else float('inf')
    
    print(f"  ✓ Processed {len(results)} functions in {elapsed:.3f}s")
    print(f"  ✓ Throughput: {functions_per_sec:.0f} functions/second")
    
    assert elapsed < 1.0, f"Should process 100 functions in < 1 second, took {elapsed:.3f}s"
    
    print("  ✅ Performance test passed!\n")


def run_all_tests():
    """Run complete test suite"""
    print("\n" + "=" * 80)
    print("UTILITY DETECTOR - TEST SUITE")
    print("=" * 80 + "\n")
    
    try:
        test_complexity_analyzer()
        test_pattern_detector()
        test_scoring_system()
        test_end_to_end()
        test_edge_cases()
        test_performance()
        
        print("=" * 80)
        print("✅ ALL TESTS PASSED!")
        print("=" * 80)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        raise


if __name__ == '__main__':
    run_all_tests()


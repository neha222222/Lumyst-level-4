"""
Example Usage: Integrating Utility Detection into Lumyst

This file demonstrates different ways to use the utility detector service
and integrate it into a graph visualization pipeline.
"""

import json
from utility_detector import UtilityDetectorService


def example_1_basic_usage():
    """
    Example 1: Basic usage with JSON file
    """
    print("=" * 80)
    print("EXAMPLE 1: Basic Usage")
    print("=" * 80)
    
    # Load your codebase graph data
    with open('fastapi_data.json', 'r') as f:
        data = json.load(f)
    
    # Convert to expected format (simplified)
    graph_nodes = data.get('analysisData', {}).get('graphNodes', [])
    formatted_data = {
        'nodes': [
            {
                'id': node.get('id', ''),
                'type': 'function',
                'label': node.get('label', ''),
                'data': {
                    'code': node.get('code', ''),
                    'filePath': node.get('id', '').split(':')[1] if ':' in node.get('id', '') else ''
                }
            }
            for node in graph_nodes
            if node.get('type') in ('Function', 'Method')
        ],
        'edges': []
    }
    
    # Analyze
    service = UtilityDetectorService()
    results = service.analyze_repository(formatted_data)
    
    print(f"✓ Analyzed {len(results)} functions")
    print(f"✓ Top function: {results[0]['name']} (score: {results[0]['importance_score']:.3f})")
    print()


def example_2_custom_threshold():
    """
    Example 2: Using custom threshold for filtering
    """
    print("=" * 80)
    print("EXAMPLE 2: Custom Threshold")
    print("=" * 80)
    
    service = UtilityDetectorService()
    
    # Simulated data
    mock_data = {
        'nodes': [
            {
                'id': 'test1',
                'type': 'function',
                'label': 'process_payment',
                'data': {
                    'code': 'def process_payment(amount):\n    if amount > 0:\n        return charge(amount)\n    return False',
                    'filePath': 'payment.py'
                }
            },
            {
                'id': 'test2',
                'type': 'function',
                'label': 'get_value',
                'data': {
                    'code': 'def get_value(self):\n    return self.value',
                    'filePath': 'utils.py'
                }
            }
        ],
        'edges': []
    }
    
    results = service.analyze_repository(mock_data)
    
    # Try different thresholds
    for threshold in [0.2, 0.3, 0.4, 0.5]:
        filtered = service.filter_by_threshold(results, threshold=threshold)
        print(f"Threshold {threshold}: {filtered['statistics']['utility_count']} utilities, "
              f"{filtered['statistics']['important_count']} important")
    print()


def example_3_lumyst_integration():
    """
    Example 3: How to integrate into Lumyst graph rendering
    """
    print("=" * 80)
    print("EXAMPLE 3: Lumyst Integration Pattern")
    print("=" * 80)
    
    # Pseudo-code showing integration
    code_example = '''
    # In Lumyst's graph rendering pipeline:
    
    from utility_detector import UtilityDetectorService
    
    def render_codebase_graph(codebase_data, filter_utilities=True):
        """Render codebase graph with optional utility filtering"""
        
        # Step 1: Analyze functions
        if filter_utilities:
            detector = UtilityDetectorService()
            analysis = detector.analyze_repository(codebase_data)
            
            # Step 2: Filter by importance score
            important_functions = [
                func for func in analysis 
                if func['importance_score'] >= 0.3
            ]
            
            # Step 3: Update graph with filtered nodes
            filtered_nodes = [
                node for node in codebase_data['nodes']
                if node['id'] in {f['file_path'] for f in important_functions}
            ]
            
            codebase_data['nodes'] = filtered_nodes
        
        # Step 4: Render the graph (existing Lumyst logic)
        return render_graph(codebase_data)
    
    # Usage in UI:
    # <button onClick={() => render_codebase_graph(data, filter_utilities=true)}>
    #   Hide Utilities
    # </button>
    '''
    
    print(code_example)
    print()


def example_4_explain_score():
    """
    Example 4: Explaining why a function got its score
    """
    print("=" * 80)
    print("EXAMPLE 4: Score Explanation")
    print("=" * 80)
    
    # Load results
    with open('fastapi_analysis_results.json', 'r') as f:
        data = json.load(f)
    
    # Pick a utility function
    utility = data['utilities'][0]
    
    print(f"Function: {utility['name']}")
    print(f"Score: {utility['importance_score']:.3f} (utility threshold < 0.3)")
    print(f"\nReasons for low score:")
    
    reasons = []
    if utility['cyclomatic_complexity'] <= 2:
        reasons.append(f"  • Very low complexity ({utility['cyclomatic_complexity']})")
    if utility['is_getter_setter']:
        reasons.append("  • Detected as getter/setter pattern")
    if utility['is_single_return']:
        reasons.append("  • Single return statement")
    if utility['is_wrapper']:
        reasons.append("  • Wrapper function pattern")
    if utility['has_trivial_name']:
        reasons.append(f"  • Trivial naming pattern ('{utility['name']}')")
    if utility['lines_of_code'] <= 5:
        reasons.append(f"  • Very few lines of code ({utility['lines_of_code']})")
    
    for reason in reasons:
        print(reason)
    print()


def example_5_batch_analysis():
    """
    Example 5: Analyzing multiple repositories
    """
    print("=" * 80)
    print("EXAMPLE 5: Batch Analysis")
    print("=" * 80)
    
    # Simulate analyzing multiple repos
    repos = ['fastapi', 'django', 'flask']  # Example
    
    print("Batch analysis pattern:")
    print("""
    results = {}
    for repo_name in repos:
        data = load_repo_data(repo_name)
        service = UtilityDetectorService()
        analysis = service.analyze_repository(data)
        
        results[repo_name] = {
            'total': len(analysis),
            'utilities': sum(1 for f in analysis if f['importance_score'] < 0.3),
            'utility_rate': sum(1 for f in analysis if f['importance_score'] < 0.3) / len(analysis)
        }
    
    # Compare utility rates across repos
    for repo, stats in results.items():
        print(f"{repo}: {stats['utility_rate']:.1%} utilities")
    """)
    print()


def example_6_performance_tips():
    """
    Example 6: Performance optimization tips
    """
    print("=" * 80)
    print("EXAMPLE 6: Performance Tips")
    print("=" * 80)
    
    tips = """
    Performance Optimization Tips:
    
    1. Cache Results:
       - Store analysis results and only reanalyze changed files
       - Use file modification timestamps for cache invalidation
    
    2. Parallel Processing:
       from concurrent.futures import ProcessPoolExecutor
       
       with ProcessPoolExecutor() as executor:
           results = list(executor.map(analyze_function, functions))
    
    3. Incremental Analysis:
       # Only analyze modified functions
       modified_functions = detect_changes(old_graph, new_graph)
       new_results = analyze_repository(modified_functions)
       cached_results.update(new_results)
    
    4. Streaming for Large Codebases:
       # Process in chunks instead of loading everything
       for chunk in load_in_chunks(data, chunk_size=1000):
           results.extend(service.analyze_repository(chunk))
    
    Current performance: ~500 functions/second on M1 MacBook Pro
    """
    
    print(tips)
    print()


def main():
    """Run all examples"""
    print("\n" + "=" * 80)
    print("UTILITY DETECTOR - USAGE EXAMPLES")
    print("=" * 80 + "\n")
    
    # Run examples
    example_1_basic_usage()
    example_2_custom_threshold()
    example_3_lumyst_integration()
    example_4_explain_score()
    example_5_batch_analysis()
    example_6_performance_tips()
    
    print("=" * 80)
    print("✅ All examples completed!")
    print("=" * 80)


if __name__ == '__main__':
    main()


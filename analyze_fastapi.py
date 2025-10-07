"""
Main entry point for analyzing the FastAPI repository.

This script:
1. Loads the JSON data from Lumyst's analysis
2. Converts it to the expected format
3. Runs the utility detection service
4. Outputs ranked results
"""

import json
import sys
from utility_detector import UtilityDetectorService


def load_and_convert_data(file_path: str) -> dict:
    """
    Load JSON data and convert to expected format.
    
    The input format has graphNodes as a dictionary where each key is a node ID
    and each value contains node information including code.
    
    We need to convert this to a format with:
    - nodes: list of function nodes
    - edges: list of call relationships
    """
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    graph_nodes = data.get('analysisData', {}).get('graphNodes', [])
    
    # Convert to expected format
    nodes = []
    edges = []
    
    for node_data in graph_nodes:
        # Only process function nodes
        if node_data.get('type') in ('Function', 'Method'):
            node_id = node_data.get('id', '')
            nodes.append({
                'id': node_id,
                'type': 'function',
                'label': node_data.get('label', ''),
                'data': {
                    'code': node_data.get('code', ''),
                    'filePath': node_id.split(':')[1] if ':' in node_id else 'unknown'
                }
            })
    
    # Build edges from code analysis (looking at function calls in code)
    # For now, we'll have a simplified approach without full call graph
    # The fan-in/fan-out metrics will be computed based on available edge data
    # In the real data, edges should come from the graph structure
    
    return {
        'nodes': nodes,
        'edges': edges  # Empty for now, can be enhanced
    }


def main():
    """Main execution"""
    if len(sys.argv) < 2:
        print("Usage: python analyze_fastapi.py <json_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    print("Loading and converting data...")
    data = load_and_convert_data(input_file)
    print(f"Loaded {len(data['nodes'])} functions\n")
    
    print("Running utility detection analysis...")
    service = UtilityDetectorService()
    results = service.analyze_repository(data)
    
    print(f"Analysis complete. Processed {len(results)} functions.\n")
    
    # Filter by threshold
    filtered = service.filter_by_threshold(results, threshold=0.3)
    
    # Print statistics
    print("=" * 80)
    print("ANALYSIS RESULTS")
    print("=" * 80)
    print(f"Total Functions: {filtered['statistics']['total_functions']}")
    print(f"Utility Functions: {filtered['statistics']['utility_count']} "
          f"({filtered['statistics']['utility_percentage']:.1f}%)")
    print(f"Important Functions: {filtered['statistics']['important_count']}")
    print(f"Threshold: {filtered['threshold']}")
    print("=" * 80)
    
    # Show top 10 most important functions
    print("\n📌 TOP 10 MOST IMPORTANT FUNCTIONS:")
    print("-" * 80)
    for i, func in enumerate(results[:10], 1):
        print(f"{i}. {func['name']}")
        print(f"   Score: {func['importance_score']:.3f} | "
              f"Complexity: {func['cyclomatic_complexity']} | "
              f"LOC: {func['lines_of_code']}")
        print(f"   File: {func['file_path']}")
        print()
    
    # Show sample utility functions
    print("\n🔧 SAMPLE UTILITY FUNCTIONS (Low Importance):")
    print("-" * 80)
    utilities = filtered['utilities'][:10]
    for i, func in enumerate(utilities, 1):
        print(f"{i}. {func['name']}")
        print(f"   Score: {func['importance_score']:.3f} | "
              f"Complexity: {func['cyclomatic_complexity']} | "
              f"LOC: {func['lines_of_code']}")
        reasons = []
        if func['is_getter_setter']:
            reasons.append("getter/setter")
        if func['is_single_return']:
            reasons.append("single return")
        if func['is_wrapper']:
            reasons.append("wrapper")
        if func['has_trivial_name']:
            reasons.append("trivial name")
        if reasons:
            print(f"   Reasons: {', '.join(reasons)}")
        print()
    
    # Save full results to file
    output_file = 'fastapi_analysis_results.json'
    with open(output_file, 'w') as f:
        json.dump(filtered, f, indent=2)
    
    print(f"\n✅ Full results saved to: {output_file}")
    print("\nYou can now use this ranked list to filter your codebase graph!")


if __name__ == '__main__':
    main()

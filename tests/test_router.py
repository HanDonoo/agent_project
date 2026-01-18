"""
Test the AI Router functionality
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.router import QueryRouter, QueryType


def test_router():
    """Test the query router with various query types"""
    router = QueryRouter()
    
    print("=" * 60)
    print("Testing AI Router - Query Classification")
    print("=" * 60)
    
    # Test cases
    test_queries = [
        # Direct lookups
        ("Find john.doe@onenz.co.nz", QueryType.DIRECT_LOOKUP),
        ("What's the email for jane.smith@onenz.co.nz?", QueryType.DIRECT_LOOKUP),
        
        # Simple searches
        ("Find someone in billing team", QueryType.SIMPLE_SEARCH),
        ("Who is in Auckland office?", QueryType.SIMPLE_SEARCH),
        ("Show me network engineers", QueryType.SIMPLE_SEARCH),
        
        # Complex intents
        ("I need help with BIA provisioning for a new customer", QueryType.COMPLEX_INTENT),
        ("Who can assist with network security compliance?", QueryType.COMPLEX_INTENT),
        ("Looking for someone to help set up enterprise provisioning", QueryType.COMPLEX_INTENT),
        
        # Conversational
        ("Thanks for the help!", QueryType.CONVERSATIONAL),
        ("Hello", QueryType.CONVERSATIONAL),
        ("Goodbye", QueryType.CONVERSATIONAL),
        
        # Ambiguous
        ("Help", QueryType.AMBIGUOUS),
        ("Find", QueryType.AMBIGUOUS),
    ]
    
    passed = 0
    failed = 0
    
    for query, expected_type in test_queries:
        result = router.route_query(query)
        actual_type = result['query_type']
        strategy = result['strategy']
        confidence = result['confidence']
        
        # Check if classification is correct
        is_correct = actual_type == expected_type
        status = "✅ PASS" if is_correct else "❌ FAIL"
        
        if is_correct:
            passed += 1
        else:
            failed += 1
        
        print(f"\n{status}")
        print(f"Query: '{query}'")
        print(f"Expected: {expected_type.value}")
        print(f"Actual: {actual_type.value}")
        print(f"Strategy: {strategy}")
        print(f"Confidence: {confidence:.2f}")
        print(f"Reasoning: {result['reasoning']}")
        
        if result['extracted_info']:
            print(f"Extracted: {result['extracted_info']}")
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed out of {len(test_queries)} tests")
    print("=" * 60)
    
    # Performance summary
    print("\n" + "=" * 60)
    print("Strategy Distribution:")
    print("=" * 60)
    
    strategies = {}
    for query, _ in test_queries:
        result = router.route_query(query)
        strategy = result['strategy']
        strategies[strategy] = strategies.get(strategy, 0) + 1
    
    for strategy, count in strategies.items():
        percentage = (count / len(test_queries)) * 100
        print(f"{strategy:10s}: {count:2d} queries ({percentage:5.1f}%)")
    
    print("\n" + "=" * 60)
    print("AI Usage Analysis:")
    print("=" * 60)
    
    ai_needed = sum(1 for q, _ in test_queries if router.should_use_ai(router.route_query(q)))
    no_ai_needed = len(test_queries) - ai_needed
    
    print(f"Queries needing AI:     {ai_needed:2d} ({ai_needed/len(test_queries)*100:5.1f}%)")
    print(f"Queries without AI:     {no_ai_needed:2d} ({no_ai_needed/len(test_queries)*100:5.1f}%)")
    print(f"\n💡 Efficiency: {no_ai_needed/len(test_queries)*100:.1f}% of queries can be handled without AI!")
    
    return passed == len(test_queries)


def test_should_use_ai():
    """Test the should_use_ai method"""
    router = QueryRouter()
    
    print("\n" + "=" * 60)
    print("Testing should_use_ai() Method")
    print("=" * 60)
    
    test_cases = [
        ("john.doe@onenz.co.nz", False, "Email lookup - no AI needed"),
        ("Find someone in billing", False, "Simple search - no AI needed"),
        ("I need help with provisioning", True, "Complex intent - AI needed"),
        ("Thanks!", True, "Conversational - AI needed"),
        ("Help", True, "Ambiguous - AI needed"),
    ]
    
    for query, expected_ai, reason in test_cases:
        result = router.route_query(query)
        needs_ai = router.should_use_ai(result)
        
        status = "✅" if needs_ai == expected_ai else "❌"
        ai_status = "AI needed" if needs_ai else "No AI needed"
        
        print(f"\n{status} '{query}'")
        print(f"   Expected: {'AI' if expected_ai else 'No AI'}")
        print(f"   Actual: {ai_status}")
        print(f"   Reason: {reason}")


if __name__ == "__main__":
    print("\n🤖 AI Router Test Suite\n")
    
    # Run tests
    success = test_router()
    test_should_use_ai()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed - review output above")
    print("=" * 60)


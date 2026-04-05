import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fallback_llm.llm_xml_generator import generate_fallback_outputs
from unittest.mock import patch, MagicMock

def test_scenario(name, mock_response, expected_success=True):
    print(f"\n>>> Testing Scenario: {name}")
    
    with patch('openai.OpenAI') as mock_openai:
        # Mock client.chat.completions.create
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content=mock_response))]
        mock_client.chat.completions.create.return_value = mock_completion
        
        # Test generate_fallback_outputs
        xml, py = generate_fallback_outputs("Test problem")
        
        success = "<xml" in xml.lower() and "</xml>" in xml.lower() and len(py.strip()) > 10
        
        py_display = py[:50].replace('\n', ' ')
        print(f"XML snippet: {xml[:50]}...")
        print(f"Python snippet: {py_display}...")
        
        if success == expected_success:
            print(f"✅ Result as expected ({'Success' if success else 'Failure'})")
        else:
            print(f"❌ Unexpected result! Expected {'Success' if expected_success else 'Failure'}, got {'Success' if success else 'Failure'}")
            print(f"RAW: {mock_response}")

if __name__ == "__main__":
    # 1. Perfect JSON
    test_scenario("Perfect JSON", '{"xml": "<xml><block type=\\"text_print\\"></block></xml>", "python": "print(\\"hello world\\")"}')
    
    # 2. JSON with Markdown (should fallback to heuristic)
    test_scenario("JSON with Markdown", 'Sure! Here is the JSON:\n```json\n{"xml": "<xml><block type=\\"text_print\\"></block></xml>", "python": "print(\\"hello world\\")"}\n```')
    
    # 3. Messy text with XML and Python (no JSON)
    test_scenario("Heuristic Separation", 'Here is the XML:\n<xml><block type="text_print"></block></xml>\nAnd here is the Python:\ndef solve():\n    print("hello")\nsolve()')
    
    # 4. Total garbage
    test_scenario("Total Garbage", 'I cannot help with that.', expected_success=False)

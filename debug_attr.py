
import os, sys
PROJECT_ROOT = os.path.abspath(".")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from core.generators.llm import LLMGenerator
    gen = LLMGenerator("gemini", "none")
    print(f"LLMGenerator has _repair_and_parse_json: {hasattr(gen, '_repair_and_parse_json')}")
    if hasattr(gen, '_repair_and_parse_json'):
        print("Test calling it...")
        res = gen._repair_and_parse_json('{"test": 1}')
        print(f"Result: {res}")
except Exception as e:
    print(f"Error: {e}")

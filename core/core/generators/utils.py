import json

def repair_and_parse_json(content: str) -> dict:
    """v47 Advanced JSON Repair. Mikey"""
    if not content or len(content.strip()) < 10:
        return None
        
    # 1. Strip Markdown
    content = content.strip()
    if content.startswith("```json"):
        content = content[7:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()
    
    # 2. Try Standard Load
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
        
    # 3. Emergency Cleaning: Find first { and last }
    try:
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1:
            chunk = content[start:end+1]
            return json.loads(chunk)
    except:
        pass
        
    # 4. Harder clean: Replace some common errors
    try:
        # Replace smart quotes
        clean = content.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
        return json.loads(clean)
    except:
        pass
        
    return None

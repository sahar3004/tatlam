from tatlam.core.rules import RuleEngine
from tatlam.core.doctrine import get_system_prompt

def verify():
    print("=== Rule Engine Verification ===")
    re = RuleEngine()
    print(f"Loaded {len(re.rules)} rules.")
    
    # Test Context 1: Surface Suspicious Object
    ctx_surface = {
        "location_type": "surface",
        "category": "suspicious_object"
    }
    rules_surface = re.get_rules(ctx_surface)
    print("\n[Surface Rules]:")
    for r in rules_surface:
        print(f"- {r.id}: {r.content[:50]}...")
        
    # Test Context 2: Underground Suspicious Object
    ctx_underground = {
        "location_type": "underground",
        "category": "suspicious_object"
    }
    rules_underground = re.get_rules(ctx_underground)
    print("\n[Underground Rules]:")
    for r in rules_underground:
        print(f"- {r.id}: {r.content[:50]}...")
        
    # Check for exclusion
    surface_only = [r for r in rules_surface if "surface" in r.id]
    underground_only = [r for r in rules_underground if "underground" in r.id]
    
    if surface_only and not any(r in rules_underground for r in surface_only):
        print("\n✅ SUCCESS: Surface rules NOT present in Underground context.")
    else:
        print("\n❌ SPLIT FAIL: Context leakage detected.")

    # Test System Prompt Injection
    print("\n[System Prompt Injection Check]")
    prompt = get_system_prompt("writer", venue="jaffa", context=ctx_surface)
    if "*** הנחיות דינמיות וחוקים מעודכנים (Active Rules) ***" in prompt:
         print("✅ SUCCESS: Dynamic rules section found in prompt.")
         if "Train can skip station" in prompt or " trains" in prompt or "Dilug" in prompt: # Check for content from suspicious_object.yaml
             print("✅ SUCCESS: Specific content found.")
         else:
             print("⚠️ WARNING: Specific content not found in prompt.")
    else:
         print("❌ FAIL: Dynamic rules section MISSING.")

if __name__ == "__main__":
    verify()

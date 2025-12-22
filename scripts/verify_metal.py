import time
import sys
from tatlam.core.local_llm import LocalQwenProvider

def verify_metal_performance():
    print("🧪 Starting Metal Performance Smoke Test...")
    
    try:
        # Initialize with verbose=False to reduce noise, unless we fail
        provider = LocalQwenProvider(verbose=True)
        
        prompt = "Write a haiku about cybersecurity."
        print(f"\n📝 Prompt: '{prompt}'")
        
        start_time = time.time()
        # Mocking TTFT measurement requires streaming or deeper hook, 
        # for now we measure total generation time/TPS.
        
        response = provider.generate(prompt, max_tokens=100)
        end_time = time.time()
        
        print(f"\n🤖 Response:\n{response.strip()}\n")
        
        # We rely on the internal print of the provider for TPS, 
        # but let's calculate rough aggregate here too.
        # Since we can't easily get exact token count without tokenizer outside, 
        # we'll estimate or trust the provider's internal log which we saw in local_llm.py
        
    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    verify_metal_performance()

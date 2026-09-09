import time
import urllib.request
import json
import sys

def probe(model):
    print(f'Probing {model}...')
    # Cold start
    try:
        urllib.request.urlopen('http://127.0.0.1:11434/api/generate', data=json.dumps({'model': model, 'prompt': 'hi', 'stream': False}).encode(), timeout=10)
    except Exception:
        pass
    time.sleep(2)

    start = time.time()
    try:
        req = urllib.request.Request(
            'http://127.0.0.1:11434/api/generate',
            data=json.dumps({'model': model, 'prompt': 'досчитай до ста по-русски', 'stream': False, 'num_predict': 128}).encode(),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            j = json.loads(resp.read().decode())
    except Exception as e:
        print(f"Error probing {model}: {e}")
        return

    end = time.time()
    gen_time = end - start
    total_tokens = j.get('eval_count', 0)
    prompt_tokens = j.get('prompt_eval_count', 0)
    eval_duration = j.get('eval_duration', 1) / 1e9
    prompt_eval_duration = j.get('prompt_eval_duration', 1) / 1e9
    
    gen_tps = total_tokens / gen_time if gen_time > 0 else 0
    prompt_tps = prompt_tokens / prompt_eval_duration if prompt_eval_duration > 0 else 0
    
    print(f"  Result: Gen: {gen_tps:.2f} t/s, Prompt: {prompt_tps:.2f} t/s")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        probe(sys.argv[1])
    else:
        print("Usage: python probe.py <model_name>")

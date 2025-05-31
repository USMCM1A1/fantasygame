import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("DEBUG: Minimal test started. Attempting to import common_b_s...", flush=True)
try:
    import common_b_s
    print("DEBUG: common_b_s imported successfully.", flush=True)
except Exception as e:
    print(f"CRITICAL ERROR importing common_b_s: {e}", flush=True)
    sys.exit(1)

print("DEBUG: Minimal test finished.", flush=True)

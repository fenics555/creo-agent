# -*- coding: utf-8 -*-
import sys, os
sys.path.append(r"D:\AI\tools\agent")
sys.path.append(r"D:\AI\tools")
import behavior_tools as bt

if __name__ == "__main__":
    print("Starting behavior_run...")
    try:
        result = bt.run()
        print("\n=== BEHAVIOR REPORT ===\n")
        print(result)
        print("\n=======================")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error: {e}")

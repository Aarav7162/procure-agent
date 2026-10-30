import json

path = r"C:\Users\aarav.SOMEGUYWITHPRET\.gemini\antigravity\brain\0781f990-710b-4a29-95f3-77c687ca8fa4\.system_generated\logs\transcript_full.jsonl"
with open(path, "r", encoding="utf-8") as f:
    for line in f:
        obj = json.loads(line)
        if obj.get("step_index") == 87:
            for tc in obj.get("tool_calls", []):
                args = tc.get("args", {})
                print("=== STEP 87 index.css ===")
                raw = args.get("CodeContent", "")
                if raw.startswith('"') and raw.endswith('"'):
                    code = json.loads(raw)
                else:
                    code = raw
                print(code)
        elif obj.get("step_index") == 94:
            for tc in obj.get("tool_calls", []):
                args = tc.get("args", {})
                print("=== STEP 94 App.tsx ===")
                raw = args.get("CodeContent", "")
                if raw.startswith('"') and raw.endswith('"'):
                    code = json.loads(raw)
                else:
                    code = raw
                print(code)


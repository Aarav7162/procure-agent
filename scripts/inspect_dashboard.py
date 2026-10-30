import re

with open('dashboard/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

ids = set(re.findall(r'getElementById\(["\']([^"\']+)["\']\)', text))
qs = set(re.findall(r'querySelector\(["\']#([a-zA-Z0-9_\-]+)["\']\)', text))
all_ids = sorted(list(ids | qs))
print("Referenced IDs count:", len(all_ids))
print("Referenced IDs:", all_ids)

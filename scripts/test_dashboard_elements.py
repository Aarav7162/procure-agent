import re

with open('dashboard/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

buttons = [
    'chip-code', 'chip-impossible', 'chip-adversarial', 'chip-ocr', 'chip-sensor',
    'btn-submit', 'btn-attack', 'btn-occupy', 'btn-mode-live', 'btn-mode-replay',
    'btn-replay-play', 'btn-replay-prev', 'btn-replay-next', 'nav-command', 'nav-treasury',
    'nav-marketplace', 'nav-verification', 'nav-paypal', 'nav-ledger'
]

missing = [x for x in buttons if f'id="{x}"' not in content]
print("Missing elements:", missing if missing else "None! All 19 interactive controls are present.")

# Check key styles
print("ambient-globe present:", "ambient-globe" in content)
print("ambient-beams-layer present:", "ambient-beams-layer" in content)
print("marketplace-canvas present:", "marketplace-canvas" in content)
print("toast-banner present:", "toast-banner" in content)
print("top-search-input present:", "top-search-input" in content)


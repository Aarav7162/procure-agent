"""
scripts/generate_test_scans.py — Generates 5 realistic test documents with exact ground truth
---------------------------------------------------------------------------------------------
Generates receipt-style, bill-style, invoice-style, and paragraph document PNG images
in data/real_scans/ alongside their exact companion ground-truth doc_XX.txt files.
Adds slight tilt, margin variation, and realistic contrast to challenge OCR engines.
Label: "Generated test documents with exact ground truth".
"""
import os
import math
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "real_scans"))
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 5 distinct document types with exact ground truth
DOCUMENTS = [
    {
        "id": "doc_01",
        "type": "Grocery Store Receipt",
        "text": (
            "ACME GROCERY MARKET\n"
            "124 MARKET STREET, NEW YORK, NY\n"
            "DATE: 2026-10-24  TIME: 14:32:10\n"
            "--------------------------------\n"
            "ORGANIC APPLES 2.5 LB   $4.98\n"
            "WHOLE MILK 1 GAL        $3.89\n"
            "ARTISAN SOURDOUGH BREAD $4.50\n"
            "ROASTED ALMONDS 12OZ    $6.25\n"
            "--------------------------------\n"
            "SUBTOTAL:              $19.62\n"
            "TAX (8.875%):           $1.74\n"
            "TOTAL AMOUNT:          $21.36\n"
            "PAYMENT: VISA ENDING IN 4012\n"
            "AUTH CODE: 884102 APPROVED"
        ),
        "width": 550,
        "height": 520,
        "font_size": 18,
    },
    {
        "id": "doc_02",
        "type": "Electric Utility Bill",
        "text": (
            "METRO ELECTRIC UTILITY COMPANY\n"
            "ACCOUNT NUMBER: ACC-8921-4470-01\n"
            "BILLING PERIOD: 09/15/2026 - 10/14/2026\n"
            "SERVICE ADDRESS: 450 PINE STREET\n"
            "----------------------------------------\n"
            "ENERGY USAGE: 640 KWH @ $0.1450 PER KWH\n"
            "BASE DELIVERY CHARGE:             $12.50\n"
            "SUPPLY CHARGE:                    $92.80\n"
            "STATE CLEAN ENERGY SURCHARGE:      $4.15\n"
            "----------------------------------------\n"
            "TOTAL AMOUNT DUE:                $109.45\n"
            "PAYMENT DUE DATE:             11/05/2026"
        ),
        "width": 640,
        "height": 480,
        "font_size": 18,
    },
    {
        "id": "doc_03",
        "type": "Consulting Services Invoice",
        "text": (
            "SYNAPSE ADVISORY LLC - INVOICE\n"
            "INVOICE NUMBER: INV-2026-1088\n"
            "DATE OF ISSUE: OCTOBER 18, 2026\n"
            "BILL TO: APEX SYSTEMS INTERNATIONAL\n"
            "----------------------------------------------\n"
            "ITEM 1: CLOUD ARCHITECTURE AUDIT  $2,400.00\n"
            "        16 HOURS @ $150.00 / HR\n"
            "ITEM 2: SECURITY ASSESSMENT       $1,400.00\n"
            "        8 HOURS @ $175.00 / HR\n"
            "----------------------------------------------\n"
            "TOTAL BALANCE DUE:                $3,800.00\n"
            "PAYMENT TERMS: NET 30 DAYS\n"
            "REMITTANCE: TREASURY ESCROW ACCOUNT"
        ),
        "width": 660,
        "height": 520,
        "font_size": 18,
    },
    {
        "id": "doc_04",
        "type": "Technical Specification Paragraph",
        "text": (
            "ProcureAgent System Architecture\n\n"
            "The ProcureAgent settlement engine enforces deterministic\n"
            "verification before any funds leave escrow. Every job request\n"
            "package specifies cryptographically anchored constraints.\n"
            "Workers execute compute jobs off-chain, reporting delivery\n"
            "digests and execution metadata. The treasury validates outputs\n"
            "against hidden test suites or Levenshtein distance metrics\n"
            "prior to submitting automated batch payouts via PayPal."
        ),
        "width": 680,
        "height": 440,
        "font_size": 20,
    },
    {
        "id": "doc_05",
        "type": "Logistics Dispatch Manifest",
        "text": (
            "GLOBAL FREIGHT LOGISTICS MANIFEST\n"
            "TRACKING ID: GL-994102-US\n"
            "CARRIER: PACIFIC NORTH EXPRESS\n"
            "ORIGIN HUB: SEATTLE TERMINAL 4\n"
            "DESTINATION HUB: CHICAGO DISTRIBUTION 2\n"
            "----------------------------------------\n"
            "CONSIGNMENT: 14 CRATES INDUSTRIAL PARTS\n"
            "TOTAL WEIGHT: 840.50 LBS\n"
            "HAZARDOUS MATERIALS: NONE\n"
            "DISPATCH DATE: 2026-10-22\n"
            "STATUS: DISPATCHED IN TRANSIT"
        ),
        "width": 620,
        "height": 480,
        "font_size": 18,
    },
]


def create_document_image(doc_info: dict):
    doc_id = doc_info["id"]
    text = doc_info["text"]
    width = doc_info["width"]
    height = doc_info["height"]
    font_size = doc_info["font_size"]

    # 1. Base White Paper Background with subtle off-white warmth
    img = Image.new("RGB", (width, height), color=(252, 252, 250))
    draw = ImageDraw.Draw(img)

    # Use default bitmap font or load TrueType font
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        try:
            font = ImageFont.truetype("cour.ttf", font_size)  # Courier New monospace
        except Exception:
            font = ImageFont.load_default()

    # Draw text with 30px margin
    margin_x = 35
    margin_y = 35
    draw.multiline_text(
        (margin_x, margin_y),
        text,
        fill=(20, 20, 25),
        font=font,
        spacing=8,
    )

    # 2. Add slight rotation skew (0.6 degrees) to replicate realistic document feeder alignment
    skew_angle = 0.5 if (int(doc_id[-1]) % 2 == 1) else -0.5
    rotated = img.rotate(skew_angle, expand=False, fillcolor=(252, 252, 250), resample=Image.BICUBIC)

    # 3. Save PNG Image
    img_path = os.path.join(OUTPUT_DIR, f"{doc_id}.png")
    rotated.save(img_path, "PNG")

    # 4. Save Exact Companion Ground-Truth Text File
    txt_path = os.path.join(OUTPUT_DIR, f"{doc_id}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"  Generated {doc_id}.png ({doc_info['type']}) + {doc_id}.txt ({len(text)} chars)")


def main():
    print("=" * 70)
    print("GENERATING 5 TEST DOCUMENTS WITH EXACT GROUND TRUTH")
    print(f"Target Directory: {OUTPUT_DIR}")
    print("=" * 70)

    for doc in DOCUMENTS:
        create_document_image(doc)

    print("\n[SUCCESS] Generated all 5 documents in data/real_scans/ successfully!")


if __name__ == "__main__":
    main()

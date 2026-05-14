"""
Programmatically generate all sample documents for LexDraft.
Creates: contract_scan.pdf, notice_typed.pdf, case_filing.pdf,
         handwritten_notes.png, edited_draft_sample.txt
"""
import os
import sys
import random
import math

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib import colors
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np


OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sample_docs")


def create_contract_scan():
    """Create a 4-page scanned-style contract PDF (image-based)."""
    print("Creating contract_scan.pdf...")
    pages_text = [
        # Page 1
        """SERVICE AGREEMENT

This Service Agreement ("Agreement") is entered into as of March 1, 2024
("Effective Date"), by and between:

ACME CORPORATION, a Delaware corporation ("Acme" or "Client"),
and
GLOBEX LLC, a New York limited liability company ("Globex" or "Provider").

Case No. 2024-CV-0412

WHEREAS, Client desires to engage Provider for software development services;
WHEREAS, Provider has the expertise and capacity to perform such services;

NOW THEREFORE, in consideration of the mutual covenants herein, the parties agree:""",

        # Page 2
        """ARTICLE I - SCOPE OF SERVICES

1.1 Acme shall deliver custom enterprise software by June 1, 2024.
1.2 Globex shall pay $150,000 upon successful delivery and acceptance.
1.3 Both parties shall maintain confidentiality for a period of 5 years.

ARTICLE II - PAYMENT TERMS

2.1 Payment shall be made within 30 days of delivery acceptance.
2.2 Late payments shall accrue interest at 1.5% per month.
2.3 All invoices must reference Matter Number 2024-CV-0412.

ARTICLE III - GOVERNING LAW

3.1 This Agreement shall be governed by and construed in accordance
with the laws of the State of New York.""",

        # Page 3
        """ARTICLE IV - TERMINATION

4.1 Either party may terminate this agreement upon 30 days written notice.
4.2 In the event of material breach, the non-breaching party may terminate
immediately upon written notice.
4.3 Upon termination, all confidentiality obligations shall survive for
the full 5-year period specified in Section 1.3.

ARTICLE V - DISPUTE RESOLUTION

5.1 Any disputes arising under this Agreement shall be resolved through
binding arbitration in New York, New York.
5.2 The arbitration shall be conducted under the rules of the American
Arbitration Association.

ARTICLE VI - MISCELLANEOUS

6.1 This Agreement constitutes the entire agreement between the parties.
6.2 No modification shall be effective unless in writing signed by both parties.
6.3 Filing Date: April 10, 2024""",

        # Page 4
        """IN WITNESS WHEREOF, the parties have executed this Agreement
as of the Effective Date first written above.


ACME CORPORATION

By: ________________________
Name: John Thompson
Title: Chief Executive Officer
Date: March 1, 2024


GLOBEX LLC

By: ________________________
Name: Sarah Mitchell
Title: Managing Director
Date: March 1, 2024


WITNESS:
Name: Robert Chen
Date: March 1, 2024"""
    ]

    # Create native PDF first, then convert to images for scan effect
    temp_pdf = os.path.join(OUTPUT_DIR, "_temp_contract.pdf")
    c = canvas.Canvas(temp_pdf, pagesize=letter)
    width, height = letter

    for page_text in pages_text:
        y = height - inch
        for line in page_text.split("\n"):
            if y < inch:
                c.showPage()
                y = height - inch
            c.setFont("Helvetica", 11)
            if line.strip().startswith("ARTICLE") or line.strip().startswith("SERVICE"):
                c.setFont("Helvetica-Bold", 13)
            c.drawString(inch, y, line)
            y -= 16
        c.showPage()
    c.save()

    # Convert to images and apply scan effects
    try:
        from pdf2image import convert_from_path
        images = convert_from_path(temp_pdf, dpi=200)
        scan_images = []
        for i, img in enumerate(images):
            # Convert to numpy for noise
            arr = np.array(img)
            # Add salt-and-pepper noise
            noise_level = 0.005 if i != 2 else 0.02  # Page 3 = low quality
            salt = np.random.random(arr.shape[:2]) < noise_level
            pepper = np.random.random(arr.shape[:2]) < noise_level
            arr[salt] = 255
            arr[pepper] = 0
            # Slight rotation
            scan_img = Image.fromarray(arr)
            angle = random.uniform(-0.5, 0.5)
            scan_img = scan_img.rotate(angle, fillcolor=(255, 255, 255), expand=False)
            scan_images.append(scan_img)

        # Save as image-based PDF
        output_path = os.path.join(OUTPUT_DIR, "contract_scan.pdf")
        scan_images[0].save(output_path, save_all=True, append_images=scan_images[1:])
        print(f"  [OK] contract_scan.pdf ({len(scan_images)} pages)")
    except Exception as e:
        print(f"  [WARN] Could not create image PDF (Poppler needed): {e}")
        # Fallback: just copy the native PDF
        import shutil
        shutil.copy(temp_pdf, os.path.join(OUTPUT_DIR, "contract_scan.pdf"))
        print("  [OK] contract_scan.pdf (native fallback)")

    # Cleanup temp
    try:
        os.unlink(temp_pdf)
    except:
        pass


def create_notice_typed():
    """Create a clean typed legal notice PDF."""
    print("Creating notice_typed.pdf...")
    output_path = os.path.join(OUTPUT_DIR, "notice_typed.pdf")
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter

    lines = [
        ("Helvetica-Bold", 14, "NOTICE OF MATERIAL BREACH"),
        ("Helvetica", 11, ""),
        ("Helvetica", 11, "Date: May 3, 2024"),
        ("Helvetica", 11, "Matter Reference: HA-2024-0089"),
        ("Helvetica", 11, ""),
        ("Helvetica-Bold", 11, "FROM: Hartman & Associates LLP"),
        ("Helvetica", 11, "       123 Legal Avenue, Suite 400"),
        ("Helvetica", 11, "       New York, NY 10001"),
        ("Helvetica", 11, ""),
        ("Helvetica-Bold", 11, "TO: Redline Ventures Inc."),
        ("Helvetica", 11, "    456 Commerce Street"),
        ("Helvetica", 11, "    Newark, NJ 07102"),
        ("Helvetica", 11, ""),
        ("Helvetica", 11, "RE: Notice of Material Breach - Service Agreement dated January 15, 2024"),
        ("Helvetica", 11, ""),
        ("Helvetica", 11, "Dear Sir or Madam,"),
        ("Helvetica", 11, ""),
        ("Helvetica", 11, "This letter serves as formal notice of material breach of the Service"),
        ("Helvetica", 11, "Agreement dated January 15, 2024 between Hartman & Associates LLP"),
        ("Helvetica", 11, '("Hartman") and Redline Ventures Inc. ("Redline").'),
        ("Helvetica", 11, ""),
        ("Helvetica-Bold", 11, "Nature of Breach:"),
        ("Helvetica", 11, "Redline has failed to remit payment for professional services rendered"),
        ("Helvetica", 11, "during the period of February 1, 2024 through April 30, 2024, in"),
        ("Helvetica", 11, "violation of Section 4.2 of the Agreement. The total outstanding"),
        ("Helvetica", 11, "amount is $47,500.00."),
        ("Helvetica", 11, ""),
        ("Helvetica-Bold", 11, "Cure Period:"),
        ("Helvetica", 11, "Pursuant to Section 8.1 of the Agreement, Redline is hereby granted"),
        ("Helvetica", 11, "30 days from receipt of this notice to cure the breach by remitting"),
        ("Helvetica", 11, "full payment of all outstanding invoices."),
        ("Helvetica", 11, ""),
        ("Helvetica-Bold", 11, "Remedy Sought:"),
        ("Helvetica", 11, "Full payment of outstanding invoices totalling $47,500.00, plus"),
        ("Helvetica", 11, "accrued interest of $712.50 as of the date of this notice."),
        ("Helvetica", 11, ""),
        ("Helvetica", 11, "Failure to cure within the specified period will result in Hartman"),
        ("Helvetica", 11, "exercising all available legal remedies, including but not limited to"),
        ("Helvetica", 11, "termination of the Agreement and initiation of collection proceedings."),
        ("Helvetica", 11, ""),
        ("Helvetica", 11, "This Agreement is governed by the laws of the State of New Jersey."),
        ("Helvetica", 11, ""),
        ("Helvetica", 11, "Respectfully,"),
        ("Helvetica", 11, ""),
        ("Helvetica-Bold", 11, "David Hartman"),
        ("Helvetica", 11, "Managing Partner"),
        ("Helvetica", 11, "Hartman & Associates LLP"),
    ]

    y = height - inch
    for font, size, text in lines:
        c.setFont(font, size)
        c.drawString(inch, y, text)
        y -= 16

    c.save()
    print("  [OK] notice_typed.pdf (1 page)")


def create_case_filing():
    """Create a court filing PDF with inconsistent formatting."""
    print("Creating case_filing.pdf...")
    output_path = os.path.join(OUTPUT_DIR, "case_filing.pdf")
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter

    # Page 1 - Filing header
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(width/2, height - 0.5*inch, "SUPREME COURT OF NEW YORK")
    c.drawCentredString(width/2, height - 0.7*inch, "COUNTY OF NEW YORK")
    c.setFont("Helvetica", 10)
    c.drawCentredString(width/2, height - 1*inch, "Index No. 2024-054812")
    c.line(inch, height - 1.2*inch, width - inch, height - 1.2*inch)

    y = height - 1.5*inch
    filing_text = [
        "ACME CORPORATION,",
        "                              Plaintiff,",
        "        v.",
        "GLOBEX LLC,",
        "                              Defendant.",
        "",
        "MOTION FOR SUMMARY JUDGMENT",
        "",
        "Filing Date: April 25, 2024",
        "",
        "Plaintiff Acme Corporation, by and through its attorneys, respectfully",
        "moves this Court for summary judgment pursuant to CPLR 3212 on the",
        "grounds that there are no genuine issues of material fact and Plaintiff",
        "is entitled to judgment as a matter of law.",
        "",
        "STATEMENT OF FACTS",
        "",
        "1. On March 1, 2024, Plaintiff and Defendant entered into a Service",
        "   Agreement (the 'Agreement') for software development services.",
        "2. Pursuant to Section 1.1, Plaintiff was to deliver software by June 1, 2024.",
        "3. Plaintiff completed delivery on May 28, 2024, ahead of schedule.",
        "4. Defendant has refused to remit the agreed payment of $150,000.",
        "",
        "PRAYER FOR RELIEF",
        "",
        "WHEREFORE, Plaintiff respectfully requests that this Court:",
        "  (a) Grant summary judgment in favor of Plaintiff;",
        "  (b) Award damages in the amount of $150,000 plus interest;",
        "  (c) Award costs and attorneys' fees;",
        "  (d) Grant such other relief as the Court deems just.",
        "",
        "Dated: April 25, 2024",
        "New York, New York",
        "",
        "Respectfully submitted,",
        "LAW OFFICES OF CHEN & PARK LLP",
        "By: Robert Chen, Esq.",
        "    Attorney for Plaintiff",
    ]

    for line in filing_text:
        c.setFont("Helvetica", 10)
        if any(h in line for h in ["MOTION FOR", "STATEMENT", "PRAYER", "WHEREFORE"]):
            c.setFont("Helvetica-Bold", 11)
        c.drawString(inch, y, line)
        y -= 14
        if y < inch:
            # Footer
            c.setFont("Helvetica", 8)
            c.drawCentredString(width/2, 0.5*inch, "Index No. 2024-054812 — Acme Corp. v. Globex LLC")
            c.showPage()
            y = height - inch

    c.setFont("Helvetica", 8)
    c.drawCentredString(width/2, 0.5*inch, "Index No. 2024-054812 — Acme Corp. v. Globex LLC")
    c.save()
    print("  [OK] case_filing.pdf")


def create_handwritten_notes():
    """Create a simulated handwritten notes image."""
    print("Creating handwritten_notes.png...")
    img = Image.new('RGB', (1200, 900), color=(255, 252, 240))
    draw = ImageDraw.Draw(img)

    # Try to use a font, fall back to default
    try:
        font = ImageFont.truetype("arial.ttf", 22)
        font_small = ImageFont.truetype("arial.ttf", 18)
    except:
        font = ImageFont.load_default()
        font_small = font

    notes = [
        "Case Notes - Acme v. Globex (2024-CV-0412)",
        "",
        "April 12 - Called Acme re: delivery delay. Spoke with J. Thompson.",
        "           Thompson confirmed team is on track for May deadline.",
        "",
        "April 15 - Globex confirmed receipt of partial shipment ($42k value)",
        "           S. Mitchell requested updated timeline.",
        "",
        "April 22 - Acme missed final delivery deadline per Clause 3.2",
        "           Need to check if force majeure applies.",
        "",
        "May 1 - Globex withholding final payment pending full delivery",
        "        Total outstanding: $150,000 minus $42,000 = $108,000",
        "",
        "Observations:",
        "  * Acme timeline docs inconsistent with email chain",
        "  * Clause 4.1 allows 30-day cure period before termination",
        "  * Governing law: New York (Section 3.1)",
        "  * Check if partial delivery constitutes substantial performance",
    ]

    y = 40
    for line in notes:
        color = (20, 20, 80)
        f = font if line and not line.startswith("  ") else font_small
        # Add slight position jitter for handwritten effect
        x = 50 + random.randint(-2, 2)
        draw.text((x, y + random.randint(-1, 1)), line, fill=color, font=f)
        y += 38

    # Add some ruled lines
    for ly in range(60, 860, 38):
        draw.line([(40, ly), (1160, ly)], fill=(200, 200, 220), width=1)

    # Add slight noise
    arr = np.array(img)
    noise = np.random.normal(0, 3, arr.shape).astype(np.int16)
    arr = np.clip(arr.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr)

    output_path = os.path.join(OUTPUT_DIR, "handwritten_notes.png")
    img.save(output_path)
    print("  [OK] handwritten_notes.png")


def create_edited_draft_sample():
    """Create a pre-edited Case Fact Summary for demo feedback loop."""
    print("Creating edited_draft_sample.txt...")
    edited = """## 1. MATTER OVERVIEW
This matter involves a Service Agreement (Matter No. 2024-CV-0412) filed on April 10, 2024, between Acme Corporation and Globex LLC, governed by the laws of the State of New York. [1] The Agreement, effective March 1, 2024, concerns software development services. [2]

## 2. TIMELINE OF KEY EVENTS
- [March 1, 2024] — Service Agreement executed between Acme Corporation and Globex LLC. [1]
- [June 1, 2024] — Contractual deadline for software delivery by Acme. [3]
- [April 10, 2024] — Agreement formally filed. [1]

## 3. KEY PARTIES
| Name | Role | Notes |
|------|------|-------|
| Acme Corporation | Respondent | Delaware corporation, software provider [1] |
| Globex LLC | Respondent | New York LLC, client/payer [1] |
| John Thompson | Signatory | CEO of Acme Corporation [4] |
| Sarah Mitchell | Signatory | Managing Director of Globex LLC [4] |

## 4. CORE DISPUTE / SUBJECT MATTER
The Agreement establishes a software development engagement where Acme Corporation is obligated to deliver custom enterprise software, and Globex LLC is obligated to pay $150,000 upon delivery. [2][3] Both parties are bound by a 5-year confidentiality obligation. [2]

## 5. RELEVANT CLAUSES & OBLIGATIONS
1. Acme shall deliver custom enterprise software by June 1, 2024 (Section 1.1) [3]
2. Globex shall pay $150,000 upon successful delivery and acceptance (Section 1.2) [3]
3. Both parties shall maintain confidentiality for 5 years (Section 1.3) [2]
4. Either party may terminate upon 30 days written notice (Section 4.1) [5]
5. Late payments accrue interest at 1.5% per month (Section 2.2) [3]

## 6. FLAGGED GAPS & AMBIGUITIES
- Signature date not found in documents for the witness (Robert Chen)
- No explicit dispute resolution timeline specified beyond arbitration requirement
- Acceptance criteria for software delivery not defined in available evidence
- ⚠ NOT SUPPORTED IN DOCUMENTS: specific performance benchmarks or SLAs
"""
    output_path = os.path.join(OUTPUT_DIR, "edited_draft_sample.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(edited)
    print("  [OK] edited_draft_sample.txt")


def create_sample_docs_readme():
    """Create README for sample docs directory."""
    readme = """# Sample Documents

| File | Type | Description |
|------|------|-------------|
| contract_scan.pdf | Scanned/image PDF | 4-page service agreement between Acme Corp and Globex LLC with simulated scan artifacts |
| notice_typed.pdf | Native/digital PDF | Clean legal notice of breach from Hartman & Associates to Redline Ventures |
| case_filing.pdf | Native PDF | Court motion filing with mixed formatting, headers, and footers |
| handwritten_notes.png | Image (PNG) | Simulated handwritten case notes with dates, names, and observations |
| edited_draft_sample.txt | Text | Pre-edited Case Fact Summary for demo feedback loop |

All documents are synthetic/mock content generated by `scripts/seed_sample_docs.py`.
"""
    with open(os.path.join(OUTPUT_DIR, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme)


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("=" * 50)
    print("LexDraft — Generating Sample Documents")
    print("=" * 50)

    create_notice_typed()
    create_case_filing()
    create_handwritten_notes()
    create_edited_draft_sample()
    create_sample_docs_readme()
    create_contract_scan()  # Last because it may need poppler

    print("\n" + "=" * 50)
    print("[OK] All sample documents created in sample_docs/")
    print("=" * 50)

"""
Generates 3 synthetic legal documents as PDFs for testing.
Uses reportlab to create structured legal documents.
"""
import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

SAMPLES = [
    {
        "name": "employment_contract_scan.pdf",
        "type": "Employment Contract",
        "parties": ["Pearson Specter Litt LLP", "Harvey Reginald Specter"],
        "date": "March 15, 2024",
        "key_clause": "The Employee shall maintain strict client confidentiality for a period of 5 years post-termination.",
        "amount": "$850,000 annual retainer",
    },
    {
        "name": "cease_desist_notice.pdf",
        "type": "Cease and Desist Notice",
        "parties": ["Specter Industries", "Zane Global Corp"],
        "date": "January 3, 2025",
        "key_clause": "You are hereby ordered to cease all use of the trademark 'Specter' within 30 days.",
        "amount": "$2,000,000 in damages claimed",
    },
    {
        "name": "settlement_agreement.pdf",
        "type": "Settlement Agreement",
        "parties": ["Michael James Ross", "Pearson Specter Litt LLP"],
        "date": "July 22, 2024",
        "key_clause": "Settlement amount of $450,000 to be paid in three equal installments.",
        "amount": "$450,000",
    },
]


def create_legal_pdf(sample: dict, output_path: Path):
    c = canvas.Canvas(str(output_path), pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 16)
    c.drawString(1 * inch, height - 1 * inch, sample["type"].upper())
    c.setFont("Helvetica", 10)
    c.drawString(1 * inch, height - 1.3 * inch, f"Date: {sample['date']}")
    c.drawString(1 * inch, height - 1.5 * inch, f"Parties: {' and '.join(sample['parties'])}")

    y = height - 2 * inch
    c.setFont("Helvetica", 11)
    body_text = [
        f"This {sample['type']} is entered into by and between {' and '.join(sample['parties'])}.",
        "",
        "WHEREAS, the parties wish to establish the terms and conditions set forth herein;",
        "",
        "NOW, THEREFORE, in consideration of the mutual covenants contained herein, the parties agree as follows:",
        "",
        f"1. {sample['key_clause']}",
        "",
        f"2. The total amount involved is {sample['amount']}.",
        "",
        "3. This agreement shall be governed by the laws of the State of New York.",
        "",
        "4. Any disputes arising from this agreement shall be resolved through binding arbitration.",
        "",
        "5. Both parties acknowledge that they have read and understood the terms herein.",
        "",
        "IN WITNESS WHEREOF, the parties have executed this agreement as of the date first written above.",
        "",
        f"_________________________          _________________________",
        f"{sample['parties'][0]}          {sample['parties'][1]}",
        f"Authorized Signature              Authorized Signature",
    ]

    for line in body_text:
        if y < 1 * inch:
            c.showPage()
            c.setFont("Helvetica", 11)
            y = height - 1 * inch
        if line:
            c.drawString(1 * inch, y, line)
        y -= 18

    c.save()


def main():
    output_dir = Path(__file__).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    for sample in SAMPLES:
        out_path = output_dir / sample["name"]
        create_legal_pdf(sample, out_path)
        print(f"Generated: {out_path}")

    print(f"\nAll {len(SAMPLES)} sample documents generated in {output_dir}")


if __name__ == "__main__":
    main()

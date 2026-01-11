#!/usr/bin/env python3
"""
Generate test invoices in three formats for testing document classification:
1. Text PDF - Searchable PDF with text
2. Scanned PDF - PDF rendered as image (no extractable text)
3. PNG Image - Direct image file
"""

import os
from pathlib import Path
from datetime import datetime, timedelta
import random

# Ensure we can import reportlab and PIL
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from PIL import Image, ImageDraw, ImageFont
    import fitz  # PyMuPDF
except ImportError as e:
    print(f"Error: Missing dependency. Install with: pip install reportlab pillow PyMuPDF")
    print(f"Details: {e}")
    exit(1)

# Test data
TEST_COMPANIES = [
    {"name": "TechCore AB", "org": "559421-9601", "country": "SE", "currency": "SEK"},
    {"name": "Global Solutions GmbH", "org": "DE123456789", "country": "DE", "currency": "EUR"},
    {"name": "Nordic Trade Inc", "org": "554455-1122", "country": "SE", "currency": "SEK"},
    {"name": "Innovation Labs Ltd", "org": "GB987654321", "country": "GB", "currency": "GBP"},
]

TEST_PRODUCTS = [
    ("Consulting Services", 5000),
    ("Software License", 2500),
    ("Cloud Infrastructure", 8000),
    ("Support & Maintenance", 1500),
    ("Training Program", 3000),
    ("Hardware Equipment", 12000),
]

def generate_text_pdf(filename: str, company: dict):
    """Generate searchable text PDF"""
    doc = SimpleDocTemplate(filename, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    # Header
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#003366'),
        spaceAfter=30,
    )
    story.append(Paragraph("INVOICE", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Invoice details
    invoice_num = f"INV-{datetime.now().year}-{random.randint(1000, 9999)}"
    invoice_date = datetime.now().strftime("%Y-%m-%d")
    due_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    
    details_data = [
        ["Invoice Number:", invoice_num, "Invoice Date:", invoice_date],
        ["Organization:", company["org"], "Due Date:", due_date],
        ["Company:", company["name"], "Currency:", company["currency"]],
    ]
    
    details_table = Table(details_data, colWidths=[1.5*inch, 2*inch, 1.5*inch, 2*inch])
    details_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ]))
    story.append(details_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Items table
    items = random.sample(TEST_PRODUCTS, k=random.randint(2, 4))
    vat_rate = 0.25 if company["country"] == "SE" else 0.19 if company["country"] == "DE" else 0.20
    
    table_data = [["Description", "Quantity", "Unit Price", "Total"]]
    total_amount = 0
    
    for product, price in items:
        qty = random.randint(1, 3)
        line_total = price * qty
        total_amount += line_total
        table_data.append([product, str(qty), f"{price:,.0f}", f"{line_total:,.0f}"])
    
    vat_amount = total_amount * vat_rate
    grand_total = total_amount + vat_amount
    
    table_data.append(["", "", "Subtotal:", f"{total_amount:,.0f}"])
    table_data.append(["", "", f"VAT ({vat_rate*100:.0f}%):", f"{vat_amount:,.0f}"])
    table_data.append(["", "", "TOTAL:", f"{grand_total:,.0f}"])
    
    items_table = Table(table_data, colWidths=[3*inch, 1*inch, 1.5*inch, 1.5*inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, -3), (-1, -1), colors.HexColor('#f0f0f0')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(items_table)
    
    doc.build(story)
    print(f"✅ Text PDF: {filename}")

def generate_scanned_pdf(filename: str, company: dict):
    """Generate scanned PDF (rendered image, no extractable text)"""
    # First generate a text PDF
    temp_pdf = filename.replace('.pdf', '_temp.pdf')
    generate_text_pdf(temp_pdf, company)
    
    # Render to image using PyMuPDF
    pdf_doc = fitz.open(temp_pdf)
    first_page = pdf_doc[0]
    
    # Render at high quality
    pix = first_page.get_pixmap(matrix=fitz.Matrix(2, 2))
    image_path = filename.replace('.pdf', '.png')
    pix.save(image_path)
    
    pdf_doc.close()
    
    # Now create a PDF from the image (this makes it a scanned PDF)
    img = Image.open(image_path)
    img_converted = img.convert('RGB')
    
    # Create PDF from image
    img_converted.save(filename, 'PDF')
    
    # Clean up temp files
    os.remove(temp_pdf)
    os.remove(image_path)
    
    print(f"✅ Scanned PDF: {filename}")

def generate_png_image(filename: str, company: dict):
    """Generate invoice as PNG image"""
    width, height = 800, 1100
    image = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(image)
    
    # Try to use a default font, fallback to default if not available
    try:
        title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 40)
        heading_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
        body_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 11)
    except:
        title_font = heading_font = body_font = ImageFont.load_default()
    
    y = 40
    
    # Header
    draw.text((40, y), "INVOICE", fill='black', font=title_font)
    y += 60
    
    # Company info
    invoice_num = f"INV-{datetime.now().year}-{random.randint(1000, 9999)}"
    invoice_date = datetime.now().strftime("%Y-%m-%d")
    due_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    
    draw.text((40, y), f"Company: {company['name']}", fill='black', font=body_font)
    y += 25
    draw.text((40, y), f"Organization: {company['org']}", fill='black', font=body_font)
    y += 25
    draw.text((40, y), f"Invoice #: {invoice_num}", fill='black', font=body_font)
    y += 25
    draw.text((40, y), f"Date: {invoice_date}", fill='black', font=body_font)
    y += 25
    draw.text((40, y), f"Due: {due_date}", fill='black', font=body_font)
    y += 40
    
    # Items
    draw.text((40, y), "Description", fill='#003366', font=heading_font)
    draw.text((400, y), "Qty", fill='#003366', font=heading_font)
    draw.text((480, y), "Unit Price", fill='#003366', font=heading_font)
    draw.text((650, y), "Total", fill='#003366', font=heading_font)
    y += 30
    
    items = random.sample(TEST_PRODUCTS, k=random.randint(2, 4))
    vat_rate = 0.25 if company["country"] == "SE" else 0.19 if company["country"] == "DE" else 0.20
    
    total_amount = 0
    for product, price in items:
        qty = random.randint(1, 3)
        line_total = price * qty
        total_amount += line_total
        
        draw.text((40, y), product[:40], fill='black', font=body_font)
        draw.text((400, y), str(qty), fill='black', font=body_font)
        draw.text((480, y), f"{price:,.0f}", fill='black', font=body_font)
        draw.text((650, y), f"{line_total:,.0f}", fill='black', font=body_font)
        y += 25
    
    y += 20
    vat_amount = total_amount * vat_rate
    grand_total = total_amount + vat_amount
    
    draw.text((480, y), "Subtotal:", fill='black', font=heading_font)
    draw.text((650, y), f"{total_amount:,.0f}", fill='black', font=heading_font)
    y += 25
    
    draw.text((480, y), f"VAT ({vat_rate*100:.0f}%):", fill='black', font=heading_font)
    draw.text((650, y), f"{vat_amount:,.0f}", fill='black', font=heading_font)
    y += 30
    
    draw.rectangle([(480, y-5), (800, y+2)], fill='#f0f0f0')
    draw.text((480, y), "TOTAL:", fill='black', font=heading_font)
    draw.text((650, y), f"{grand_total:,.0f}", fill='black', font=heading_font)
    
    image.save(filename)
    print(f"✅ PNG Image: {filename}")

def main():
    # Create documents directory if needed
    docs_dir = Path("documents/raw")
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    print("Generating test invoices...\n")
    
    # Generate invoices for each company
    for i, company in enumerate(TEST_COMPANIES, 1):
        safe_name = company["name"].replace(" ", "_").lower()
        
        # Text PDF
        text_pdf = docs_dir / f"{i:02d}_textpdf_{safe_name}.pdf"
        generate_text_pdf(str(text_pdf), company)
        
        # Scanned PDF
        scanned_pdf = docs_dir / f"{i:02d}_scanned_{safe_name}.pdf"
        generate_scanned_pdf(str(scanned_pdf), company)
        
        # PNG Image
        png_file = docs_dir / f"{i:02d}_image_{safe_name}.png"
        generate_png_image(str(png_file), company)
        
        print()
    
    print("✅ All test invoices generated in documents/raw/")
    print("\nGenerated files:")
    for f in sorted(docs_dir.glob("*")):
        print(f"  - {f.name}")

if __name__ == "__main__":
    main()

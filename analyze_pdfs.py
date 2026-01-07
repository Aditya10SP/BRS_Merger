#!/usr/bin/env python3
"""
Script to analyze and compare PDF structure
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False
    print("PyMuPDF not available, trying alternative...")

def analyze_pdf_with_pymupdf(pdf_path):
    """Analyze PDF using PyMuPDF"""
    doc = fitz.open(pdf_path)
    print(f"\n{'='*60}")
    print(f"PDF: {pdf_path}")
    print(f"{'='*60}")
    print(f"Pages: {len(doc)}")
    print(f"Metadata: {doc.metadata}")
    
    # Analyze first few pages
    for page_num in range(min(3, len(doc))):
        page = doc[page_num]
        print(f"\n--- Page {page_num + 1} ---")
        text = page.get_text()
        print(f"Text length: {len(text)} chars")
        print(f"First 500 chars:\n{text[:500]}")
        
        # Get text blocks with formatting
        blocks = page.get_text("dict")["blocks"]
        print(f"\nNumber of text blocks: {len(blocks)}")
        for i, block in enumerate(blocks[:5]):  # First 5 blocks
            if "lines" in block:
                print(f"\nBlock {i}:")
                for line in block["lines"][:2]:  # First 2 lines
                    for span in line["spans"]:
                        print(f"  Font: {span['font']}, Size: {span['size']:.1f}, Text: {span['text'][:50]}")
    
    doc.close()

def analyze_pdf_with_reportlab(pdf_path):
    """Fallback: Just extract basic info"""
    from PyPDF2 import PdfReader
    
    reader = PdfReader(pdf_path)
    print(f"\n{'='*60}")
    print(f"PDF: {pdf_path}")
    print(f"{'='*60}")
    print(f"Pages: {len(reader.pages)}")
    
    # Extract text from first few pages
    for page_num in range(min(3, len(reader.pages))):
        page = reader.pages[page_num]
        text = page.extract_text()
        print(f"\n--- Page {page_num + 1} ---")
        print(f"Text length: {len(text)} chars")
        print(f"First 500 chars:\n{text[:500]}")

if __name__ == "__main__":
    example_pdf = "test_example/v1.pdf"
    generated_pdf = "data/outputs/BRS-FINAL-1767343687858.pdf"
    
    if HAS_PYMUPDF:
        analyze_pdf_with_pymupdf(example_pdf)
        analyze_pdf_with_pymupdf(generated_pdf)
    else:
        analyze_pdf_with_reportlab(example_pdf)
        analyze_pdf_with_reportlab(generated_pdf)

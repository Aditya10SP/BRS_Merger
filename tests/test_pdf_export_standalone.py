import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.pdf_exporter import PDFExporter
from app.models.schemas import FinalBRS, GeneratedSection

def test_pdf_generation():
    print("Starting PDF generation test...")
    try:
        exporter = PDFExporter()
        
        sections = [
            GeneratedSection(
                section_id="SEC-001",
                section_title="Introduction",
                section_path="1",
                content="This is the introduction section.\nIt has multiple lines.\n\nAnd paragraphs.",
                source_documents=["DOC-1"],
                applied_changes=[]
            ),
            GeneratedSection(
                section_id="SEC-002",
                section_title="Scope",
                section_path="1.1",
                content="This is the scope subsection.\n• Item 1\n• Item 2",
                source_documents=["DOC-1"],
                applied_changes=["CR-1"]
            ),
            GeneratedSection(
                section_id="SEC-003",
                section_title="Functional Requirements",
                section_path="2",
                content="These are functional requirements.",
                source_documents=["DOC-1", "DOC-2"],
                applied_changes=[]
            )
        ]
        
        final_brs = FinalBRS(
            brs_id="BRS-TEST-001",
            title="Test BRS Document",
            version="v1.0",
            sections=sections,
            source_brs_documents=["DOC-1", "DOC-2"],
            applied_change_requests=["CR-1"],
            validation_passed=True,
            validation_notes=["Note 1", "Note 2"]
        )
        
        output_path = Path("test_output.pdf")
        if output_path.exists():
            os.remove(output_path)
            
        exporter.export_to_pdf(final_brs, output_path)
        
        if output_path.exists() and output_path.stat().st_size > 0:
            print(f"SUCCESS: PDF generated at {output_path.absolute()}")
            print(f"Size: {output_path.stat().st_size} bytes")
        else:
            print("FAILURE: PDF not generated or empty")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pdf_generation()

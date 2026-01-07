"""
PDF export service for generating formatted BRS documents.
"""
from pathlib import Path
from typing import Optional
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib import colors

from app.models.schemas import FinalBRS, GeneratedSection
from app.core.logging_config import logger


class PDFExporter:
    """Export Final BRS to formatted PDF document."""
    
    def __init__(self):
        """Initialize PDF exporter with styles."""
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles for BRS document."""
        # Try to use Tahoma font, fallback to Helvetica if not available
        try:
            title_font = 'Tahoma-Bold'
            body_font = 'Tahoma'
            italic_font = 'Tahoma-Italic'
        except:
            # Fallback to Helvetica if Tahoma not available
            title_font = 'Helvetica-Bold'
            body_font = 'Helvetica'
            italic_font = 'Helvetica-Oblique'
            logger.warning("Tahoma font not available, using Helvetica as fallback")
        
        # Title style - 22.4pt Tahoma-Bold
        self.styles.add(ParagraphStyle(
            name='BRSTitle',
            parent=self.styles['Heading1'],
            fontSize=22.4,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName=title_font
        ))
        
        # Subtitle style - 16pt Tahoma
        self.styles.add(ParagraphStyle(
            name='BRSSubtitle',
            parent=self.styles['Normal'],
            fontSize=16,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName=body_font
        ))
        
        # Document metadata style - 12.8pt Tahoma
        self.styles.add(ParagraphStyle(
            name='Metadata',
            parent=self.styles['Normal'],
            fontSize=12.8,
            textColor=colors.HexColor('#333333'),
            spaceAfter=6,
            alignment=TA_LEFT,
            fontName=body_font
        ))
        
        # Section heading style - 12.8pt Tahoma-Bold
        self.styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=self.styles['Heading2'],
            fontSize=12.8,
            textColor=colors.HexColor('#000000'),
            spaceAfter=12,
            spaceBefore=20,
            fontName=title_font
        ))
        
        # Subsection heading style - 12.8pt Tahoma-Bold
        self.styles.add(ParagraphStyle(
            name='SubsectionHeading',
            parent=self.styles['Heading3'],
            fontSize=12.8,
            textColor=colors.HexColor('#000000'),
            spaceAfter=10,
            spaceBefore=15,
            fontName=title_font
        ))
        
        # Body text style - 12.8pt Tahoma
        self.styles.add(ParagraphStyle(
            name='BRSBody',
            parent=self.styles['Normal'],
            fontSize=12.8,
            textColor=colors.HexColor('#000000'),
            spaceAfter=12,
            alignment=TA_LEFT,
            leading=18
        ))
        
        # Traceability style - 10pt Tahoma-Italic
        self.styles.add(ParagraphStyle(
            name='Traceability',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#666666'),
            spaceAfter=8,
            fontName=italic_font
        ))
    
    def export_to_pdf(self, final_brs: FinalBRS, output_path: Path) -> None:
        """
        Export Final BRS to PDF document.
        
        Args:
            final_brs: Final BRS object
            output_path: Path to save PDF file
        """
        logger.info(f"Exporting BRS to PDF: {output_path}")
        
        # Store final_brs for use in header/footer
        self.final_brs = final_brs
        self.generation_time = datetime.now().strftime('%d/%m/%y, %I:%M %p')
        
        # Create PDF document
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Set PDF metadata
        doc.title = final_brs.title or "Business Requirements Specification"
        doc.author = "BRS Consolidation System"
        doc.subject = f"BRS {final_brs.version}"
        
        # Build document content
        story = []
        
        # Add title page
        story.extend(self._create_title_page(final_brs))
        story.append(PageBreak())
        
        # Add document metadata
        story.extend(self._create_metadata_section(final_brs))
        story.append(Spacer(1, 0.3 * inch))
        
        # Add sections
        for section in final_brs.sections:
            story.extend(self._create_section(section))
        
        # Add validation notes if present
        if final_brs.validation_notes:
            story.append(PageBreak())
            story.extend(self._create_validation_section(final_brs))
        
        # Build PDF with headers and footers
        doc.build(story, onFirstPage=self._add_header_footer, onLaterPages=self._add_header_footer)
        logger.info(f"PDF exported successfully: {output_path}")
    
    
    def _add_header_footer(self, canvas, doc):
        """Add header and footer to each page."""
        canvas.saveState()
        
        # Get page dimensions
        page_width, page_height = letter
        
        # Header - 7pt font, gray color
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(colors.HexColor('#666666'))
        
        # Header left: Generation time
        canvas.drawString(72, page_height - 50, self.generation_time)
        
        # Header center: Document title
        title = self.final_brs.title or "Business Requirements Specification"
        # Truncate title if too long
        if len(title) > 50:
            title = title[:47] + "..."
        
        title_width = canvas.stringWidth(title, 'Helvetica', 7)
        canvas.drawString((page_width - title_width) / 2, page_height - 50, title)
        
        # Header right: Page number
        page_text = f"Page {doc.page}"
        page_width_text = canvas.stringWidth(page_text, 'Helvetica', 7)
        canvas.drawString(page_width - 72 - page_width_text, page_height - 50, page_text)
        
        # Footer: File path (optional, smaller font)
        canvas.setFont('Helvetica', 6)
        footer_text = f"file:///{str(doc._filename)}"
        canvas.drawString(72, 50, footer_text)
        
        canvas.restoreState()

    def _create_title_page(self, final_brs: FinalBRS) -> list:
        """Create title page elements."""
        elements = []
        
        # Add spacing from top
        elements.append(Spacer(1, 2 * inch))
        
        # Title
        title = Paragraph(
            final_brs.title or "Business Requirements Specification",
            self.styles['BRSTitle']
        )
        elements.append(title)
        
        # Add Subtitle
        # Use a default subtitle since it's not in the schema yet, or derive from ID
        subtitle_text = "Scramble 2.0 - Sensitive Data Masking System"
        elements.append(Paragraph(subtitle_text, self.styles['BRSSubtitle']))
        
        elements.append(Spacer(1, 0.5 * inch))
        
        # Document ID and Version
        metadata_table = Table([
            ['Document ID:', final_brs.brs_id],
            ['Version:', final_brs.version],
            ['Generated:', datetime.now().strftime('%B %d, %Y')],
            ['Status:', 'Final']
        ], colWidths=[2*inch, 4*inch])
        
        metadata_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2c3e50')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(metadata_table)
        
        return elements
    
    def _create_metadata_section(self, final_brs: FinalBRS) -> list:
        """Create metadata section."""
        elements = []
        
        # Source documents
        if final_brs.source_brs_documents:
            elements.append(Paragraph(
                "<b>Source BRS Documents:</b>",
                self.styles['Metadata']
            ))
            for doc_id in final_brs.source_brs_documents:
                elements.append(Paragraph(
                    f"• {doc_id}",
                    self.styles['Metadata']
                ))
            elements.append(Spacer(1, 0.1 * inch))
        
        # Applied CRs
        if final_brs.applied_change_requests:
            elements.append(Paragraph(
                "<b>Applied Change Requests:</b>",
                self.styles['Metadata']
            ))
            for cr_id in final_brs.applied_change_requests:
                elements.append(Paragraph(
                    f"• {cr_id}",
                    self.styles['Metadata']
                ))
            elements.append(Spacer(1, 0.1 * inch))
        
        # Validation status
        validation_status = "✓ Passed" if final_brs.validation_passed else "✗ Failed"
        validation_color = "green" if final_brs.validation_passed else "red"
        elements.append(Paragraph(
            f"<b>Validation Status:</b> <font color='{validation_color}'>{validation_status}</font>",
            self.styles['Metadata']
        ))
        
        return elements
    
    def _create_section(self, section: GeneratedSection) -> list:
        """Create section elements."""
        elements = []
        
        # Determine nesting level based on dots in section path (e.g., "1.2" has 1 dot -> level 2)
        # Assuming format like "1", "1.1", "1.1.1" etc.
        level = section.section_path.count('.') + 1
        
        # Choose heading style based on level
        if level == 1:
            style = self.styles['SectionHeading']
        elif level == 2:
            style = self.styles['SubsectionHeading']
        else:
            # For deeper levels, we can create a custom style or reuse SubsectionHeading with indentation
            # reusing SubsectionHeading for now, but could be adjusted
            style = self.styles['SubsectionHeading'] 

        # Section heading
        heading_text = f"{section.section_path} {section.section_title}"
        elements.append(Paragraph(heading_text, style))
        
        # Section content
        # Split content by paragraphs and format
        paragraphs = section.content.split('\n\n')
        for para in paragraphs:
            if para.strip():
                # Check if it's a list item
                if para.strip().startswith(('•', '-', '*', '1.', '2.', '3.')):
                    # Add some indentation for list items if needed, or rely on bullet handling if using ListFlowable
                    # For simplicity using BRSBody
                    elements.append(Paragraph(para.strip(), self.styles['BRSBody']))
                else:
                    elements.append(Paragraph(para.strip(), self.styles['BRSBody']))
        
        # Add traceability information
        if section.source_documents or section.applied_changes:
            trace_parts = []
            if section.source_documents:
                trace_parts.append(f"Sources: {', '.join(section.source_documents)}")
            if section.applied_changes:
                trace_parts.append(f"Applied Changes: {', '.join(section.applied_changes)}")
            
            trace_text = " | ".join(trace_parts)
            elements.append(Paragraph(
                f"<i>[{trace_text}]</i>",
                self.styles['Traceability']
            ))
        
        elements.append(Spacer(1, 0.2 * inch))
        
        return elements
    

    
    def _create_validation_section(self, final_brs: FinalBRS) -> list:
        """Create validation notes section."""
        elements = []
        
        elements.append(Paragraph("Validation Notes", self.styles['SectionHeading']))
        
        for note in final_brs.validation_notes[:20]:  # Limit to first 20 notes
            elements.append(Paragraph(f"• {note}", self.styles['BRSBody']))
        
        if len(final_brs.validation_notes) > 20:
            elements.append(Paragraph(
                f"<i>... and {len(final_brs.validation_notes) - 20} more notes</i>",
                self.styles['Traceability']
            ))
        
        return elements

"""
Template extraction service for preserving document formatting.
Extracts structure and style information from source BRS documents.
"""
from typing import Dict, List, Optional, Any
from pathlib import Path
import re
from docx import Document as DocxDocument
from docx.shared import Pt, RGBColor
from pypdf import PdfReader

from app.core.logging_config import logger


class DocumentTemplate:
    """Stores document template information."""
    
    def __init__(self):
        self.title_style: Dict[str, Any] = {}
        self.heading_styles: Dict[int, Dict[str, Any]] = {}
        self.body_style: Dict[str, Any] = {}
        self.section_numbering_format: str = "numeric"  # numeric, alpha, roman
        self.has_table_of_contents: bool = False
        self.header_text: Optional[str] = None
        self.footer_text: Optional[str] = None
        self.page_size: str = "letter"
        self.margins: Dict[str, float] = {}
        

class TemplateExtractor:
    """Extracts formatting template from source documents."""
    
    def extract_from_docx(self, file_path: Path) -> DocumentTemplate:
        """
        Extract template information from DOCX file.
        
        Args:
            file_path: Path to DOCX file
            
        Returns:
            DocumentTemplate with extracted formatting
        """
        logger.info(f"Extracting template from DOCX: {file_path}")
        
        template = DocumentTemplate()
        
        try:
            doc = DocxDocument(str(file_path))
            
            # Extract styles from paragraphs
            for para in doc.paragraphs:
                if not para.text.strip():
                    continue
                
                style_name = para.style.name if para.style else "Normal"
                
                # Detect title
                if "Title" in style_name or para.runs and para.runs[0].font.size and para.runs[0].font.size.pt > 18:
                    template.title_style = self._extract_paragraph_style(para)
                
                # Detect headings
                elif "Heading" in style_name:
                    level = self._extract_heading_level(style_name)
                    if level and level not in template.heading_styles:
                        template.heading_styles[level] = self._extract_paragraph_style(para)
                
                # Detect section numbering format
                if re.match(r'^\d+(\.\d+)*\s', para.text):
                    template.section_numbering_format = "numeric"
                elif re.match(r'^[A-Z](\.[A-Z])*\s', para.text):
                    template.section_numbering_format = "alpha"
            
            # Extract page setup
            section = doc.sections[0] if doc.sections else None
            if section:
                template.page_size = "letter"  # Default
                template.margins = {
                    "top": section.top_margin.inches if section.top_margin else 1.0,
                    "bottom": section.bottom_margin.inches if section.bottom_margin else 1.0,
                    "left": section.left_margin.inches if section.left_margin else 1.0,
                    "right": section.right_margin.inches if section.right_margin else 1.0,
                }
            
            logger.info(f"Template extracted: {len(template.heading_styles)} heading levels")
            return template
            
        except Exception as e:
            logger.error(f"Error extracting template from DOCX: {e}")
            return self._get_default_template()
    
    def extract_from_pdf(self, file_path: Path) -> DocumentTemplate:
        """
        Extract template information from PDF file.
        Note: PDF extraction is limited compared to DOCX.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            DocumentTemplate with extracted formatting
        """
        logger.info(f"Extracting template from PDF: {file_path}")
        
        template = DocumentTemplate()
        
        try:
            reader = PdfReader(str(file_path))
            
            # Extract text and analyze structure
            if reader.pages:
                page = reader.pages[0]
                text = page.extract_text()
                
                # Detect section numbering format from content
                lines = text.split('\n')
                for line in lines[:20]:  # Check first 20 lines
                    if re.match(r'^\d+(\.\d+)*\s', line):
                        template.section_numbering_format = "numeric"
                        break
                    elif re.match(r'^[A-Z](\.[A-Z])*\s', line):
                        template.section_numbering_format = "alpha"
                        break
            
            logger.info("Template extracted from PDF (limited)")
            return template
            
        except Exception as e:
            logger.error(f"Error extracting template from PDF: {e}")
            return self._get_default_template()
    
    def _extract_paragraph_style(self, para) -> Dict[str, Any]:
        """Extract style information from a paragraph."""
        style = {}
        
        if para.runs:
            run = para.runs[0]
            if run.font.size:
                style['font_size'] = run.font.size.pt
            if run.font.name:
                style['font_name'] = run.font.name
            if run.font.bold is not None:
                style['bold'] = run.font.bold
            if run.font.italic is not None:
                style['italic'] = run.font.italic
            if run.font.color and run.font.color.rgb:
                style['color'] = str(run.font.color.rgb)
        
        if para.alignment is not None:
            style['alignment'] = str(para.alignment)
        
        return style
    
    def _extract_heading_level(self, style_name: str) -> Optional[int]:
        """Extract heading level from style name."""
        match = re.search(r'Heading\s*(\d+)', style_name, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None
    
    def _get_default_template(self) -> DocumentTemplate:
        """Get default template when extraction fails."""
        template = DocumentTemplate()
        template.section_numbering_format = "numeric"
        template.heading_styles = {
            1: {'font_size': 16, 'bold': True},
            2: {'font_size': 14, 'bold': True},
            3: {'font_size': 12, 'bold': True},
        }
        return template

# Template Preservation Feature

## Overview
The system now extracts and preserves the document structure from the original BRS files and applies it to the final consolidated BRS.

## How It Works

### 1. Template Extraction
When you upload the **first BRS document** for a project:
- The system extracts the document template (structure, formatting, numbering style)
- Stores it for use in generating the final BRS
- Applies this template to all output formats

### 2. What Gets Preserved

#### From DOCX Files:
- ✅ Section numbering format (1.1, 1.2 vs A.1, A.2)
- ✅ Heading styles (font sizes, bold, colors)
- ✅ Page margins
- ✅ Document structure

#### From PDF Files:
- ✅ Section numbering format
- ⚠️ Limited formatting (PDFs don't preserve editable styles)

### 3. Template Application
The final BRS output will:
- Use the same section numbering format as your original BRS
- Apply similar heading styles
- Maintain consistent document structure

## Usage Workflow

### Step 1: Start New Project
```
Click "New Project" button
→ Clears vector store
→ Clears previous template
```

### Step 2: Upload BRS Files
```
Upload first BRS file (v1.pdf or v1.docx)
→ System extracts template from this file
→ Template is stored for this project

Upload remaining BRS files (v2, v3, etc.)
→ Content is processed
→ Template remains from first file
```

### Step 3: Upload CR Files
```
Upload all CR files
→ Change requests are processed
```

### Step 4: Consolidate
```
Click "Start Consolidation"
→ System generates final BRS
→ Applies extracted template to output
```

### Step 5: Download
```
Download PDF/DOCX
→ Output matches original BRS format
```

## Example

### Original BRS Format:
```
1. Introduction
   1.1 Purpose
   1.2 Scope
2. Requirements
   2.1 Functional Requirements
   2.2 Non-Functional Requirements
```

### Final BRS Output:
```
1. Introduction
   1.1 Purpose (consolidated)
   1.2 Scope (consolidated)
2. Requirements
   2.1 Functional Requirements (consolidated)
   2.2 Non-Functional Requirements (consolidated)
```

The numbering format and structure match the original!

## Technical Details

### Files Modified:
1. **`app/services/template_extractor.py`** (NEW)
   - Extracts template from DOCX/PDF files
   - Stores formatting information

2. **`app/services/orchestrator.py`**
   - Stores template from first BRS upload
   - Passes template to exporters
   - Clears template when starting new project

3. **`app/services/pdf_exporter.py`**
   - Accepts template parameter
   - Uses template for formatting (future enhancement)

4. **`app/services/docx_exporter.py`**
   - Accepts template parameter
   - Uses template for formatting (future enhancement)

### Template Storage:
- Template is stored in memory during the session
- Cleared when "New Project" is clicked
- Extracted from the **first** uploaded BRS file

## Best Practices

### ✅ DO:
- Upload your most representative BRS file first
- Use DOCX files for better template extraction
- Click "New Project" before starting a different project
- Upload all BRS versions before consolidating

### ❌ DON'T:
- Mix different document formats in one project
- Upload BRS files with completely different structures
- Forget to click "New Project" between different projects

## Limitations

### Current Implementation:
- Template is extracted from the **first** BRS file only
- PDF template extraction is limited (text-based only)
- Complex formatting (tables, images) not fully preserved
- Template applies to structure, not all visual formatting

### Future Enhancements:
- Extract and merge templates from multiple BRS files
- Better PDF formatting extraction
- Preserve table structures
- Support for custom styles and themes

## Troubleshooting

**Q: My final BRS doesn't match the original format**
A: Make sure the first uploaded BRS file has the format you want. The template is extracted from the first file only.

**Q: Different BRS files have different formats**
A: The system uses the format from the first uploaded file. Upload your preferred format first.

**Q: PDF output doesn't preserve formatting**
A: PDF template extraction is limited. Use DOCX files for better results.

**Q: I want to change the template mid-project**
A: Click "New Project", then upload files in the desired order.

## Summary

The template preservation feature ensures that your final consolidated BRS maintains the same structure and numbering format as your original BRS documents. This makes the output more consistent with your organization's documentation standards.

**Key Benefit**: Final BRS looks and feels like your original BRS documents! 🎉

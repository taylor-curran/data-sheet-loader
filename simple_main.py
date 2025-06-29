#!/usr/bin/env python3
"""
Simple PDF Header-Based Chunker
Extracts content from PDF datasheets and organizes it into files based on detected headers.
Uses only pdfplumber and standard libraries - no AI required.
"""

import os
import re
import json
import pdfplumber
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from prefect import flow, task


class PDFHeaderChunker:
    """Simple PDF processor that chunks content by detected headers."""
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.headers = []
        self.content_chunks = []
        
    def detect_headers(self, text: str) -> List[str]:
        """Detect headers in text using simple heuristics."""
        lines = text.split('\n')
        headers = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Header detection heuristics
            is_header = False
            
            # Check for section numbering (1.1, 2.3.1, etc.)
            if re.match(r'^\d+(\.\d+)*\.?\s+[A-Z]', line):
                is_header = True
            
            # Check for all caps headers (short lines)
            elif len(line) < 80 and line.isupper() and len(line.split()) > 1:
                is_header = True
            
            # Check for title case headers with specific patterns
            elif (len(line) < 60 and 
                  line.istitle() and 
                  not line.endswith('.') and
                  len(line.split()) > 1):
                is_header = True
            
            # Check for headers with specific keywords
            elif any(keyword in line.lower() for keyword in [
                'introduction', 'overview', 'specification', 'features',
                'description', 'operation', 'configuration', 'registers',
                'timing', 'electrical', 'mechanical', 'package'
            ]) and len(line) < 80:
                is_header = True
            
            if is_header:
                headers.append(line)
        
        return headers
    
    def extract_content_between_headers(self, text: str, headers: List[str]) -> List[Dict]:
        """Extract content between detected headers."""
        if not headers:
            return [{"header": "Main Content", "content": text}]
        
        chunks = []
        lines = text.split('\n')
        current_chunk = {"header": "Introduction", "content": ""}
        
        for line in lines:
            line_stripped = line.strip()
            
            # Check if this line is a header
            if line_stripped in headers:
                # Save current chunk if it has content
                if current_chunk["content"].strip():
                    chunks.append(current_chunk)
                
                # Start new chunk
                current_chunk = {"header": line_stripped, "content": ""}
            else:
                # Add line to current chunk
                current_chunk["content"] += line + '\n'
        
        # Add final chunk
        if current_chunk["content"].strip():
            chunks.append(current_chunk)
        
        return chunks
    
    def clean_filename(self, text: str) -> str:
        """Convert header text to clean filename."""
        # Remove section numbers
        text = re.sub(r'^\d+(\.\d+)*\.?\s*', '', text)
        
        # Convert to lowercase and replace spaces/special chars
        text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
        text = re.sub(r'\s+', '_', text.strip())
        text = text.lower()
        
        # Limit length
        if len(text) > 50:
            text = text[:50]
        
        return text or "section"
    
    def create_directory_structure(self, chunks: List[Dict]) -> Dict:
        """Create directory structure based on content chunks."""
        structure = {}
        
        for chunk in chunks:
            header = chunk["header"]
            content = chunk["content"]
            
            # Determine directory based on header content
            if any(keyword in header.lower() for keyword in ['register', 'configuration', 'control']):
                category = "registers"
            elif any(keyword in header.lower() for keyword in ['timing', 'electrical', 'specification']):
                category = "specifications"
            elif any(keyword in header.lower() for keyword in ['feature', 'overview', 'description']):
                category = "overview"
            elif any(keyword in header.lower() for keyword in ['operation', 'mode', 'function']):
                category = "operation"
            elif any(keyword in header.lower() for keyword in ['package', 'mechanical', 'pin']):
                category = "mechanical"
            else:
                category = "general"
            
            if category not in structure:
                structure[category] = []
            
            filename = self.clean_filename(header) + ".md"
            structure[category].append({
                "filename": filename,
                "header": header,
                "content": content.strip()
            })
        
        return structure
    
    def write_markdown_files(self, structure: Dict, pdf_name: str) -> None:
        """Write organized markdown files to disk."""
        # Create base output directory
        base_dir = self.output_dir / pdf_name.replace('.pdf', '')
        base_dir.mkdir(parents=True, exist_ok=True)
        
        # Write files organized by category
        for category, files in structure.items():
            category_dir = base_dir / category
            category_dir.mkdir(exist_ok=True)
            
            for file_info in files:
                file_path = category_dir / file_info["filename"]
                
                # Create markdown content
                content = f"# {file_info['header']}\n\n{file_info['content']}"
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"Created: {file_path}")
        
        # Create index file
        self.create_index_file(base_dir, structure)
    
    def create_index_file(self, base_dir: Path, structure: Dict) -> None:
        """Create an index file with the directory structure."""
        index_content = "# Datasheet Structure\n\n"
        index_content += "This document was automatically generated from a PDF datasheet.\n\n"
        
        for category, files in structure.items():
            index_content += f"## {category.title()}\n\n"
            for file_info in files:
                file_path = f"{category}/{file_info['filename']}"
                index_content += f"- [{file_info['header']}]({file_path})\n"
            index_content += "\n"
        
        with open(base_dir / "README.md", 'w', encoding='utf-8') as f:
            f.write(index_content)
        
        print(f"Created: {base_dir / 'README.md'}")
    
    def process_pdf(self, pdf_path: str, max_pages: Optional[int] = None) -> Dict:
        """Main processing function."""
        print(f"Processing PDF: {pdf_path}")
        
        all_text = ""
        all_headers = []
        
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            # Handle max_pages = None or -1 for entire file
            if max_pages is None or max_pages == -1:
                pages_to_process = total_pages
            else:
                pages_to_process = min(max_pages, total_pages)
            
            print(f"Processing {pages_to_process} of {total_pages} pages")
            
            for page_num, page in enumerate(pdf.pages[:pages_to_process]):
                if page_num % 10 == 0:
                    print(f"  Processing page {page_num + 1}...")
                
                text = page.extract_text()
                if text:
                    all_text += f"\n--- PAGE {page_num + 1} ---\n" + text
                    
                    # Extract headers from this page
                    page_headers = self.detect_headers(text)
                    all_headers.extend(page_headers)
        
        print(f"Detected {len(all_headers)} potential headers")
        
        # Remove duplicates while preserving order
        unique_headers = []
        seen = set()
        for header in all_headers:
            if header not in seen:
                unique_headers.append(header)
                seen.add(header)
        
        print(f"Found {len(unique_headers)} unique headers")
        
        # Extract content chunks
        chunks = self.extract_content_between_headers(all_text, unique_headers)
        print(f"Created {len(chunks)} content chunks")
        
        # Create directory structure
        structure = self.create_directory_structure(chunks)
        
        # Write files
        pdf_name = Path(pdf_path).name
        self.write_markdown_files(structure, pdf_name)
        
        return {
            "pdf_path": pdf_path,
            "total_pages": total_pages,
            "pages_processed": pages_to_process,
            "headers_found": len(unique_headers),
            "content_chunks": len(chunks),
            "structure": structure
        }


@task
def process_pdf_with_chunker(pdf_file_path: str, output_dir: str, max_pages: Optional[int] = None) -> Dict:
    """Task to process PDF with the header-based chunker"""
    # Check if PDF exists
    if not os.path.exists(pdf_file_path):
        print(f"PDF file not found: {pdf_file_path}")
        print("Please ensure the PDF file exists or update the PDF_FILE_PATH variable.")
        return {}
    
    # Create processor
    processor = PDFHeaderChunker(output_dir=output_dir)
    
    # Process PDF
    try:
        result = processor.process_pdf(pdf_file_path, max_pages=max_pages)
        
        print("\n" + "="*50)
        print("PROCESSING COMPLETE")
        print("="*50)
        print(f"PDF: {result['pdf_path']}")
        print(f"Pages processed: {result['pages_processed']}/{result['total_pages']}")
        print(f"Headers found: {result['headers_found']}")
        print(f"Content chunks: {result['content_chunks']}")
        print(f"Output directory: {output_dir}")
        
        # Show structure summary
        print("\nGenerated structure:")
        for category, files in result['structure'].items():
            print(f"  {category}/: {len(files)} files")
        
        return result
        
    except Exception as e:
        print(f"Error processing PDF: {e}")
        import traceback
        traceback.print_exc()
        return {}


@flow
def load_pdfs_plumber(pdf_file_path: str, output_dir: str = "output", max_pages: Optional[int] = None, debug_mode: bool = True):
    """Main flow to process PDF with simple header-based chunking
    
    Args:
        pdf_file_path (str): Path to the PDF file
        output_dir (str): Output directory for generated files
        max_pages (int or None): Number of pages to process. Use None or -1 for entire file
        debug_mode (bool): Whether to show detailed debug output
    """
    
    pages_desc = (
        "entire file"
        if (max_pages is None or max_pages == -1)
        else f"{max_pages} pages"
    )
    if debug_mode:
        print(f"Starting PDF processing: {pdf_file_path} ({pages_desc})")
        print(f"Output directory: {output_dir}")
    
    # Process PDF using the chunker task
    result = process_pdf_with_chunker(
        pdf_file_path=pdf_file_path,
        output_dir=output_dir,
        max_pages=max_pages
    )
    
    if debug_mode and result:
        print("PDF processing workflow completed successfully!")
    
    return result


if __name__ == "__main__":
    # Configuration
    PDF_FILE_PATH = "example_data_sheets/BST-BMP280-DS001-11.pdf"
    OUTPUT_DIR = "output"
    
    # Run the PDF processing
    # Use max_pages=None or max_pages=-1 to process entire file
    result = load_pdfs_plumber(
        pdf_file_path=PDF_FILE_PATH,
        output_dir=OUTPUT_DIR,
        max_pages=5,  # Process first 5 pages, use None for entire file
        debug_mode=True
    )

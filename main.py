# main.py

# -- phase 1: rough file tree structure generation

import json
import pdfplumber
from openai import OpenAI
from utils import print_section
from prefect import flow, task
from prefect.cache_policies import INPUTS, TASK_SOURCE
client = OpenAI()

@task
def extract_headers_and_summary(pdf_path, max_pages=5):
    """Extract headers and basic content summary using pdfplumber"""
    print_section("PDFPLUMBER EXTRACTION STARTING", f"Processing: {pdf_path}")
    
    headers = []
    content_summary = []
    
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"Total pages: {total_pages}")
        
        # Handle max_pages = None or -1 for entire file
        if max_pages is None or max_pages == -1:
            pages_to_process = pdf.pages
            print(f"Processing ALL {total_pages} pages")
        else:
            pages_to_process = pdf.pages[:max_pages]
            print(f"Processing first {min(max_pages, total_pages)} pages")
        
        for page_num, page in enumerate(pages_to_process):
            print(f"\nProcessing page {page_num + 1}...")
            
            text = page.extract_text()
            if text:
                lines = text.split('\n')
                
                # Simple header detection (lines that are short, uppercase, or numbered)
                for line in lines:
                    line = line.strip()
                    if line and (
                        len(line) < 50 and 
                        (line.isupper() or 
                         any(line.startswith(str(i)) for i in range(1, 20)) or
                         line.count('.') >= 2)  # Likely section numbering
                    ):
                        headers.append(f"Page {page_num + 1}: {line}")
                
                # Extract first few meaningful lines as summary
                meaningful_lines = [line.strip() for line in lines if len(line.strip()) > 20]
                if meaningful_lines:
                    content_summary.append(f"Page {page_num + 1}: {meaningful_lines[0][:100]}...")
    
    return headers, content_summary

@task(cache_policy=INPUTS + TASK_SOURCE)
def generate_initial_tree_structure(file_id: str, file_tree_prompt: str, debug_mode: bool = True):
    """Generate initial tree structure from PDF using OpenAI API.
    
    Args:
        file_id (str): OpenAI file ID for the uploaded PDF
        file_tree_prompt (str): Prompt for tree structure generation
        debug_mode (bool): Whether to show detailed debug output
        
    Returns:
        str: AI-generated tree structure
    """
    if debug_mode:
        print_section("OPENAI TREE GENERATION TASK", f"Processing file ID: {file_id}")
    
    response = client.responses.create(
        model="gpt-4.1",
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_file",
                        "file_id": file_id,
                    },
                    {
                        "type": "input_text",
                        "text": file_tree_prompt,
                    },
                ],
            }
        ],
    )
    
    ai_tree_structure = response.output_text
    if debug_mode:
        print_section("OPENAI TREE STRUCTURE RESULT", ai_tree_structure)
    
    return ai_tree_structure

@task(cache_policy=INPUTS + TASK_SOURCE)
def refine_tree_structure(ai_structure: str, headers: list, debug_mode: bool = True):
    """Refine tree structure based on AI structure and extracted headers.
    
    Args:
        ai_structure (str): Initial AI-generated structure
        headers (list): List of extracted headers from PDF
        debug_mode (bool): Whether to show detailed debug output
        
    Returns:
        str: Refined tree structure
    """
    if debug_mode:
        print_section("STRUCTURE REFINEMENT TASK", "Refining structure based on headers...")
    
    refine_prompt = f"""Based on the AI-generated structure and the extracted headers, suggest improvements.

AI Structure:
{ai_structure}

Extracted Headers:
{chr(10).join(headers[:20])}  # First 20 headers

Provide a refined JSON structure that combines the best of both approaches."""
    
    refinement_response = client.responses.create(
        model="gpt-4.1",
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": refine_prompt,
                    },
                ],
            }
        ],
    )
    
    refined_structure = refinement_response.output_text
    if debug_mode:
        print_section("FINAL REFINED STRUCTURE", refined_structure)
    
    return refined_structure

@flow
def load_pdf(pdf_file_path, max_pages=5, debug_mode=True):
    """Main function to process PDF and generate file tree structure
    
    Args:
        pdf_file_path (str): Path to the PDF file
        max_pages (int or None): Number of pages to process. Use None or -1 for entire file
        debug_mode (bool): Whether to show detailed debug output
    """
    
    pages_desc = "entire file" if (max_pages is None or max_pages == -1) else f"{max_pages} pages"
    if debug_mode:
        print_section("STARTING PDF PROCESSING", f"File: {pdf_file_path}\nProcessing: {pages_desc}")
    
    # Step 1: Enhanced tree generation prompt
    file_tree_prompt = """Analyze this datasheet and create a simple directory/file structure for organizing its content.

Return a JSON structure with file and directory names that would organize this datasheet's content logically.
Keep names short and descriptive. Focus on major sections like overview, specifications, pinout, registers, etc.

Format as valid JSON with nested structure showing directories and files.
Example format:
{
  "overview": {
    "description.md": null,
    "features.md": null
  },
  "specifications": {
    "electrical.md": null,
    "mechanical.md": null
  }
}"""

    if debug_mode:
        print_section("STEP 1: FILE UPLOAD", "Uploading PDF to OpenAI...")

    # Upload file to OpenAI
    file = client.files.create(
        file=open(pdf_file_path, "rb"), purpose="user_data"
    )

    if debug_mode:
        print(f"File ID: {file.id}")

    # Step 1: Generate initial tree structure (cached task)
    ai_tree_structure = generate_initial_tree_structure(
        file_id=file.id,
        file_tree_prompt=file_tree_prompt,
        debug_mode=debug_mode
    )

    # Step 2: Extract headers and content using pdfplumber
    headers, content_summary = extract_headers_and_summary(pdf_file_path, max_pages)

    if debug_mode:
        print_section("STEP 2: PDFPLUMBER HEADERS", "\n".join(headers))
        print_section("STEP 2: PDFPLUMBER CONTENT SUMMARY", "\n".join(content_summary))

    # Step 3: Refine structure (cached task)
    refined_structure = refine_tree_structure(
        ai_structure=ai_tree_structure,
        headers=headers,
        debug_mode=debug_mode
    )

    if debug_mode:
        print_section("PROCESS COMPLETE", "Tree generation and header extraction finished!")
    
    return {
        "ai_structure": ai_tree_structure,
        "headers": headers,
        "content_summary": content_summary,
        "refined_structure": refined_structure
    }

if __name__ == "__main__":
    # Configuration
    PDF_FILE_PATH = "example_data_sheets/BST-BMP280-DS001-11.pdf"
    
    # Run the PDF processing
    # Use max_pages=None or max_pages=-1 to process entire file
    result = load_pdf(PDF_FILE_PATH, max_pages=5, debug_mode=True)

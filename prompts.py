# prompts.py
# Contains all prompts used for OpenAI API calls


def get_file_tree_prompt():
    """Returns the prompt for generating initial file tree structure"""
    return """
    Analyze this datasheet and create a comprehensive directory/file structure for organizing its content.

    CRITICAL REQUIREMENTS:
    - Use HIGHLY DESCRIPTIVE and SPECIFIC file names - err on the side of long, descriptive names
    - Break up ANY section that might be long into multiple smaller, focused files
    - Each file should contain only ONE specific topic or concept
    - If a section covers multiple topics, create separate files for each topic
    - Create deep directory structures with logical groupings

    Return a JSON structure with file and directory names that organize this datasheet's content.
    Focus on major sections like overview, specifications, pinout, registers, operation modes, etc.
    For each major section, think about what sub-topics exist and create separate files for each.

    Format as valid JSON with nested structure showing directories and files.
    """


def get_refinement_prompt(ai_structure: str, headers: list, content_summary: list):
    """Returns the prompt for refining the file tree structure

    Args:
        ai_structure (str): The initial AI-generated structure
        headers (list): List of extracted headers from PDF
        content_summary (list): List of content summaries from PDF pages
    """
    return f"""Based on the AI-generated structure and the extracted PDF content, create an IMPROVED and MORE GRANULAR file structure.

CRITICAL REQUIREMENTS:
- Use HIGHLY DESCRIPTIVE and SPECIFIC file names - err on the side of long, descriptive names
- Break up ANY section that might be long into multiple smaller, focused files
- Each file should contain only ONE specific topic or concept
- Use the extracted headers and content to identify specific topics that need separate files
- Create deeper directory structures with more subdirectories for better organization

AI-GENERATED STRUCTURE:
{ai_structure}

EXTRACTED HEADERS FROM PDF:
{chr(10).join(headers)}  # All extracted headers

CONTENT SUMMARIES FROM PDF PAGES:
{chr(10).join(content_summary)}  # Content summaries from each page

REFINEMENT GUIDELINES:
1. Look at the extracted headers and create individual files for each distinct topic mentioned
2. Use the content summaries to understand what specific information is covered
3. If headers mention specific registers, measurements, modes, or procedures, create separate files for each
4. Break down any broad categories into multiple specific files
5. Use the exact terminology from the headers and content in your filenames
6. Create deeper directory structures with more subdirectories for better organization

Return ONLY valid JSON with the refined structure. Remember: MORE SPECIFIC FILES with DESCRIPTIVE NAMES is always better."""

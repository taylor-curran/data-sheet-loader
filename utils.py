from prefect.artifacts import create_markdown_artifact, create_table_artifact
import json


def print_section(title, content):
    """Pretty print debug sections"""
    print(f"\n{'=' * 50}")
    print(f" {title}")
    print(f"{'=' * 50}")
    print(content)
    print(f"{'=' * 50}\n")


def create_json_structure_artifact(
    json_content: str, title: str, key: str, description: str
):
    """Create a markdown artifact for JSON structure with proper formatting"""
    # Format the JSON content for better readability
    breakpoint()
    try:
        # Parse and re-format the JSON for consistent indentation
        parsed_json = json.loads(json_content)
        formatted_json = json.dumps(parsed_json, indent=2)
    except json.JSONDecodeError:
        # If it's not valid JSON, use as-is
        formatted_json = json_content

    markdown_content = f"""# {title}

```json
{formatted_json}
```

## Summary
{description}
"""

    create_markdown_artifact(
        key=key,
        markdown=markdown_content,
        description=f"{title} - Generated JSON structure for datasheet organization",
    )


def create_headers_table_artifact(headers: list, key: str):
    """Create a table artifact for extracted headers"""
    if not headers:
        return

    # Convert headers list to table format
    table_data = []
    for i, header in enumerate(headers, 1):
        table_data.append({"#": i, "Header Text": header, "Length": len(header)})

    create_table_artifact(
        key=key,
        table=table_data,
        description="# Extracted Headers from PDF\n\nHeaders extracted using pdfplumber from the datasheet PDF. These provide insight into the document structure and content organization.",
    )


def create_content_summary_artifact(content_summary: list, key: str):
    """Create a table artifact for content summary"""
    if not content_summary:
        return

    # Convert content summary to table format
    table_data = []
    for i, summary in enumerate(content_summary, 1):
        # Extract page info if available
        if summary.startswith("Page "):
            parts = summary.split(": ", 1)
            page_info = parts[0] if len(parts) > 1 else f"Page {i}"
            content = parts[1] if len(parts) > 1 else summary
        else:
            page_info = f"Page {i}"
            content = summary

        table_data.append(
            {
                "Page": page_info,
                "Content Preview": content[:100] + "..."
                if len(content) > 100
                else content,
                "Full Length": len(content),
            }
        )

    create_table_artifact(
        key=key,
        table=table_data,
        description="# Content Summary from PDF\n\nContent summaries extracted from each page of the datasheet PDF using pdfplumber. This provides an overview of the content on each page.",
    )


def create_processing_summary_artifact(
    pdf_path: str, total_pages: int, processed_pages: int, key: str
):
    """Create a summary artifact for the processing results"""

    processing_info = f"""# PDF Processing Summary

## File Information
- **File Path**: `{pdf_path}`
- **Total Pages**: {total_pages}
- **Pages Processed**: {processed_pages}
- **Processing Coverage**: {(processed_pages / total_pages) * 100:.1f}%

## Processing Status
✅ PDF successfully processed  
✅ Headers extracted using pdfplumber  
✅ AI structure generated using OpenAI  
✅ Structure refined based on extracted content  

## Next Steps
The generated structure can now be used to organize the datasheet content into a logical directory/file hierarchy for AI consumption.
"""

    create_markdown_artifact(
        key=key,
        markdown=processing_info,
        description="Processing summary for the PDF datasheet extraction workflow",
    )

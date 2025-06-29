# main.py
"""Just a quick example, this doesn't work consistently and will probably fall apart with larger datasheets"""

from openai import OpenAI

client = OpenAI()

file_tree_prompt = """
I want to break this data sheet into a nested file/directory tree.

It should be structured as an information tree, with global information at the top level and more specific information about sub-components organized into subdirectories and files under their relevant parent directories.

Naming of files and directories is important: names must be uniform, informative, and reflect the content as clearly as possible. Longer names are ok.

Each file should contain no more than 1-2 sections to keep individual files small and very quick to read.

## Output Format
Represent the resulting tree structure using a JSON object, where:
- Each directory is represented as an object with its name as the key and its contents (files or subdirectories) as the value.
- Each file is represented by its name as the key and its content (section names or brief summary) as the value. Example:
"""


file = client.files.create(
    file=open("BST-BMP280-DS001-11.pdf", "rb"), purpose="user_data"
)

response = client.responses.create(
    model="gpt-4.1",
    input=[
        {
            "role": "user",
            "content": [
                {
                    "type": "input_file",
                    "file_id": file.id,
                },
                {
                    "type": "input_text",
                    "text": file_tree_prompt,
                },
            ],
        }
    ],
)

print(response.output_text)

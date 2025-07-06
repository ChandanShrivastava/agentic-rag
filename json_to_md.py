import os
import json
import argparse

def convert_json_to_markdown(json_data, indent=0):
    """
    Converts a JSON object or array into a Markdown formatted string,
    using proper subheading levels and spacing for better readability
    and LLM understanding. Skips the 'full_description' and 'claims' fields.
    """
    markdown_output = []
    # Indentation for nested items
    indent_str = "    " * indent
    # Fields to skip
    FIELDS_TO_SKIP = {"full_description", "claims", "background"} # Using a set for efficient lookup

    if isinstance(json_data, dict):
        for key, value in json_data.items():
            # Skip the specified fields
            if key in FIELDS_TO_SKIP:
                continue

            # Determine the heading level, capping at H6
            heading_level = min(6, indent + 1)
            heading_prefix = "#" * heading_level

            # Add a newline for spacing before each new section/key-value pair
            if indent == 0 or (indent > 0 and isinstance(value, (dict, list))):
                markdown_output.append("\n") # Extra newline for spacing sections

            # Use subheadings for nested objects/arrays, or bold for simple key-values
            if isinstance(value, (dict, list)):
                markdown_output.append(f"{indent_str}{heading_prefix} {key.replace('_', ' ').title()}\n")
                # Recurse for nested dictionaries or lists
                markdown_output.append(convert_json_to_markdown(value, indent + 1))
            else:
                # For simple key-value pairs, use bold key and its value
                markdown_output.append(f"{indent_str}**{key.replace('_', ' ').title()}:** {value}\n")

    elif isinstance(json_data, list):
        # Add a newline for spacing before a new list section
        if indent > 0:
            markdown_output.append("\n")

        for i, item in enumerate(json_data):
            # For each item in the list, use a list item prefix
            markdown_output.append(f"{indent_str}- ")
            if isinstance(item, (dict, list)):
                # If the list item is a nested object or list, recurse
                # No extra newline for the current list item, it's handled inside recursion
                markdown_output.append(convert_json_to_markdown(item, indent + 1))
            else:
                # For simple list items
                markdown_output.append(f"{item}\n")

    else:
        # For simple values that might be passed directly (e.g., from a list)
        markdown_output.append(f"{json_data}\n")

    return "".join(markdown_output)

def main():
    """
    Main function to parse arguments, read JSON files, and convert them to Markdown,
    only if the 'decision' field in the JSON is 'ACCEPTED' or 'REJECTED'.
    """
    parser = argparse.ArgumentParser(
        description="Convert JSON files to Markdown files."
    )
    parser.add_argument(
        "max_files",
        type=int,
        help="Maximum number of JSON files to process."
    )
    parser.add_argument(
        "input_folder",
        type=str,
        help="Path to the folder containing JSON files."
    )
    parser.add_argument(
        "output_folder",
        type=str,
        help="Path to the folder where Markdown files will be saved."
    )

    args = parser.parse_args()

    input_path = os.path.abspath(args.input_folder)
    output_path = os.path.abspath(args.output_folder)
    max_files_to_process = args.max_files

    # Create output folder if it doesn't exist
    os.makedirs(output_path, exist_ok=True)

    processed_count = 0
    skipped_count = 0
    print(f"Processing JSON files from: {input_path}")
    print(f"Saving Markdown files to: {output_path}")
    print(f"Maximum files to process: {max_files_to_process}")

    try:
        # List all files in the input folder
        files = [f for f in os.listdir(input_path) if f.endswith('.json')]
        files.sort() # Ensure consistent order for processing

        for filename in files:
            if processed_count >= max_files_to_process:
                print(f"Reached maximum file limit of {max_files_to_process}. Stopping.")
                break

            json_filepath = os.path.join(input_path, filename)
            markdown_filename = os.path.splitext(filename)[0] + ".md"
            markdown_filepath = os.path.join(output_path, markdown_filename)

            print(f"Attempting to process '{filename}'...")

            try:
                with open(json_filepath, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)

                # Check the 'decision' field
                decision = json_data.get('decision')
                if decision in ["ACCEPTED", "REJECTED"]:
                    markdown_content = convert_json_to_markdown(json_data)

                    with open(markdown_filepath, 'w', encoding='utf-8') as f:
                        f.write(markdown_content)

                    processed_count += 1
                    print(f"Successfully converted '{filename}' (Decision: {decision}).")
                else:
                    skipped_count += 1
                    print(f"Skipping '{filename}' due to decision '{decision}'. Only 'ACCEPTED' or 'REJECTED' are processed.")

            except json.JSONDecodeError:
                print(f"Error: Could not decode JSON from '{filename}'. Skipping.")
            except FileNotFoundError:
                print(f"Error: File '{filename}' not found. Skipping.")
            except Exception as e:
                print(f"An unexpected error occurred while processing '{filename}': {e}. Skipping.")

    except FileNotFoundError:
        print(f"Error: Input folder '{input_path}' not found.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    print(f"\nFinished processing. Converted {processed_count} JSON files to Markdown. Skipped {skipped_count} files.")

if __name__ == "__main__":
    main()
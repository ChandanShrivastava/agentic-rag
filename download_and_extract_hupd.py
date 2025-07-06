import os
import tarfile
import argparse # Import argparse for command-line arguments
from huggingface_hub import hf_hub_download

def download_and_extract_hupd(repo_id: str, filename: str, download_dir: str, extract_dir: str):
    """
    Downloads a file from Hugging Face Hub and extracts it if it's a tar.gz.

    Args:
        repo_id (str): The Hugging Face repository ID (e.g., "HUPD/hupd").
        filename (str): The specific file to download (e.g., "data/2018.tar.gz").
        download_dir (str): Directory to save the downloaded file.
        extract_dir (str): Directory to extract the contents.
    """
    # Create directories if they don't exist
    os.makedirs(download_dir, exist_ok=True)
    os.makedirs(extract_dir, exist_ok=True) 

    print(f"Downloading {filename} from {repo_id} using huggingface_hub...")
    try:
        downloaded_filepath = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            cache_dir=download_dir,
            repo_type="dataset"
        )
        print(f"File downloaded to: {downloaded_filepath}")
    except Exception as e:
        print(f"Error downloading file from Hugging Face Hub: {e}")
        return

    print(f"Extracting {downloaded_filepath} to {extract_dir}...")
    try:
        with tarfile.open(downloaded_filepath, "r:gz") as tar:
            tar.extractall(path=extract_dir) # Extract into the base directory
        print("Extraction complete.")
        
        # Construct the expected path for the extracted JSON files
        # This assumes the tarball contains a top-level folder named after the year (e.g., "2018/")
        year_folder_name = filename.split('/')[1].split('.')[0]
        final_json_path = os.path.join(extract_dir, year_folder_name)
        print(f"JSON files should now be in: {final_json_path}")
        
        # Optional: Verify by listing some contents
        if os.path.exists(final_json_path) and os.listdir(final_json_path):
            print(f"First 5 items in {final_json_path}: {os.listdir(final_json_path)[:5]}")
        else:
            print(f"Warning: Expected directory {final_json_path} either doesn't exist or is empty after extraction.")

    except tarfile.ReadError as e:
        print(f"Error: Could not read tar.gz file. It might be corrupted: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during extraction: {e}")


if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Download and extract HUPD dataset for a specific year.")
    parser.add_argument(
        "year", 
        type=str, 
        nargs='?', # Makes the argument optional
        default="2018", # Default value if no argument is provided
        help="The year of the HUPD dataset to download (e.g., '2018', '2019'). Defaults to 2018."
    )
    args = parser.parse_args()

    HUGGINGFACE_REPO_ID = "HUPD/hupd"
    
    # Use the year from the command-line argument
    year_to_download = args.year 
    TAR_FILENAME = f"data/{year_to_download}.tar.gz"

    DOWNLOAD_CACHE_DIR = "hf_cache"
    # Extract directly into 'hupd_extracted'. The tarball itself will create the year subdirectory.
    EXTRACT_DIR = "hupd_extracted" 

    download_and_extract_hupd(HUGGINGFACE_REPO_ID, TAR_FILENAME, DOWNLOAD_CACHE_DIR, EXTRACT_DIR)
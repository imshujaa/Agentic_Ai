import os
import shutil
from tqdm import tqdm
import tarfile  # The correct library for reading .tar.xz archives

from whoosh.index import create_in, open_dir 
from whoosh.fields import Schema, TEXT, ID
from whoosh.analysis import StandardAnalyzer

# --- Configuration ---
INDEX_DIR = "indexdir"
# This path now correctly points to the nested folder structure you described
DATA_FOLDER = os.path.join("openwebtext", "openwebtext")

def build_the_index():
    """
    A standalone script to reliably build the search index from your local
    'openwebtext/openwebtext' folder containing .xz archives.
    This should be run only once.
    """
    print("--- Starting Index Creation Script (for local .tar.xz archives) ---")

    # 1. Verify that your local data folder exists
    if not os.path.exists(DATA_FOLDER):
        print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print(f"FATAL: Your local data folder was not found at the path: '{DATA_FOLDER}'")
        print("Please ensure your folder structure is 'openwebtext/openwebtext/<files.xz>'")
        print(f"relative to where you are running this script.")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        return

    # 2. Clean up any old, broken index
    if os.path.exists(INDEX_DIR):
        print(f"Found an old index directory at '{INDEX_DIR}'. Deleting it.")
        shutil.rmtree(INDEX_DIR)
    
    # 3. Indexing ---
    print("\nCreating new index...")
    os.makedirs(INDEX_DIR, exist_ok=True)
    analyzer = StandardAnalyzer()
    schema = Schema(path=ID(unique=True, stored=True), 
                    content=TEXT(stored=True, analyzer=analyzer))
    ix = create_in(INDEX_DIR, schema)
    
    # Use a simple writer for maximum reliability
    writer = ix.writer()

    print("Indexing documents from your local folder...")
    doc_count = 0
    
    # Find all .xz files within the specified data folder
    xz_files = [os.path.join(root, file) for root, _, files in os.walk(DATA_FOLDER) for file in files if file.endswith('.xz')]

    if not xz_files:
        print(f"\nFATAL ERROR: No .xz files were found in your '{DATA_FOLDER}' directory.")
        return

    for filepath in tqdm(xz_files, desc="Processing Archives"):
        try:
            # Open the file as a tar archive compressed with xz
            with tarfile.open(filepath, "r:xz") as tar:
                for member in tar.getmembers():
                    # Check if the member is a file (and not a directory)
                    if member.isfile():
                        extracted_file = tar.extractfile(member)
                        if extracted_file:
                            # Read the content of the file-in-the-archive
                            content = extracted_file.read().decode('utf-8', errors='ignore')
                            if content:
                                # Create a unique path for each document
                                doc_path = f"{os.path.basename(filepath)}/{member.name}"
                                writer.add_document(path=doc_path, content=content)
                                doc_count += 1
        except Exception as e:
            # This will catch files that are not valid tar.xz archives
            print(f"\nSkipping file {filepath} due to an error: {e}")

    print(f"\nCommitting {doc_count} documents to the index...")
    writer.commit()
    
    # 4. Final Verification ---
    ix_verify = open_dir(INDEX_DIR)
    with ix_verify.searcher() as s:
        doc_total = s.doc_count()
        if doc_total > 0:
            print("\n====================================================================")
            print(f"SUCCESS! The index was created and contains {doc_total} documents.")
            print("You can now run the main 'app.py' to start the web server.")
            print("====================================================================")
        else:
            print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            print("FATAL ERROR: Indexing completed but resulted in an empty index.")
            print("This likely means the .xz files are not in the expected .tar.xz format.")
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

if __name__ == '__main__':
    build_the_index()


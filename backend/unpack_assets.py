import os
import zipfile
import glob

def unpack_all():
    """Unpack all pre-indexed assets during server startup on Render."""
    
    # 1. Unpack SQLite database
    db_path = "bonequest.db"
    db_zip = "packed_db.zip"
    
    if os.path.exists(db_zip) and not os.path.exists(db_path):
        print(f"[unpack] Found {db_zip}, extracting database...", flush=True)
        try:
            with zipfile.ZipFile(db_zip, 'r') as zipf:
                zipf.extractall()
            print("[unpack] Database extracted successfully.")
        except Exception as e:
            print(f"[unpack] Failed to extract database: {e}")
    
    # 2. Unpack PDF uploads
    upload_zips = glob.glob("packed_uploads_*.zip")
    if upload_zips:
        upload_dir = os.path.join("data", "uploads")
        
        # Determine if extraction is needed (Render ephemeral filesystem will be empty)
        needs_extract = True
        if os.path.exists(upload_dir):
            # If there's already multiple PDFs, we don't need to re-extract on every hot-reload
            pdf_count = len([f for f in os.listdir(upload_dir) if f.endswith('.pdf')])
            if pdf_count > 5:
                needs_extract = False
                
        if needs_extract:
            print("[unpack] Ephemeral state detected. Unpacking upload chunks...", flush=True)
            os.makedirs("data", exist_ok=True)
            for uzip in sorted(upload_zips):
                try:
                    print(f"   -> Extracting {uzip}...", flush=True)
                    with zipfile.ZipFile(uzip, 'r') as zipf:
                        zipf.extractall("data")  # extract into data/ because internal arcname is uploads/...
                except Exception as e:
                    print(f"[unpack] Failed to extract {uzip}: {e}")
            print("[unpack] Uploads extracted successfully.")

if __name__ == "__main__":
    unpack_all()

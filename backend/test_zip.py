import zipfile
import os

db_path = "bonequest.db"
zip_path = "bonequest.db.zip"

if not os.path.exists(db_path):
    print(f"{db_path} not found")
else:
    print("Zipping database...")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
        zipf.write(db_path)
    
    zip_size = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"Compressed size: {zip_size:.2f} MB")

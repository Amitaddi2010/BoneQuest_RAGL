import os
import zipfile

def pack_assets():
    print("📦 Packing BoneQuest Assets locally for GitHub...", flush=True)
    
    # 1. Pack database
    db_path = "bonequest.db"
    db_zip = "packed_db.zip"
    if os.path.exists(db_path):
        print(f"-> Packing database: {db_path} -> {db_zip}...")
        with zipfile.ZipFile(db_zip, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
            zipf.write(db_path)
        print(f"   [Done] Size: {os.path.getsize(db_zip) / (1024*1024):.2f} MB")
    
    # 2. Pack uploads into max 80MB chunks
    uploads_dir = os.path.join("data", "uploads")
    if not os.path.exists(uploads_dir):
        print("-> No uploads directory found, skipping.")
        return
        
    MAX_SIZE_MB = 80
    MAX_BYTES = MAX_SIZE_MB * 1024 * 1024
    
    current_zip_idx = 1
    current_zip_size = 0
    current_zip_name = f"packed_uploads_{current_zip_idx}.zip"
    current_zip_obj = zipfile.ZipFile(current_zip_name, 'w', zipfile.ZIP_DEFLATED)
    
    files_packed = 0
    
    print("-> Packing uploads folder...", flush=True)
    for root, dirs, files in os.walk(uploads_dir):
        for file in files:
            file_path = os.path.join(root, file)
            file_size = os.path.getsize(file_path)
            
            # Split if threshold exceeded
            if current_zip_size + file_size > MAX_BYTES and current_zip_size > 0:
                current_zip_obj.close()
                print(f"   Created chunk: {current_zip_name} ({current_zip_size / (1024*1024):.2f} MB)")
                
                current_zip_idx += 1
                current_zip_size = 0
                current_zip_name = f"packed_uploads_{current_zip_idx}.zip"
                current_zip_obj = zipfile.ZipFile(current_zip_name, 'w', zipfile.ZIP_DEFLATED)
            
            # Archive name keeps the relative 'uploads/...' structure
            arcname = os.path.relpath(file_path, "data")
            current_zip_obj.write(file_path, arcname)
            current_zip_size += file_size
            files_packed += 1
            
    current_zip_obj.close()
    
    if current_zip_size == 0:
        if os.path.exists(current_zip_name):
            os.remove(current_zip_name)
    else:
        print(f"   Created chunk: {current_zip_name} ({current_zip_size / (1024*1024):.2f} MB)")
        
    print(f"-> Packed {files_packed} upload files across {current_zip_idx} chunks.")
    print("✅ All assets packed! You can now commit and push to Git.")

if __name__ == "__main__":
    pack_assets()


"""
Cloud Deployment Packager
- Packages bot code into a deployable ZIP
- Excludes secrets, logs, results, data
"""
import os
import shutil
import zipfile
from datetime import datetime

EXCLUDE_DIRS = ['venv', '__pycache__', '.git', 'logs', 'results', 'data', '.idea', '.vscode']
EXCLUDE_FILES = ['.env', '.DS_Store']

def create_deployment_package():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"polymarket_bot_deploy_{timestamp}.zip"
    
    print(f"Packaging for Cloud Deployment: {zip_filename}...")
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk('.'):
            # Exclude dirs
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            
            for file in files:
                if file in EXCLUDE_FILES:
                    continue
                if file.endswith('.zip'):
                    continue
                    
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, '.')
                zipf.write(file_path, arcname)
                
    print(f"[OK] Package created: {zip_filename}")
    print("Upload this ZIP to AWS EC2, Lambda, or GCP.")
    print("Remember to set environment variables on the cloud instance manually!")

if __name__ == "__main__":
    create_deployment_package()


"""
Secrets Management Setup
- Checks for .env file
- Validates required keys
- Creates .env.template if missing
- Warns about unprotected keys
"""
import os
import shutil

REQUIRED_KEYS = [
    "PRIVATE_KEY",
    "CLOB_API_KEY",
    "CLOB_API_SECRET",
    "CLOB_PASSPHRASE",
    "LIVE_TRADING"
]

def setup_secrets():
    print("Checking Security Configuration...")
    
    # 1. Check .gitignore
    gitignore_path = ".gitignore"
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r") as f:
            content = f.read()
            if ".env" not in content:
                print("[WARNING] .env is NOT in .gitignore! Fix this immediately.")
                with open(gitignore_path, "a") as f_append:
                    f_append.write("\n.env\n")
                print("Added .env to .gitignore")
            else:
                print("[OK] .env is gitignored.")
    else:
        print("[WARNING] No .gitignore found. Creating one.")
        with open(gitignore_path, "w") as f:
            f.write(".env\n__pycache__/\n*.pyc\nlogs/\nresults/\ndata/\n")
            
    # 2. Check .env
    env_path = ".env"
    template_path = ".env.template"
    
    if not os.path.exists(env_path):
        print("[INFO] .env not found. Creating from template...")
        with open(env_path, "w") as f:
            for key in REQUIRED_KEYS:
                f.write(f"{key}=\n")
        print("Created empty .env")
        
    # Validation
    missing_keys = []
    with open(env_path, "r") as f:
        content = f.read()
        for key in REQUIRED_KEYS:
            if key not in content:
                missing_keys.append(key)
    
    if missing_keys:
        print(f"[ERROR] Missing keys in .env: {missing_keys}")
    else:
        print("[OK] All required keys present in .env")
        
    # 3. Create Template (safe to share)
    with open(template_path, "w") as f:
        for key in REQUIRED_KEYS:
            f.write(f"{key}=<YOUR_{key}>\n")
    print(f"[OK] Updated {template_path}")

    print("\nSecurity Check Complete.")

if __name__ == "__main__":
    setup_secrets()

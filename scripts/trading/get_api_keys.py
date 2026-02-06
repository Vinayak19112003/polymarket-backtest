"""
Generate Polymarket CLOB API Credentials

Run: python scripts/get_api_keys.py

You will be prompted for your private key.
"""
import os
import sys

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from py_clob_client.client import ClobClient
except ImportError:
    print("ERROR: py-clob-client not installed!")
    sys.exit(1)

def main():
    print("=" * 50)
    print("  POLYMARKET CLOB API KEY GENERATOR")
    print("=" * 50)
    print()
    
    private_key = input("Enter your MetaMask private key (starts with 0x): ").strip()
    
    # Handle possible multiline paste
    if len(private_key) < 60: 
        # try reading another line if user pasted with newline
        try:
            part2 = input().strip()
            private_key += part2
        except:
            pass

    if not private_key.startswith("0x"):
        private_key = "0x" + private_key
    
    print(f"\nKey Length: {len(private_key)} (Expected: 66)")
    
    if len(private_key) != 66:
        print("ERROR: Private key should be 64 hex characters (+ 0x prefix)")
        print("Please ensure you copied the entire key.")
        sys.exit(1)
    
    print("\nConnecting to Polymarket CLOB API...")
    
    try:
        # Initialize client
        client = ClobClient(
            host="https://clob.polymarket.com",
            chain_id=137,
            key=private_key
        )
        
        print("Creating or retrieving API credentials...")
        try:
            # Try the modern method first
            creds = client.create_or_derive_api_key()
        except AttributeError:
            # Fallback for older versions or if method name differs
            try:
                creds = client.derive_api_key()
            except Exception as e:
                 print(f"derive_api_key failed: {e}")
                 print("Trying create_api_key...")
                 creds = client.create_api_key()

        print("\n" + "=" * 50)
        print("  YOUR API CREDENTIALS (SAVE THESE!)")
        print("=" * 50)
        print(f"\nCLOB_API_KEY={creds.api_key}")
        print(f"CLOB_API_SECRET={creds.api_secret}")
        print(f"CLOB_PASSPHRASE={creds.api_passphrase}")
        print()
        print("Step 1: Copy these values to your .env file")
        print("Step 2: Ensure your wallet has Polygon MATIC")
        print("Step 3: Ensure you have logged into Polymarket.com once to initialize account")
        print("=" * 50)
        
    except Exception as e:
        print(f"\nERROR: {e}")
        print("\nTroubleshooting:")
        print("1. Have you deposited USDC into Polymarket via the website?")
        print("2. Have you logged in at least once?")
        print("3. Does your wallet have MATIC (for gas)?")
        sys.exit(1)

if __name__ == "__main__":
    main()

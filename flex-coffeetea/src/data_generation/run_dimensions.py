import os
import subprocess
import sys

def main():
    print("="*60)
    print("STARTING DIMENSION GENERATION")
    print("="*60)
    
    script_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dimension")
    
    scripts = [
        "generate_store_profile.py",
        "generate_baverage_dimensions.py",
        "generate_food_retail_merch.py",
        "generate_hr_dimensions.py",
        "generate_minor_dimensions.py",
        "generate_missing_dimensions.py"
    ]
    
    for script_name in scripts:
        print(f"\n" + "="*40)
        print(f"---> Running: {script_name}")
        print("="*40)
        
        script_path = os.path.join(script_dir, script_name)
        
        if not os.path.exists(script_path):
            print(f"ERROR: {script_path} not found!")
            sys.exit(1)
            
        result = subprocess.run([sys.executable, script_path])
        if result.returncode != 0:
            print(f"\n[!] Error occurred while running {script_name}. Aborting.")
            sys.exit(1)
            
    print("\n" + "="*60)
    print("DIMENSION GENERATION COMPLETE")
    print("="*60)

if __name__ == "__main__":
    main()

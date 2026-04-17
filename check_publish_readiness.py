"""
Pre-Publishing Verification Script
Checks what files will be published to GitHub
"""
import os
from pathlib import Path
from pathlib import PurePath

# Files that SHOULD be published
SHOULD_INCLUDE = [
    "src/main.py",
    "src/detector.py",
    "src/roi_manager.py",
    "src/alert_system.py",
    "config/settings.yaml.example",
    "find_camera.py",
    "augment_train.py",
    "merge_datasets.py",
    "requirements.txt",
    "README.md",
    "LICENSE",
    ".gitignore",
    "PUBLISHING_GUIDE.md",
    "DETECTION_FIXES.md",
]

# Patterns that should NOT be published
SHOULD_EXCLUDE = [
    "*.pt",
    "*.pth",
    ".venv/",
    "__pycache__/",
    "wildlife_dataset/",
    "final_dataset/",
    "runs/",
    "data/logs/",
    "config/settings.yaml",  # Personal config
]

def check_project_readiness():
    print("=" * 60)
    print("🔍 GitHub Publishing Readiness Check")
    print("=" * 60)
    
    root = Path(__file__).parent
    issues = []
    warnings = []
    
    # Check essential files exist
    print("\n✅ Checking essential files...")
    for file in SHOULD_INCLUDE:
        if (root / file).exists():
            print(f"   ✓ {file}")
        else:
            print(f"   ✗ {file} - MISSING")
            issues.append(f"Missing file: {file}")
    
    # Check for files that should be excluded
    print("\n🚫 Checking for files that should NOT be published...")
    exclude_patterns = ["*.pt", "*.pth"]
    found_large = []
    
    for pattern in exclude_patterns:
        for file in root.glob(pattern):
            size_mb = file.stat().st_size / (1024 * 1024)
            found_large.append((file.name, size_mb))
            print(f"   ⚠️  {file.name} ({size_mb:.1f} MB) - Will be excluded by .gitignore")
    
    # Check directories
    print("\n📁 Checking directory structure...")
    exclude_dirs = [".venv", "wildlife_dataset", "final_dataset", "runs", "__pycache__"]
    for dir_name in exclude_dirs:
        dir_path = root / dir_name
        if dir_path.exists():
            print(f"   ⚠️  {dir_name}/ exists - Will be excluded by .gitignore")
        else:
            print(f"   ✓ {dir_name}/ not found (good)")
    
    # Check .gitignore exists
    print("\n📄 Checking .gitignore...")
    gitignore_path = root / ".gitignore"
    if gitignore_path.exists():
        print("   ✓ .gitignore found")
        with open(gitignore_path, 'r') as f:
            content = f.read()
            if "*.pt" in content:
                print("   ✓ .gitignore excludes model files")
            else:
                print("   ⚠️  .gitignore might not exclude .pt files")
                warnings.append(".gitignore may not exclude model files")
    else:
        print("   ✗ .gitignore MISSING")
        issues.append("Missing .gitignore file")
    
    # Check requirements.txt
    print("\n📦 Checking requirements.txt...")
    req_path = root / "requirements.txt"
    if req_path.exists():
        print("   ✓ requirements.txt found")
        with open(req_path, 'r') as f:
            lines = f.readlines()
            print(f"   ✓ {len(lines)} dependencies listed")
    else:
        print("   ✗ requirements.txt MISSING")
        issues.append("Missing requirements.txt")
    
    # Check README
    print("\n📖 Checking README.md...")
    readme_path = root / "README.md"
    if readme_path.exists():
        print("   ✓ README.md found")
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if "Installation" in content and "Usage" in content:
                print("   ✓ README contains installation and usage instructions")
            else:
                print("   ⚠️  README might be incomplete")
                warnings.append("README may need more details")
    else:
        print("   ✗ README.md MISSING")
        issues.append("Missing README.md")
    
    # Check LICENSE
    print("\n⚖️  Checking LICENSE...")
    license_path = root / "LICENSE"
    if license_path.exists():
        print("   ✓ LICENSE found")
    else:
        print("   ⚠️  LICENSE missing (recommended for open source)")
        warnings.append("Consider adding a LICENSE file")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Summary")
    print("=" * 60)
    
    if issues:
        print(f"\n❌ {len(issues)} issue(s) found:")
        for issue in issues:
            print(f"   - {issue}")
        print("\n⚠️  Please fix these before publishing!")
        return False
    else:
        print("\n✅ All essential files present!")
        
        if warnings:
            print(f"\n⚠️  {len(warnings)} warning(s):")
            for warning in warnings:
                print(f"   - {warning}")
        
        if found_large:
            print(f"\n📦 {len(found_large)} large file(s) will be excluded:")
            for name, size in found_large:
                print(f"   - {name} ({size:.1f} MB)")
        
        print("\n✅ Project is READY for GitHub publishing!")
        print("\n📤 Next steps:")
        print("   1. git init")
        print("   2. git add .")
        print("   3. git status  (review files)")
        print("   4. git commit -m 'Initial commit'")
        print("   5. Create repo on GitHub")
        print("   6. git push -u origin main")
        return True

if __name__ == "__main__":
    check_project_readiness()

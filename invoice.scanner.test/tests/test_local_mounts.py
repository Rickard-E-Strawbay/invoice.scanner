#!/usr/bin/env python3
"""
Test script to verify and list contents of mounted directories
"""

from pathlib import Path

MOUNTS = {
    "invoice.scanner.api": "/mounts/invoice.scanner.api",
    "invoice.scanner.cloud.functions": (
        "/mounts/invoice.scanner.cloud.functions"
    ),
}


def main():
    print("=" * 60)
    print("Testing Mount Directories")
    print("=" * 60)
    
    for name, path in MOUNTS.items():
        print(f"\n📁 {name}")
        print(f"   Path: {path}")
        
        mount_path = Path(path)
        
        if not mount_path.exists():
            print("   ❌ NOT FOUND - Directory does not exist")
            continue
        
        if not mount_path.is_dir():
            print("   ❌ NOT A DIRECTORY")
            continue
        
        print("   ✅ EXISTS")
        
        try:
            contents = list(mount_path.iterdir())
            if not contents:
                print("   (empty directory)")
            else:
                print(f"   Contents ({len(contents)} items):")
                for item in sorted(contents):
                    item_type = "📁" if item.is_dir() else "📄"
                    print(f"      {item_type} {item.name}")
        except PermissionError:
            print("   ❌ PERMISSION DENIED - Cannot read directory")
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

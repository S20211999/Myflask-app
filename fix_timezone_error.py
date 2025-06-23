"""
Fix Timezone Error Script
This script will fix the timezone.UTC compatibility issue
"""

import re
import os

def fix_timezone_error():
    print("🔧 Fixing timezone compatibility issue...")
    
    app_file = 'app.py'
    
    if not os.path.exists(app_file):
        print("❌ app.py file not found!")
        return False
    
    try:
        # Read the file
        with open(app_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Create backup
        backup_file = 'app_backup.py'
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Backup created: {backup_file}")
        
        # Replace timezone.UTC with timezone.utc
        original_count = content.count('timezone.UTC')
        content = content.replace('timezone.UTC', 'timezone.utc')
        
        # Write the fixed content back
        with open(app_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Fixed {original_count} timezone references")
        print("✅ app.py has been updated!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("🚀 Flask License Manager - Timezone Fix")
    print("=" * 40)
    
    if fix_timezone_error():
        print("\n🎉 Success! The timezone error has been fixed.")
        print("\n📋 Next steps:")
        print("1. Stop your Flask app (Ctrl+C)")
        print("2. Restart: python app.py")
        print("3. Try the settings toggle again")
    else:
        print("\n❌ Fix failed. Please check the error above.")

if __name__ == "__main__":
    main()

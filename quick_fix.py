"""
Quick Fix Script for License Manager Database Issue
This will immediately fix the missing license_number column issue.
"""

import sqlite3
import os

def quick_fix():
    print("🔧 Quick Fix for License Manager Database")
    print("=" * 45)
    
    db_path = 'license_manager.db'
    
    if not os.path.exists(db_path):
        print("❌ Database file not found!")
        print("Please run the main app first: python app.py")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the column exists
        cursor.execute("PRAGMA table_info(custom_app)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'license_number' not in columns:
            print("🔨 Adding missing license_number column...")
            
            # Add the column
            cursor.execute("ALTER TABLE custom_app ADD COLUMN license_number VARCHAR(50) DEFAULT ''")
            
            # Update existing apps with default license numbers
            cursor.execute("SELECT id, name FROM custom_app")
            apps = cursor.fetchall()
            
            for app_id, name in apps:
                default_license = f"LIC-{app_id:04d}"
                cursor.execute("UPDATE custom_app SET license_number = ? WHERE id = ?", (default_license, app_id))
            
            conn.commit()
            print(f"✅ Fixed! Updated {len(apps)} existing applications")
            print("✅ Database is now ready!")
            
        else:
            print("✅ Database is already up to date!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        conn.close()

def main():
    if quick_fix():
        print("\n🎉 Success! You can now access:")
        print("   - Dashboard: http://127.0.0.1:5000/dashboard")
        print("   - MyApps: http://127.0.0.1:5000/myapps")
        print("\n💡 Restart your Flask app if it's still running:")
        print("   1. Press Ctrl+C to stop the app")
        print("   2. Run: python app.py")
    else:
        print("\n❌ Fix failed. Try deleting the database file and starting fresh:")
        print("   1. Stop the Flask app (Ctrl+C)")
        print("   2. Delete: license_manager.db")
        print("   3. Run: python app.py")

if __name__ == "__main__":
    main()

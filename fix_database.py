"""
Database Fix Script
This script will fix common database issues automatically.
"""

import os
import sqlite3
import shutil
from datetime import datetime

def backup_database():
    """Create a backup of the existing database"""
    db_path = 'license_manager.db'
    if os.path.exists(db_path):
        backup_path = f'license_manager_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
        shutil.copy2(db_path, backup_path)
        print(f"✅ Database backed up to: {backup_path}")
        return backup_path
    return None

def fix_database():
    """Fix database issues"""
    db_path = 'license_manager.db'
    
    # Create backup first
    backup_path = backup_database()
    
    if not os.path.exists(db_path):
        print("No database file found. Will be created on first app run.")
        return True
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("Fixing database issues...")
        
        # Check and fix custom_app table
        cursor.execute("PRAGMA table_info(custom_app)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'license_number' not in columns:
            print("Adding missing license_number column...")
            cursor.execute("ALTER TABLE custom_app ADD COLUMN license_number VARCHAR(50) DEFAULT ''")
            
            # Update existing apps
            cursor.execute("SELECT id FROM custom_app")
            apps = cursor.fetchall()
            for (app_id,) in apps:
                license_num = f"LIC-{app_id:04d}"
                cursor.execute("UPDATE custom_app SET license_number = ? WHERE id = ?", (license_num, app_id))
            
            print(f"Updated {len(apps)} apps with license numbers")
        
        # Create missing tables
        tables_to_create = [
            ("footprint_table", """
                CREATE TABLE IF NOT EXISTS footprint_table (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    table_name VARCHAR(100) NOT NULL,
                    widget_name VARCHAR(100) NOT NULL,
                    is_visible BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """),
            ("daily_license_usage", """
                CREATE TABLE IF NOT EXISTS daily_license_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_id INTEGER,
                    server_type VARCHAR(50),
                    username VARCHAR(80),
                    device_name VARCHAR(100),
                    first_in_time DATETIME,
                    last_out_time DATETIME,
                    usage_date DATE,
                    total_hours FLOAT DEFAULT 0.0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """),
            ("my_apps_daily_usage", """
                CREATE TABLE IF NOT EXISTS my_apps_daily_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    app_id INTEGER,
                    username VARCHAR(80),
                    email VARCHAR(120),
                    first_in_time DATETIME,
                    last_out_time DATETIME,
                    usage_date DATE,
                    total_hours FLOAT DEFAULT 0.0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
        ]
        
        for table_name, create_sql in tables_to_create:
            cursor.execute(create_sql)
            print(f"Created/verified table: {table_name}")
        
        conn.commit()
        print("✅ Database fixed successfully!")
        
        # Verify the fix
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"\nDatabase now has {len(tables)} tables:")
        for table in sorted(tables):
            print(f"  - {table}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing database: {e}")
        if backup_path and os.path.exists(backup_path):
            print(f"Restoring from backup: {backup_path}")
            shutil.copy2(backup_path, db_path)
        return False
    finally:
        conn.close()

def main():
    print("🔧 Flask License Manager Database Fix Tool\n")
    
    choice = input("Choose an option:\n1. Fix existing database\n2. Start fresh (delete current database)\n3. Exit\nEnter choice (1-3): ")
    
    if choice == '1':
        if fix_database():
            print("\n🎉 Database fixed! You can now run: python app.py")
        else:
            print("\n❌ Fix failed. Consider option 2 (start fresh)")
    
    elif choice == '2':
        db_path = 'license_manager.db'
        if os.path.exists(db_path):
            backup_database()
            os.remove(db_path)
            print("✅ Database deleted. A new one will be created when you run the app.")
            print("Run: python app.py")
        else:
            print("No database file to delete.")
    
    elif choice == '3':
        print("Exiting...")
    
    else:
        print("Invalid choice. Exiting...")

if __name__ == "__main__":
    main()

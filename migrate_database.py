"""
Database Migration Script - Fixed Version
Run this script to update your existing database with new columns and tables.
"""

import sqlite3
import os
from datetime import datetime

def migrate_database():
    db_path = 'license_manager.db'
    
    if not os.path.exists(db_path):
        print("Database file not found. It will be created when you run the main app.")
        return True
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Starting database migration...")
    
    try:
        # Check if license_number column exists in custom_app table
        cursor.execute("PRAGMA table_info(custom_app)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'license_number' not in columns:
            print("Adding license_number column to custom_app table...")
            cursor.execute("ALTER TABLE custom_app ADD COLUMN license_number VARCHAR(50) DEFAULT ''")
            
            # Set default license numbers for existing apps
            cursor.execute("SELECT id, name FROM custom_app")
            apps = cursor.fetchall()
            for app_id, name in apps:
                default_license = f"LIC-{app_id:04d}"
                cursor.execute("UPDATE custom_app SET license_number = ? WHERE id = ?", (default_license, app_id))
            
            print(f"Updated {len(apps)} existing apps with default license numbers")
        else:
            print("license_number column already exists")
        
        # Create FootprintTable if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS footprint_table (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name VARCHAR(100) NOT NULL,
                widget_name VARCHAR(100) NOT NULL,
                is_visible BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("Created/verified footprint_table")
        
        # Create DailyLicenseUsage if it doesn't exist
        cursor.execute("""
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
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (server_id) REFERENCES license_server (id)
            )
        """)
        print("Created/verified daily_license_usage table")
        
        # Create MyAppsDailyUsage if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS my_apps_daily_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_id INTEGER,
                username VARCHAR(80),
                email VARCHAR(120),
                first_in_time DATETIME,
                last_out_time DATETIME,
                usage_date DATE,
                total_hours FLOAT DEFAULT 0.0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (app_id) REFERENCES custom_app (id)
            )
        """)
        print("Created/verified my_apps_daily_usage table")
        
        conn.commit()
        print("✅ Database migration completed successfully!")
        
        # Show current table structure
        print("\nCurrent database tables:")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        for table in tables:
            print(f"- {table[0]}")
        
        return True
            
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    success = migrate_database()
    if success:
        print("\n🎉 Migration completed! You can now run: python app.py")
    else:
        print("\n❌ Migration failed. You may need to delete the database and start fresh.")

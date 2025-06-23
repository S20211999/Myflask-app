"""
Database Reset Script
WARNING: This will delete all existing data and recreate the database.
Only use this if you want to start fresh.
"""

import os
import sqlite3

def reset_database():
    db_path = 'license_manager.db'
    
    if os.path.exists(db_path):
        response = input("WARNING: This will delete all existing data. Are you sure? (yes/no): ")
        if response.lower() != 'yes':
            print("Database reset cancelled.")
            return
        
        os.remove(db_path)
        print("Existing database deleted.")
    
    print("Database will be recreated when you run the main application.")
    print("Run: python app.py")

if __name__ == "__main__":
    reset_database()

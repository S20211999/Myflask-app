"""
Error Checking Script for Flask License Manager
This script will check for common issues and potential errors.
"""

import os
import sqlite3
import sys

def check_database_structure():
    """Check if database exists and has correct structure"""
    db_path = 'license_manager.db'
    
    if not os.path.exists(db_path):
        print("✅ Database file doesn't exist - will be created on first run")
        return True
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check all required tables
        required_tables = [
            'user', 'license_server', 'custom_app', 'app_user', 
            'activity_log', 'license_usage', 'footprint_database',
            'footprint_table', 'daily_license_usage', 'my_apps_daily_usage'
        ]
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        missing_tables = []
        for table in required_tables:
            if table not in existing_tables:
                missing_tables.append(table)
        
        if missing_tables:
            print(f"❌ Missing tables: {missing_tables}")
            return False
        
        # Check custom_app table structure
        cursor.execute("PRAGMA table_info(custom_app)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'license_number' not in columns:
            print("❌ custom_app table missing license_number column")
            return False
        
        print("✅ Database structure looks good")
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False
    finally:
        conn.close()

def check_python_dependencies():
    """Check if all required Python packages are installed"""
    required_packages = [
        'flask', 'flask_sqlalchemy', 'flask_login', 'werkzeug'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing Python packages: {missing_packages}")
        print("Run: pip install -r requirements.txt")
        return False
    
    print("✅ All required packages are installed")
    return True

def check_file_structure():
    """Check if all required files exist"""
    required_files = [
        'app.py',
        'requirements.txt',
        'templates/base.html',
        'templates/auth/login.html',
        'templates/dashboard.html',
        'templates/cadence.html',
        'templates/mentor.html',
        'templates/altium.html',
        'templates/myapps.html',
        'templates/footprint.html',
        'templates/settings.html',
        'templates/admin.html'
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    
    print("✅ All required files exist")
    return True

def check_app_py_syntax():
    """Check app.py for syntax errors"""
    try:
        with open('app.py', 'r') as f:
            code = f.read()
        
        compile(code, 'app.py', 'exec')
        print("✅ app.py syntax is valid")
        return True
        
    except SyntaxError as e:
        print(f"❌ Syntax error in app.py: {e}")
        return False
    except Exception as e:
        print(f"❌ Error checking app.py: {e}")
        return False

def check_template_syntax():
    """Check template files for basic syntax issues"""
    template_files = [
        'templates/base.html',
        'templates/auth/login.html',
        'templates/dashboard.html'
    ]
    
    issues = []
    
    for template in template_files:
        if os.path.exists(template):
            try:
                with open(template, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for common template issues
                if '{% extends' in content and not content.strip().startswith('{% extends'):
                    issues.append(f"{template}: extends should be at the beginning")
                
                # Check for unmatched braces
                open_braces = content.count('{%')
                close_braces = content.count('%}')
                if open_braces != close_braces:
                    issues.append(f"{template}: Unmatched template braces")
                
            except Exception as e:
                issues.append(f"{template}: Error reading file - {e}")
    
    if issues:
        print("❌ Template issues found:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    
    print("✅ Template files look good")
    return True

def check_port_availability():
    """Check if port 5000 is available"""
    import socket
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', 5000))
        sock.close()
        
        if result == 0:
            print("⚠️  Port 5000 is already in use")
            return False
        else:
            print("✅ Port 5000 is available")
            return True
            
    except Exception as e:
        print(f"❌ Error checking port: {e}")
        return False

def main():
    print("🔍 Checking Flask License Manager for errors...\n")
    
    all_good = True
    
    # Run all checks
    checks = [
        ("Python Dependencies", check_python_dependencies),
        ("File Structure", check_file_structure),
        ("App.py Syntax", check_app_py_syntax),
        ("Template Syntax", check_template_syntax),
        ("Database Structure", check_database_structure),
        ("Port Availability", check_port_availability)
    ]
    
    for check_name, check_func in checks:
        print(f"\n📋 {check_name}:")
        if not check_func():
            all_good = False
    
    print("\n" + "="*50)
    
    if all_good:
        print("🎉 All checks passed! Your application should run without issues.")
        print("\nTo start the application:")
        print("python app.py")
    else:
        print("❌ Some issues were found. Please fix them before running the application.")
        print("\nCommon fixes:")
        print("1. Run: pip install -r requirements.txt")
        print("2. Run: python migrate_database.py")
        print("3. Check that all template files exist")
    
    print("="*50)

if __name__ == "__main__":
    main()

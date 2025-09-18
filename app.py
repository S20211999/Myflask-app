
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, timezone
import subprocess
import threading
import json
import os
import re
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///license_manager.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# [Keep all your existing model classes here - User, LicenseServer, CustomApp, etc.]
# ... [All model definitions remain the same] ...

# FIXED: Background task functions with proper context management
def run_terminal_command(command, server_id):
    try:
        with app.app_context():  # ✅ CRITICAL FIX: Add application context
            server = LicenseServer.query.get(server_id)
            if not server:
                print(f"No server found with ID {server_id}")
                return

            exec_path = server.path
            if not exec_path:
                print(f"No path configured for server {server.name}")
                return

            lmutil_path = os.path.join(exec_path, "lmutil.exe")
            if not os.path.exists(lmutil_path):
                print(f"lmutil.exe not found at {exec_path}")
                return

            cmd = f'"{lmutil_path}" {server.command}'
            print(f"Executing: {cmd} in {exec_path}")
            
            result = subprocess.run(
                cmd,
                cwd=exec_path,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                print("Command executed successfully")
                print(f"Output: {result.stdout[:200]}...")
                parse_license_data(result.stdout, server_id)
            else:
                print(f"Command failed for server {server.name}: {result.stderr}")

    except subprocess.TimeoutExpired:
        print(f"Command timeout for server {server_id}")
    except Exception as e:
        print(f"Error running command: {e}")

def parse_license_data(output, server_id):
    try:
        # Already inside app context from run_terminal_command
        LicenseUsage.query.filter_by(server_id=server_id).delete()
        
        pcb_studio_block = re.search(
            r'Users of PCB_design_studio:.*?\(Total of \d+ licenses? issued;\s+Total of \d+ licenses? in use\)\s*"PCB_design_studio"\s+v([\d.]+),\s+vendor:\s+(\w+),\s+expiry:\s+([^,\n]+).*?vendor_string:\s+([^\n]+).*?floating license(.*?)(?=\n\s*Users of|$)',
            output,
            re.DOTALL
        )
        
        if pcb_studio_block:
            license_info = {
                'name': 'PCB_design_studio',
                'vendor': pcb_studio_block.group(2),
                'expiry': pcb_studio_block.group(3),
                'vendor_string': pcb_studio_block.group(4).strip(),
                'license_type': 'Floating License'
            }
            session['license_info'] = license_info

            user_block = pcb_studio_block.group(5)
            user_matches = re.finditer(
                r'\s*(\S+)\s+(\S+)\s+\d+:\d+\s+\(v(\d+\.\d+)\)\s+\([^)]*\),\s+start\s+(\w+\s+\d+/\d+\s+\d+:\d+)',
                user_block,
                re.MULTILINE
            )

            for match in user_matches:
                try:
                    username = match.group(1)
                    hostname = match.group(2)
                    app_version = match.group(3)
                    start_time_str = match.group(4)
                    
                    today = datetime.now(timezone.utc)
                    start_time = datetime.strptime(
                        f"{today.year} {start_time_str}", 
                        "%Y %a %m/%d %H:%M"
                    ).replace(tzinfo=timezone.utc)
                    
                    usage = LicenseUsage(
                        server_id=server_id,
                        username=username,
                        device_name=hostname,
                        version=app_version,
                        in_time=start_time
                    )
                    db.session.add(usage)
                    print(f"Parsed user: {username}, Host: {hostname}, App Version: {app_version}, Start: {start_time_str}")

                except Exception as e:
                    print(f"Error processing user {username}: {e}")
                    continue

            db.session.commit()
  
    except Exception as e:
        print(f"Error parsing license data: {e}")
        db.session.rollback()

def save_daily_usage():
    """Save daily usage data for all license servers and apps"""
    try:
        with app.app_context():  # ✅ CRITICAL FIX: Add application context
            today = datetime.now(timezone.utc).date()
            
            for server in LicenseServer.query.filter_by(is_enabled=True).all():
                usage_records = LicenseUsage.query.filter_by(server_id=server.id).all()
                
                for usage in usage_records:
                    if usage.in_time and usage.in_time.date() == today:
                        daily_record = DailyLicenseUsage.query.filter_by(
                            server_id=server.id,
                            username=usage.username,
                            usage_date=today
                        ).first()
                        
                        if not daily_record:
                            daily_record = DailyLicenseUsage(
                                server_id=server.id,
                                server_type=server.server_type,
                                username=usage.username,
                                device_name=usage.device_name,
                                first_in_time=usage.in_time,
                                usage_date=today
                            )
                            db.session.add(daily_record)
                        
                        if usage.out_time:
                            daily_record.last_out_time = usage.out_time
                            if daily_record.first_in_time:
                                hours = (usage.out_time - daily_record.first_in_time).total_seconds() / 3600
                                daily_record.total_hours = hours
            
            for app_obj in CustomApp.query.all():
                app_users = AppUser.query.filter_by(app_id=app_obj.id, status='active').all()
                
                for user in app_users:
                    if user.in_time and user.in_time.date() == today:
                        daily_record = MyAppsDailyUsage.query.filter_by(
                            app_id=app_obj.id,
                            username=user.username,
                            usage_date=today
                        ).first()
                        
                        if not daily_record:
                            daily_record = MyAppsDailyUsage(
                                app_id=app_obj.id,
                                username=user.username,
                                email=user.email,
                                first_in_time=user.in_time,
                                usage_date=today
                            )
                            db.session.add(daily_record)
                        
                        if user.out_time:
                            daily_record.last_out_time = user.out_time
                            if daily_record.first_in_time:
                                hours = (user.out_time - daily_record.first_in_time).total_seconds() / 3600
                                daily_record.total_hours = hours
            
            db.session.commit()
    except Exception as e:
        print(f"Error in save_daily_usage: {e}")
        with app.app_context():
            db.session.rollback()

def start_background_monitoring():
    def monitor_licenses():
        while True:
            try:
                with app.app_context():  # ✅ CRITICAL FIX: Add application context
                    servers = LicenseServer.query.filter_by(is_enabled=True).all()
                    threads = []
                    
                    for server in servers:
                        thread = threading.Thread(target=run_terminal_command, args=(server.command, server.id))
                        thread.daemon = True
                        thread.start()
                        threads.append(thread)
                    
                    for thread in threads:
                        thread.join()
                    
                    save_daily_usage()
                    
            except Exception as e:
                print(f"Error in background monitoring: {e}")
            
            threading.Event().wait(300)  # Wait 5 minutes
    
    monitor_thread = threading.Thread(target=monitor_licenses)
    monitor_thread.daemon = True
    monitor_thread.start()

# FIXED: API endpoint with proper error handling
@app.route('/api/footprint/add', methods=['POST'])
def add_footprint_api():
    try:
        data = request.get_json()
        
        # Verify license first using existing license verification system
        license_verification = data.get('license_verification', {})
        username = license_verification.get('username')
        email = license_verification.get('email')
        license_number = license_verification.get('license_number')
        
        print(f"[DEBUG] Received footprint data: {data.get('part_number')}, {data.get('footprint_name')}")
        print(f"[DEBUG] License verification: {username}, {email}, {license_number}")
        
        if not username or not email or not license_number:
            return jsonify({
                'status': 'error', 
                'message': 'License verification required'
            }), 401
        
        # Verify the license using existing logic
        with app.app_context():  # ✅ CRITICAL FIX: Ensure we're in app context
            app_obj = CustomApp.query.filter_by(license_number=license_number).first()
            if not app_obj:
                return jsonify({'status': 'error', 'message': 'Invalid license number'}), 401
            
            user = AppUser.query.filter(
                (AppUser.username == username) | (AppUser.email == email),
                AppUser.app_id == app_obj.id,
                AppUser.status == 'active',
                AppUser.permission == 'allow'
            ).first()
            
            if not user:
                return jsonify({'status': 'error', 'message': 'License verification failed'}), 401
            
            # Check expiry date
            if user.expiry_date and user.expiry_date < datetime.now(timezone.utc):
                return jsonify({'status': 'error', 'message': 'License expired'}), 401
            
            # Now save footprint data
            package_type = data.get('package_type')
            part_number = data.get('part_number')
            footprint_name = data.get('footprint_name')
            specifications = data.get('specifications', {})
            user_created = data.get('user_created', username)
            
            if not package_type or not part_number or not footprint_name:
                return jsonify({
                    'status': 'error', 
                    'message': 'package_type, part_number, and footprint_name are required'
                }), 400
            
            # Save to main FootprintDatabase table
            footprint = FootprintDatabase(
                package_type=package_type,
                part_number=part_number,
                footprint_name=footprint_name,
                specifications=json.dumps(specifications),
                user_created=user_created
            )
            db.session.add(footprint)
            
            # Save to package-specific table if it exists
            if package_type in PACKAGE_TABLE_MAP:
                PackageTable = PACKAGE_TABLE_MAP[package_type]
                
                # Create package-specific record
                package_record = PackageTable(
                    part_number=part_number,
                    footprint_name=footprint_name,
                    user_created=user_created
                )
                
                # Set package-specific attributes
                for key, value in specifications.items():
                    if hasattr(package_record, key) and value:
                        try:
                            # Convert to appropriate type
                            if key in ['pin_count']:
                                setattr(package_record, key, int(value))
                            elif key in ['body_length', 'body_width', 'body_height', 'pad_length', 
                                       'pad_width', 'mask_expansion', 'paste_expansion', 'airgap',
                                       'pitch', 'fillet_radius', 'mp_expansion']:
                                setattr(package_record, key, float(value))
                            else:
                                setattr(package_record, key, str(value))
                        except (ValueError, TypeError):
                            continue
                
                db.session.add(package_record)
            
            # Update user activity
            user.in_time = datetime.now(timezone.utc)
            
            db.session.commit()
            
            print(f"[SUCCESS] Saved footprint: {footprint_name} for user: {user_created}")
            
            return jsonify({
                'status': 'success',
                'message': 'Footprint data saved successfully',
                'footprint_id': footprint.id
            }), 200
        
    except Exception as e:
        print(f"[ERROR] Failed to save footprint: {str(e)}")
        with app.app_context():
            db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'Failed to save footprint data: {str(e)}'
        }), 500

# [Keep all other existing routes...]

if __name__ == '__main__':
    with app.app_context():  # ✅ CRITICAL FIX: Initialize database with context
        db.create_all()
        
        # Create default admin user if not exists
        if not User.query.filter_by(username='admin').first():
            admin_user = User(
                username='admin',
                email='admin@example.com',
                password_hash=generate_password_hash('admin123'),
                is_admin=True
            )
            db.session.add(admin_user)
            db.session.commit()
            print("Created default admin user: admin/admin123")
        
        # Check if license_number column exists before querying
        try:
            apps_without_license = CustomApp.query.filter_by(license_number='').all()
            for app_obj in apps_without_license:
                app_obj.license_number = f"LIC-{app_obj.id:04d}"
            
            if apps_without_license:
                db.session.commit()
                print(f"Updated {len(apps_without_license)} apps with default license numbers")
        except Exception as e:
            if "no such column" in str(e):
                print("Database schema needs updating. Please run: python migrate_database.py")
                print("Or delete license_manager.db to start fresh.")
            else:
                print(f"Database error: {e}")
    
    # Start background monitoring
    start_background_monitoring()
    
    print("Flask License Manager with PySide6 Integration")
    print("=" * 50)
    print("Server starting on http://localhost:5000")
    print("Default admin login: admin/admin123")
    print("API endpoints available:")
    print("  - GET  /api/health")
    print("  - POST /api/verify_license") 
    print("  - POST /api/footprint/add")
    print("  - GET  /api/footprint/list")
    print("=" * 50)
    
    # Run the app on local network
    app.run(host='0.0.0.0', port=5000, debug=True)


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

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = db.Column(db.Boolean, default=True)

class LicenseServer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    server_type = db.Column(db.String(50), nullable=False)  # cadence, mentor, altium
    command = db.Column(db.Text, nullable=False)
    path = db.Column(db.String(500))  # Path to license server executable
    total_licenses = db.Column(db.Integer, default=0)
    is_enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class CustomApp(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    license_number = db.Column(db.String(50), nullable=False, default='')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class AppUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.Integer, db.ForeignKey('custom_app.id'))
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    in_time = db.Column(db.DateTime)
    out_time = db.Column(db.DateTime)
    expiry_date = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='inactive')
    permission = db.Column(db.String(20), default='allow')  # allow/deny

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    action = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    ip_address = db.Column(db.String(45))
    user = db.relationship('User', backref='activity_logs')

class LicenseUsage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.Integer, db.ForeignKey('license_server.id'))
    username = db.Column(db.String(80))
    device_name = db.Column(db.String(100))
    version = db.Column(db.String(50))
    in_time = db.Column(db.DateTime)
    out_time = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='active')
    
    # Properties for backward compatibility
    @property
    def User(self):
        return self.username
    
    @property
    def Host(self):
        return self.device_name
    
    @property
    def App_Version(self):
        return self.version
    
    @property
    def Date(self):
        return self.in_time
    
    @property
    def Time(self):
        return self.in_time

# Updated FootprintDatabase with package-wise tables
class FootprintDatabase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    package_type = db.Column(db.String(50), nullable=False)  # DiscreteN, Sot23N, etc.
    part_number = db.Column(db.String(100), nullable=False)
    footprint_name = db.Column(db.String(100), nullable=False)
    specifications = db.Column(db.Text)  # JSON string of all parameters
    user_created = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    description = db.Column(db.Text)

# Package-wise tables
class DiscreteNFootprint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    part_number = db.Column(db.String(100), nullable=False)
    footprint_name = db.Column(db.String(100), nullable=False)
    body_length = db.Column(db.Float)
    body_width = db.Column(db.Float)
    body_height = db.Column(db.Float)
    pad_length = db.Column(db.Float)
    pad_width = db.Column(db.Float)
    mask_expansion = db.Column(db.Float)
    paste_expansion = db.Column(db.Float)
    airgap = db.Column(db.Float)
    user_created = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class DiscreteFFootprint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    part_number = db.Column(db.String(100), nullable=False)
    footprint_name = db.Column(db.String(100), nullable=False)
    body_length = db.Column(db.Float)
    body_width = db.Column(db.Float)
    body_height = db.Column(db.Float)
    pad_length = db.Column(db.Float)
    pad_width = db.Column(db.Float)
    fillet_radius = db.Column(db.Float)
    mask_expansion = db.Column(db.Float)
    paste_expansion = db.Column(db.Float)
    airgap = db.Column(db.Float)
    user_created = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class Sot23NFootprint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    part_number = db.Column(db.String(100), nullable=False)
    footprint_name = db.Column(db.String(100), nullable=False)
    body_length = db.Column(db.Float)
    body_width = db.Column(db.Float)
    body_height = db.Column(db.Float)
    pitch = db.Column(db.Float)
    pad_length = db.Column(db.Float)
    pad_width = db.Column(db.Float)
    mask_expansion = db.Column(db.Float)
    paste_expansion = db.Column(db.Float)
    pin_count = db.Column(db.Integer, default=3)
    user_created = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class Sot23NMPEFootprint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    part_number = db.Column(db.String(100), nullable=False)
    footprint_name = db.Column(db.String(100), nullable=False)
    body_length = db.Column(db.Float)
    body_width = db.Column(db.Float)
    body_height = db.Column(db.Float)
    pitch = db.Column(db.Float)
    pad_length = db.Column(db.Float)
    pad_width = db.Column(db.Float)
    mask_expansion = db.Column(db.Float)
    paste_expansion = db.Column(db.Float)
    mp_expansion = db.Column(db.Float)
    pin_count = db.Column(db.Integer, default=3)
    user_created = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class Sot23FFootprint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    part_number = db.Column(db.String(100), nullable=False)
    footprint_name = db.Column(db.String(100), nullable=False)
    body_length = db.Column(db.Float)
    body_width = db.Column(db.Float)
    body_height = db.Column(db.Float)
    pitch = db.Column(db.Float)
    pad_length = db.Column(db.Float)
    pad_width = db.Column(db.Float)
    fillet_radius = db.Column(db.Float)
    mask_expansion = db.Column(db.Float)
    paste_expansion = db.Column(db.Float)
    pin_count = db.Column(db.Integer, default=3)
    user_created = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class FootprintTable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    table_name = db.Column(db.String(100), nullable=False)
    widget_name = db.Column(db.String(100), nullable=False)
    is_visible = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class DailyLicenseUsage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.Integer, db.ForeignKey('license_server.id'))
    server_type = db.Column(db.String(50))  # cadence, mentor, altium
    username = db.Column(db.String(80))
    device_name = db.Column(db.String(100))
    first_in_time = db.Column(db.DateTime)
    last_out_time = db.Column(db.DateTime)
    usage_date = db.Column(db.Date, default=lambda: datetime.now(timezone.utc).date())
    total_hours = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class MyAppsDailyUsage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.Integer, db.ForeignKey('custom_app.id'))
    username = db.Column(db.String(80))
    email = db.Column(db.String(120))
    first_in_time = db.Column(db.DateTime)
    last_out_time = db.Column(db.DateTime)
    usage_date = db.Column(db.Date, default=lambda: datetime.now(timezone.utc).date())
    total_hours = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def log_activity(action):
    if current_user.is_authenticated:
        important_actions = [
            'logged in', 'logged out', 'Updated user', 'Created new user', 
            'Deleted user', 'Added new app', 'Server', 'Updated user permission',
            'Added footprint'
        ]
        
        if any(keyword in action for keyword in important_actions):
            log = ActivityLog(
                user_id=current_user.id,
                action=action,
                ip_address=request.remote_addr
            )
            db.session.add(log)
            db.session.commit()

# Package type to table mapping
PACKAGE_TABLE_MAP = {
    'DiscreteN': DiscreteNFootprint,
    'DiscreteF': DiscreteFFootprint,
    'Sot23N': Sot23NFootprint,
    'Sot23NMPE': Sot23NMPEFootprint,
    'Sot23F': Sot23FFootprint,
    # Add more mappings as you implement other package types
}

# Background task functions
# Background task for running terminal commands
def run_terminal_command(command, server_id):
    """
    Execute license server command using settings from database
    """
    try:
        # Get server settings from database
        server = LicenseServer.query.get(server_id)
        if not server:
            print(f"No server found with ID {server_id}")
            return

        # Use path from server settings
        exec_path = server.path
        if not exec_path:
            print(f"No path configured for server {server.name}")
            return

        # Build full command path
        lmutil_path = os.path.join(exec_path, "lmutil.exe")  # Add .exe extension
        if not os.path.exists(lmutil_path):
            print(f"lmutil.exe not found at {exec_path}")
            return

        # Build command array using the server command
        cmd = f'"{lmutil_path}" {server.command}'  # Quote the path and append command
        print(f"Executing: {cmd} in {exec_path}")
        
        result = subprocess.run(
            cmd,
            cwd=exec_path,
            shell=True,  # Use shell=True to handle command as string
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            print("Command executed successfully")
            print(f"Output: {result.stdout[:200]}...")  # Print first 200 chars
            parse_license_data(result.stdout, server_id)
        else:
            print(f"Command failed for server {server.name}: {result.stderr}")

    except subprocess.TimeoutExpired:
        print(f"Command timeout for server {server_id}")
    except Exception as e:
        print(f"Error running command: {e}")
        raise e  # Re-raise to see full error

def parse_license_data(output, server_id):
    try:
        with app.app_context():
            LicenseUsage.query.filter_by(server_id=server_id).delete()
            
            # Look specifically for PCB_design_studio block
            pcb_studio_block = re.search(
                r'Users of PCB_design_studio:.*?\(Total of \d+ licenses? issued;\s+Total of \d+ licenses? in use\)\s*"PCB_design_studio"\s+v([\d.]+),\s+vendor:\s+(\w+),\s+expiry:\s+([^,\n]+).*?vendor_string:\s+([^\n]+).*?floating license(.*?)(?=\n\s*Users of|$)',
                output,
                re.DOTALL
            )
            
            if pcb_studio_block:
                # Store license info
                license_info = {
                    'name': 'PCB_design_studio',
                    'vendor': pcb_studio_block.group(2),
                    'expiry': pcb_studio_block.group(3),
                    'vendor_string': pcb_studio_block.group(4).strip(),
                    'license_type': 'Floating License'
                }
                session['license_info'] = license_info

                # Parse users with modified regex to capture version correctly
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
                        
                        # Convert time string to datetime
                        today = datetime.now(timezone.utc)
                        start_time = datetime.strptime(
                            f"{today.year} {start_time_str}", 
                            "%Y %a %m/%d %H:%M"
                        ).replace(tzinfo=timezone.utc)
                        
                        usage = LicenseUsage(
                            server_id=server_id,
                            username=username,
                            device_name=hostname,
                            version=app_version,  # Use the main PCB_design_studio version
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
    today = datetime.now(timezone.utc).date()

    # Save license server usage
    for server in LicenseServer.query.filter_by(is_enabled=True).all():
        usage_records = LicenseUsage.query.filter_by(server_id=server.id).all()

        for usage in usage_records:
            if usage.Date and usage.Date.date() == today:
                # Find existing record
                daily_record = DailyLicenseUsage.query.filter_by(
                    server_id=server.id,
                    username=usage.User,
                    usage_date=today
                ).first()

                if not daily_record:
                    daily_record = DailyLicenseUsage(
                        server_id=server.id,
                        server_type=server.server_type,
                        username=usage.User,
                        device_name=usage.Host,
                        first_in_time=usage.Date,
                        usage_date=today
                    )
                    db.session.add(daily_record)
                else:
                    # Update last_out_time and compute total_hours if applicable
                    if usage.Date > daily_record.first_in_time:
                        daily_record.last_out_time = usage.Date
                        time_diff = (daily_record.last_out_time - daily_record.first_in_time).total_seconds()
                        daily_record.total_hours = round(time_diff / 3600, 2)  # rounded to 2 decimal places

    # Save MyApps usage
    for app in CustomApp.query.all():
        app_users = AppUser.query.filter_by(app_id=app.id, status='active').all()

        for user in app_users:
            if user.in_time and user.in_time.date() == today:
                daily_record = MyAppsDailyUsage.query.filter_by(
                    app_id=app.id,
                    username=user.username,
                    usage_date=today
                ).first()

                if not daily_record:
                    daily_record = MyAppsDailyUsage(
                        app_id=app.id,
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
                        daily_record.total_hours = round(hours, 2)

    db.session.commit()



def start_background_monitoring():
    def monitor_licenses():
        while True:
            with app.app_context():
                try:
                    servers = LicenseServer.query.filter_by(is_enabled=True).all()
                    
                    for server in servers:
                        try:
                            run_terminal_command(server.command, server.id)
                        except Exception as e:
                            print(f"Error monitoring server {server.id}: {e}")
                            continue
                    
                    save_daily_usage()
                    
                except Exception as e:
                    print(f"Background monitoring error: {e}")
                
                # Wait 5 minutes
                threading.Event().wait(300)
    
    monitor_thread = threading.Thread(target=monitor_licenses)
    monitor_thread.daemon = True
    monitor_thread.start()

# API Routes for PySide6 Integration
@app.route('/api/health')
def health_check():
    return jsonify({'status': 'healthy', 'message': 'Flask server is running'}), 200

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
    
@app.route('/api/footprint/list')
def list_footprints_api():
    try:
        package_type = request.args.get('package_type')
        
        query = FootprintDatabase.query
        if package_type:
            query = query.filter_by(package_type=package_type)
        
        footprints = query.order_by(FootprintDatabase.created_at.desc()).all()
        
        result = []
        for fp in footprints:
            result.append({
                'id': fp.id,
                'package_type': fp.package_type,
                'part_number': fp.part_number,
                'footprint_name': fp.footprint_name,
                'specifications': json.loads(fp.specifications) if fp.specifications else {},
                'user_created': fp.user_created,
                'created_at': fp.created_at.isoformat()
            })
        
        return jsonify({
            'status': 'success',
            'footprints': result,
            'count': len(result)
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to retrieve footprints: {str(e)}'
        }), 500

@app.route('/api/verify_license', methods=['POST'])
def verify_license():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'Missing JSON payload'}), 400

        username = data.get('username')
        email = data.get('email')
        license_number = data.get('license_number')

        print(f"[verify_license] Input -> username: {username}, email: {email}, license: {license_number}")

        if not (username and email and license_number):
            return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400

        app = CustomApp.query.filter_by(license_number=license_number).first()
        if not app:
            return jsonify({'status': 'denied', 'message': 'Invalid license number'}), 404

        user = AppUser.query.filter(
            ((AppUser.username == username) | (AppUser.email == email)),
            AppUser.app_id == app.id,
            AppUser.status == 'active',
            AppUser.permission == 'allow'
        ).first()

        if user:
            if user.expiry_date:
                expiry_date_aware = user.expiry_date
                if expiry_date_aware.tzinfo is None:
                    expiry_date_aware = expiry_date_aware.replace(tzinfo=timezone.utc)

                if expiry_date_aware < datetime.now(timezone.utc):
                    return jsonify({'status': 'denied', 'message': 'License expired'}), 403

            user.in_time = datetime.now(timezone.utc)
            db.session.commit()

            return jsonify({'status': 'approved', 'message': 'License verified successfully'}), 200
        else:
            return jsonify({'status': 'denied', 'message': 'License verification failed'}), 403

    except Exception as e:
        print(f"[verify_license] Exception: {e}")
        return jsonify({'status': 'error', 'message': f'Server error: {str(e)}'}), 500

# Existing web routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            log_activity(f"User {username} logged in")
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    log_activity(f"User {current_user.username} logged out")
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        cadence_servers = LicenseServer.query.filter_by(server_type='cadence', is_enabled=True).count()
        mentor_servers = LicenseServer.query.filter_by(server_type='mentor', is_enabled=True).count()
        altium_servers = LicenseServer.query.filter_by(server_type='altium', is_enabled=True).count()
        
        try:
            custom_apps = CustomApp.query.count()
        except Exception as e:
            if "no such column" in str(e).lower():
                flash('Database needs updating. Please run the migration script.', 'warning')
                custom_apps = 0
            else:
                raise e
        
        active_users = AppUser.query.filter_by(status='active').count()
        total_footprints = FootprintDatabase.query.count()
        
        log_activity("Accessed dashboard")
        
        return render_template('dashboard.html', 
                             cadence_servers=cadence_servers,
                             mentor_servers=mentor_servers,
                             altium_servers=altium_servers,
                             custom_apps=custom_apps,
                             active_users=active_users,
                             total_footprints=total_footprints)
                             
    except Exception as e:
        if "no such column" in str(e).lower():
            flash('Database schema is outdated. Please run: python migrate_database.py', 'error')
            return render_template('dashboard.html', 
                                 cadence_servers=0,
                                 mentor_servers=0,
                                 altium_servers=0,
                                 custom_apps=0,
                                 active_users=0,
                                 total_footprints=0)
        else:
            raise e

@app.route('/footprint')
@login_required
def footprint_database():
    footprints = FootprintDatabase.query.all()
    table_widgets = FootprintTable.query.filter_by(is_visible=True).all()
    
    # Statistics
    total_footprints = len(footprints)
    package_stats = {}
    user_stats = {}
    
    for fp in footprints:
        if fp.package_type:
            package_stats[fp.package_type] = package_stats.get(fp.package_type, 0) + 1
        if fp.user_created:
            user_stats[fp.user_created] = user_stats.get(fp.user_created, 0) + 1
    
    return render_template('footprint.html', 
                         footprints=footprints,
                         table_widgets=table_widgets,
                         total_footprints=total_footprints,
                         package_stats=package_stats,
                         user_stats=user_stats)

@app.route('/footprint/package/<package_type>')
@login_required
def footprint_by_package(package_type):
    """View footprints by package type"""
    footprints = FootprintDatabase.query.filter_by(package_type=package_type).all()
    
    # Get package-specific data if available
    package_data = []
    if package_type in PACKAGE_TABLE_MAP:
        PackageTable = PACKAGE_TABLE_MAP[package_type]
        package_data = PackageTable.query.all()
    
    return render_template('footprint_package.html', 
                         package_type=package_type,
                         footprints=footprints,
                         package_data=package_data)

@app.route('/cadence')
@login_required
def cadence():
    servers = LicenseServer.query.filter_by(server_type='cadence', is_enabled=True).all()
    usage_data = {}
    
    for server in servers:
        usages = LicenseUsage.query.filter_by(server_id=server.id).all()
        usage_data[server.id] = [
            {
                'User': usage.User,
                'Host': usage.Host,
                'App_Version': usage.App_Version,
                'Date': usage.Date.strftime('%Y-%m-%d') if usage.Date else '-',
                'Time': usage.Time if usage.Time else '-'
            }
            for usage in usages
        ]
    
    log_activity("Accessed Cadence page")
    return render_template('cadence.html', servers=servers, usage_data=usage_data, license_info=session.get('license_info'))

@app.route('/cadence/refresh')
@login_required
def cadence_refresh():
    servers = LicenseServer.query.filter_by(server_type='cadence', is_enabled=True).all()
    
    for server in servers:
        try:
            run_terminal_command(server.command, server.id)
        except Exception as e:
            print(f"Error updating server {server.id}: {e}")
    
    usage_data = {}
    for server in servers:
        usages = LicenseUsage.query.filter_by(server_id=server.id).all()
        usage_data[server.id] = [
            {
                'User': usage.User,
                'Host': usage.Host,
                'App_Version': usage.App_Version,
                'Date': usage.Date.strftime('%Y-%m-%d') if usage.Date else '-',
                'Time': usage.Time if usage.Time else '-'
            }
            for usage in usages
        ]

    return jsonify(usage_data)

@app.route('/mentor')
@login_required
def mentor():
    servers = LicenseServer.query.filter_by(server_type='mentor', is_enabled=True).all()
    usage_data = {}

    for server in servers:
        usages = LicenseUsage.query.filter_by(server_id=server.id).all()
        usage_data[server.id] = [
            {
                'User': usage.User,
                'Host': usage.Host,
                'App_Version': usage.App_Version,
                'Date': usage.Date.strftime('%Y-%m-%d') if usage.Date else '-',
                'Time': usage.Time if usage.Time else '-'
            }
            for usage in usages
        ]
    
    log_activity("Accessed Mentor page")
    return render_template('mentor.html', servers=servers, usage_data=usage_data)

@app.route('/mentor/refresh')
@login_required
def mentor_refresh():
    servers = LicenseServer.query.filter_by(server_type='mentor', is_enabled=True).all()
    
    for server in servers:
        try:
            run_terminal_command(server.command, server.id)
        except Exception as e:
            print(f"Error updating server {server.id}: {e}")
    
    usage_data = {}
    for server in servers:
        usages = LicenseUsage.query.filter_by(server_id=server.id).all()
        usage_data[server.id] = [
            {
                'User': usage.User,
                'Host': usage.Host,
                'App_Version': usage.App_Version,
                'Date': usage.Date.strftime('%Y-%m-%d') if usage.Date else '-',
                'Time': usage.Time if usage.Time else '-'
            }
            for usage in usages
        ]
    
    return jsonify(usage_data)

@app.route('/altium')
@login_required
def altium():
    servers = LicenseServer.query.filter_by(server_type='altium', is_enabled=True).all()
    usage_data = {}
    
    for server in servers:
        usage_data[server.id] = LicenseUsage.query.filter_by(server_id=server.id).all()
    
    log_activity("Accessed Altium page")
    return render_template('altium.html', servers=servers, usage_data=usage_data)

@app.route('/myapps')
@login_required
def myapps():
    try:
        apps = CustomApp.query.all()
        log_activity("Accessed MyApps page")
        return render_template('myapps.html', apps=apps)
    except Exception as e:
        if "no such column" in str(e).lower():
            flash('Database schema is outdated. Please run: python migrate_database.py', 'error')
            return render_template('myapps.html', apps=[])
        else:
            raise e

@app.route('/myapps/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_app():
    if request.method == 'POST':
        name = request.form['name']
        license_number = request.form['license_number']
        
        app = CustomApp(name=name, license_number=license_number)
        db.session.add(app)
        db.session.commit()
        
        log_activity(f"Added new app: {name}")
        flash('Application added successfully!', 'success')
        return redirect(url_for('myapps'))
    
    return render_template('add_app.html')

@app.route('/myapps/<int:app_id>/users')
@login_required
def app_users(app_id):
    app = CustomApp.query.get_or_404(app_id)
    users = AppUser.query.filter_by(app_id=app_id).all()
    return render_template('app_users.html', app=app, users=users)

@app.route('/myapps/<int:app_id>/add_user', methods=['POST'])
@login_required
@admin_required
def add_app_user(app_id):
    username = request.form['username']
    email = request.form['email']
    permission = request.form['permission']
    expiry_date = request.form.get('expiry_date')
    
    user = AppUser(
        app_id=app_id,
        username=username,
        email=email,
        permission=permission,
        in_time=datetime.now(timezone.utc),
        status='active'
    )
    
    if expiry_date:
        user.expiry_date = datetime.strptime(expiry_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    
    db.session.add(user)
    db.session.commit()
    
    log_activity(f"Added user {username} to app {app_id}")
    flash('User added successfully!', 'success')
    return redirect(url_for('app_users', app_id=app_id))

@app.route('/settings')
@login_required
@admin_required
def settings():
    servers = LicenseServer.query.all()
    log_activity("Accessed Settings page")
    return render_template('settings.html', servers=servers)

@app.route('/settings/add_server', methods=['POST'])
@login_required
@admin_required
def add_server():
    name = request.form['name']
    server_type = request.form['server_type']
    command = request.form['command']
    total_licenses = int(request.form['total_licenses'])
    path = request.form.get('path')

    server = LicenseServer(
        name=name,
        server_type=server_type,
        command=command,
        path=path,
        total_licenses=total_licenses
    )

    db.session.add(server)
    db.session.commit()

    log_activity(f"Added new license server: {name}")
    flash('License server added successfully!', 'success')
    return redirect(url_for('settings'))

@app.route('/settings/edit_server/<int:server_id>', methods=['POST'])
@login_required
@admin_required
def edit_server(server_id):
    server = LicenseServer.query.get_or_404(server_id)
    server.name = request.form['name']
    server.server_type = request.form['server_type']
    server.command = request.form['command']
    server.total_licenses = int(request.form['total_licenses'])
    server.path = request.form.get('path')

    db.session.commit()

    log_activity(f"Updated license server: {server.name}")
    flash('License server updated successfully!', 'success')
    return redirect(url_for('settings'))

@app.route('/settings/delete_server/<int:server_id>', methods=['POST'])
@login_required
@admin_required
def delete_server(server_id):
    server = LicenseServer.query.get_or_404(server_id)
    
    db.session.delete(server)
    db.session.commit()
    
    log_activity(f"Deleted license server: {server.name}")
    flash(f'Server "{server.name}" deleted successfully.', 'success')
    return redirect(url_for('settings'))

@app.route('/admin')
@login_required
@admin_required
def admin():
    users = User.query.all()
    logs = ActivityLog.query.join(User).order_by(ActivityLog.timestamp.desc()).limit(50).all()
    log_activity("Accessed Admin page")
    return render_template('admin.html', users=users, logs=logs)

@app.route('/admin/create_user', methods=['POST'])
@login_required
@admin_required
def create_user():
    username = request.form['username']
    email = request.form['email']
    temp_password = request.form['temp_password']
    is_admin = 'is_admin' in request.form
    
    if User.query.filter_by(username=username).first():
        flash('Username already exists!', 'error')
        return redirect(url_for('admin'))
    
    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(temp_password),
        is_admin=is_admin
    )
    
    db.session.add(user)
    db.session.commit()
    
    log_activity(f"Created new user: {username}")
    flash('User created successfully!', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/delete_user/<int:user_id>')
@login_required
@admin_required
def delete_user(user_id):
    if user_id == current_user.id:
        flash('Cannot delete your own account!', 'error')
        return redirect(url_for('admin'))
    
    user = User.query.get_or_404(user_id)
    username = user.username
    db.session.delete(user)
    db.session.commit()
    
    log_activity(f"Deleted user: {username}")
    flash('User deleted successfully!', 'success')
    return redirect(url_for('admin'))

@app.route('/myapps/<int:app_id>/update_user_permission', methods=['POST'])
@login_required
@admin_required
def update_user_permission(app_id):
    user_id = request.form['user_id']
    permission = request.form['permission']
    
    user = AppUser.query.get_or_404(user_id)
    user.permission = permission
    db.session.commit()
    
    log_activity(f"Updated user permission for {user.username} to {permission}")
    flash('User permission updated successfully!', 'success')
    return redirect(url_for('app_users', app_id=app_id))

@app.route('/myapps/<int:app_id>/delete_user/<int:user_id>')
@login_required
@admin_required
def delete_app_user(app_id, user_id):
    user = AppUser.query.get_or_404(user_id)
    username = user.username
    db.session.delete(user)
    db.session.commit()
    
    log_activity(f"Deleted user {username} from app {app_id}")
    flash('User deleted successfully!', 'success')
    return redirect(url_for('app_users', app_id=app_id))

@app.route('/settings/toggle_server/<int:server_id>')
@login_required
@admin_required
def toggle_server(server_id):
    server = LicenseServer.query.get_or_404(server_id)
    server.is_enabled = not server.is_enabled
    db.session.commit()
    
    status = "enabled" if server.is_enabled else "disabled"
    log_activity(f"Server {server.name} {status}")
    flash(f'Server {status} successfully!', 'success')
    return redirect(url_for('settings'))

@app.route('/admin/edit_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    user.username = request.form['username']
    user.email = request.form['email']
    user.is_admin = 'is_admin' in request.form
    user.is_active = 'is_active' in request.form
    
    db.session.commit()
    
    log_activity(f"Updated user: {user.username}")
    flash('User updated successfully!', 'success')
    return redirect(url_for('admin'))

@app.route('/myapps/<int:app_id>/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def app_settings(app_id):
    app = CustomApp.query.get_or_404(app_id)
    
    if request.method == 'POST':
        app.name = request.form['name']
        app.license_number = request.form['license_number']
        db.session.commit()
        
        log_activity(f"Updated app settings: {app.name}")
        flash('Application settings updated successfully!', 'success')
        return redirect(url_for('myapps'))
    
    return render_template('app_settings.html', app=app)

@app.route('/reports/daily_usage')
@login_required
def daily_usage_report():
    cadence_usage = DailyLicenseUsage.query.filter_by(server_type='cadence').order_by(DailyLicenseUsage.usage_date.desc()).limit(100).all()
    mentor_usage = DailyLicenseUsage.query.filter_by(server_type='mentor').order_by(DailyLicenseUsage.usage_date.desc()).limit(100).all()
    altium_usage = DailyLicenseUsage.query.filter_by(server_type='altium').order_by(DailyLicenseUsage.usage_date.desc()).limit(100).all()
    myapps_usage = MyAppsDailyUsage.query.order_by(MyAppsDailyUsage.usage_date.desc()).limit(100).all()
    
    return render_template('daily_usage_report.html',
                         cadence_usage=cadence_usage,
                         mentor_usage=mentor_usage,
                         altium_usage=altium_usage,
                         myapps_usage=myapps_usage)

@app.route('/footprint/add_table_widget', methods=['POST'])
@login_required
@admin_required
def add_table_widget():
    table_name = request.form['table_name']
    widget_name = request.form['widget_name']
    
    existing = FootprintTable.query.filter_by(table_name=table_name).first()
    if existing:
        flash('Table widget already exists!', 'error')
        return redirect(url_for('footprint_database'))
    
    widget = FootprintTable(
        table_name=table_name,
        widget_name=widget_name
    )
    
    db.session.add(widget)
    db.session.commit()
    
    log_activity(f"Added table widget: {widget_name}")
    flash('Table widget added successfully!', 'success')
    return redirect(url_for('footprint_database'))

@app.route('/footprint/delete_widget/<int:widget_id>')
@login_required
@admin_required
def delete_table_widget(widget_id):
    widget = FootprintTable.query.get_or_404(widget_id)
    widget_name = widget.widget_name
    db.session.delete(widget)
    db.session.commit()
    
    log_activity(f"Deleted table widget: {widget_name}")
    flash('Table widget deleted successfully!', 'success')
    return redirect(url_for('footprint_database'))

if __name__ == '__main__':
    with app.app_context():
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
            for app in apps_without_license:
                app.license_number = f"LIC-{app.id:04d}"
            
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

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, timezone
import subprocess
import threading
import json
import os
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
    in_time = db.Column(db.DateTime)
    out_time = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='active')

class FootprintDatabase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    package = db.Column(db.String(100))
    user_created = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    description = db.Column(db.Text)

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
        # Only log specific actions
        important_actions = [
            'logged in', 'logged out', 'Updated user', 'Created new user', 
            'Deleted user', 'Added new app', 'Server', 'Updated user permission'
        ]
        
        if any(keyword in action for keyword in important_actions):
            log = ActivityLog(
                user_id=current_user.id,
                action=action,
                ip_address=request.remote_addr
            )
            db.session.add(log)
            db.session.commit()

# Background task for running terminal commands
def run_terminal_command(command, server_id):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        # Parse the result and update license usage data
        # This is a placeholder - you'll need to implement parsing based on your actual commands
        parse_license_data(result.stdout, server_id)
    except subprocess.TimeoutExpired:
        print(f"Command timeout for server {server_id}")
    except Exception as e:
        print(f"Error running command for server {server_id}: {e}")

def parse_license_data(output, server_id):
    # Placeholder function to parse license server output
    # You'll need to implement this based on your actual license server output format
    lines = output.split('\n')
    for line in lines:
        if 'user:' in line.lower():
            # Parse user data and update database
            # This is a simplified example
            pass

def save_daily_usage():
    """Save daily usage data for all license servers and apps"""
    today = datetime.now(timezone.utc).date()
    
    # Save license server usage
    for server in LicenseServer.query.filter_by(is_enabled=True).all():
        usage_records = LicenseUsage.query.filter_by(server_id=server.id).all()
        
        for usage in usage_records:
            if usage.in_time and usage.in_time.date() == today:
                # Check if daily record already exists
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
                
                # Update last out time if available
                if usage.out_time:
                    daily_record.last_out_time = usage.out_time
                    if daily_record.first_in_time:
                        hours = (usage.out_time - daily_record.first_in_time).total_seconds() / 3600
                        daily_record.total_hours = hours
    
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
                        daily_record.total_hours = hours
    
    db.session.commit()

def start_background_monitoring():
    def monitor_licenses():
        while True:
            with app.app_context():  # Add application context
                try:
                    servers = LicenseServer.query.filter_by(is_enabled=True).all()
                    threads = []
                    
                    for server in servers:
                        thread = threading.Thread(target=run_terminal_command, args=(server.command, server.id))
                        thread.daemon = True
                        thread.start()
                        threads.append(thread)
                    
                    # Wait for all threads to complete
                    for thread in threads:
                        thread.join()
                    
                    # Save daily usage data
                    save_daily_usage()
                    
                except Exception as e:
                    print(f"Error in background monitoring: {e}")
                
                # Wait 5 minutes before next check
                threading.Event().wait(300)
    
    monitor_thread = threading.Thread(target=monitor_licenses)
    monitor_thread.daemon = True
    monitor_thread.start()

# Routes
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
        # Collect data from all modules
        cadence_servers = LicenseServer.query.filter_by(server_type='cadence', is_enabled=True).count()
        mentor_servers = LicenseServer.query.filter_by(server_type='mentor', is_enabled=True).count()
        altium_servers = LicenseServer.query.filter_by(server_type='altium', is_enabled=True).count()
        
        # Handle potential missing license_number column
        try:
            custom_apps = CustomApp.query.count()
        except Exception as e:
            if "no such column" in str(e).lower():
                flash('Database needs updating. Please run the migration script.', 'warning')
                custom_apps = 0
            else:
                raise e
        
        # Active users count - count unique active users across all app users
        active_users = AppUser.query.filter_by(status='active').count()
        
        # Total footprints
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

@app.route('/cadence')
@login_required
def cadence():
    servers = LicenseServer.query.filter_by(server_type='cadence', is_enabled=True).all()
    usage_data = {}
    
    for server in servers:
        usage_data[server.id] = LicenseUsage.query.filter_by(server_id=server.id).all()
    
    log_activity("Accessed Cadence page")
    return render_template('cadence.html', servers=servers, usage_data=usage_data)

@app.route('/mentor')
@login_required
def mentor():
    servers = LicenseServer.query.filter_by(server_type='mentor', is_enabled=True).all()
    usage_data = {}
    
    for server in servers:
        usage_data[server.id] = LicenseUsage.query.filter_by(server_id=server.id).all()
    
    log_activity("Accessed Mentor page")
    return render_template('mentor.html', servers=servers, usage_data=usage_data)

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

@app.route('/api/verify_license', methods=['POST'])
def verify_license():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    license_number = data.get('license_number')
    
    # Find the app with the license number
    app = CustomApp.query.filter_by(license_number=license_number).first()
    if not app:
        return jsonify({'status': 'denied', 'message': 'Invalid license number'})
    
    # Verify user in the license server
    user = AppUser.query.filter(
        (AppUser.username == username) | (AppUser.email == email),
        AppUser.app_id == app.id,
        AppUser.status == 'active',
        AppUser.permission == 'allow'
    ).first()
    
    if user:
        # Check expiry date
        if user.expiry_date and user.expiry_date < datetime.now(timezone.utc):
            return jsonify({'status': 'denied', 'message': 'License expired'})
        
        # Update in_time
        user.in_time = datetime.now(timezone.utc)
        db.session.commit()
        
        return jsonify({'status': 'approved', 'message': 'License verified successfully'})
    else:
        return jsonify({'status': 'denied', 'message': 'License verification failed'})

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
        if fp.package:
            package_stats[fp.package] = package_stats.get(fp.package, 0) + 1
        if fp.user_created:
            user_stats[fp.user_created] = user_stats.get(fp.user_created, 0) + 1
    
    return render_template('footprint.html', 
                         footprints=footprints,
                         table_widgets=table_widgets,
                         total_footprints=total_footprints,
                         package_stats=package_stats,
                         user_stats=user_stats)

@app.route('/footprint/add_table_widget', methods=['POST'])
@login_required
@admin_required
def add_table_widget():
    table_name = request.form['table_name']
    widget_name = request.form['widget_name']
    
    # Check if widget already exists
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
    
    server = LicenseServer(
        name=name,
        server_type=server_type,
        command=command,
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
    
    db.session.commit()
    
    log_activity(f"Updated license server: {server.name}")
    flash('License server updated successfully!', 'success')
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
    # Get daily usage data for all servers
    cadence_usage = DailyLicenseUsage.query.filter_by(server_type='cadence').order_by(DailyLicenseUsage.usage_date.desc()).limit(100).all()
    mentor_usage = DailyLicenseUsage.query.filter_by(server_type='mentor').order_by(DailyLicenseUsage.usage_date.desc()).limit(100).all()
    altium_usage = DailyLicenseUsage.query.filter_by(server_type='altium').order_by(DailyLicenseUsage.usage_date.desc()).limit(100).all()
    myapps_usage = MyAppsDailyUsage.query.order_by(MyAppsDailyUsage.usage_date.desc()).limit(100).all()
    
    return render_template('daily_usage_report.html',
                         cadence_usage=cadence_usage,
                         mentor_usage=mentor_usage,
                         altium_usage=altium_usage,
                         myapps_usage=myapps_usage)

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
        
        # Check if license_number column exists before querying
        try:
            # Try to query for apps without license numbers
            apps_without_license = CustomApp.query.filter_by(license_number='').all()
            for app in apps_without_license:
                app.license_number = f"LIC-{app.id:04d}"
            
            if apps_without_license:
                db.session.commit()
                print(f"Updated {len(apps_without_license)} apps with default license numbers")
        except Exception as e:
            # If the column doesn't exist, we need to run migration
            if "no such column" in str(e):
                print("Database schema needs updating. Please run: python migrate_database.py")
                print("Or delete license_manager.db to start fresh.")
            else:
                print(f"Database error: {e}")
    
    # Start background monitoring
    start_background_monitoring()
    
    # Run the app on local network
    app.run(host='0.0.0.0', port=5000, debug=True)

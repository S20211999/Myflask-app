""" Central Server - ENHANCED
Manages user authentication, standards, and footprint data
With Library Database support
"""

from flask import Flask, request, jsonify, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets
import json
import os

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(32)  # Generate secure secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///libsienna.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

# Enable CORS for cross-origin requests
CORS(app, supports_credentials=True)

# Initialize database
db = SQLAlchemy(app)

# ==================== DATABASE MODELS ====================

class User(db.Model):
    """User model for authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin, manager, employee
    email = db.Column(db.String(120), unique=True)
    full_name = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    standards = db.relationship('Standard', backref='creator', lazy=True)
    footprints = db.relationship('Footprint', backref='creator', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'email': self.email,
            'full_name': self.full_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'is_active': self.is_active
        }


class Standard(db.Model):
    """Standards configuration model"""
    __tablename__ = 'standards'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    tool = db.Column(db.String(50))  # Altium, Allegro, PADS, Expedition
    data = db.Column(db.Text, nullable=False)  # JSON data
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    version = db.Column(db.Integer, default=1)
    is_active = db.Column(db.Boolean, default=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'tool': self.tool,
            'data': json.loads(self.data) if self.data else {},
            'created_by': self.creator.username if self.creator else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'version': self.version,
            'is_active': self.is_active
        }


class Footprint(db.Model):
    """Footprint data model"""
    __tablename__ = 'footprints'
    
    id = db.Column(db.Integer, primary_key=True)
    part_number = db.Column(db.String(100))
    footprint_name = db.Column(db.String(100))
    data = db.Column(db.Text, nullable=False)  # JSON footprint data
    standard_used = db.Column(db.String(100))
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    tool = db.Column(db.String(50))
    
    def to_dict(self):
        return {
            'id': self.id,
            'part_number': self.part_number,
            'footprint_name': self.footprint_name,
            'data': json.loads(self.data) if self.data else {},
            'standard_used': self.standard_used,
            'created_by': self.creator.username if self.creator else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'tool': self.tool
        }


class Session(db.Model):
    """Session tokens for remember me functionality"""
    __tablename__ = 'sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    
    user = db.relationship('User', backref='sessions')

# ==================== AUTHENTICATION ENDPOINTS ====================

@app.route('/api/login', methods=['POST'])
def login():
    """User login endpoint"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        remember_me = data.get('remember_me', False)
        
        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400
        
        # Find user
        user = User.query.filter_by(username=username).first()
        if not user or not user.is_active:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Verify password
        if not check_password_hash(user.password_hash, password):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Create session
        session['user_id'] = user.id
        session['username'] = user.username
        session['role'] = user.role
        if remember_me:
            session.permanent = True
        
        # Generate token for remember me
        token = None
        if remember_me:
            token = secrets.token_hex(32)
            new_session = Session(
                user_id=user.id,
                token=token,
                expires_at=datetime.utcnow() + timedelta(days=30)
            )
            db.session.add(new_session)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'username': user.username,
            'role': user.role,
            'token': token,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/logout', methods=['POST'])
def logout():
    """User logout endpoint"""
    try:
        user_id = session.get('user_id')
        if user_id:
            # Invalidate all sessions for this user
            Session.query.filter_by(user_id=user_id).delete()
            db.session.commit()
        
        session.clear()
        return jsonify({'success': True}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/verify_token', methods=['POST'])
def verify_token():
    """Verify remember me token"""
    try:
        data = request.get_json()
        token = data.get('token')
        
        if not token:
            return jsonify({'error': 'Token required'}), 400
        
        # Find session
        session_obj = Session.query.filter_by(token=token).first()
        if not session_obj or session_obj.expires_at < datetime.utcnow():
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        user = session_obj.user
        if not user.is_active:
            return jsonify({'error': 'User inactive'}), 401
        
        # Create new session
        session['user_id'] = user.id
        session['username'] = user.username
        session['role'] = user.role
        session.permanent = True
        
        return jsonify({
            'success': True,
            'username': user.username,
            'role': user.role,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== USER MANAGEMENT ENDPOINTS ====================

@app.route('/api/users', methods=['GET'])
def get_users():
    """Get all users - Modified to allow access for creator dropdown"""
    try:
        # Allow users list for dropdown purposes (only basic info)
        users = User.query.filter_by(is_active=True).all()
        
        # Return minimal user info for non-admin users
        if session.get('role') != 'admin':
            return jsonify([{
                'id': user.id,
                'username': user.username,
                'full_name': user.full_name
            } for user in users]), 200
        
        # Full user info for admin
        return jsonify([user.to_dict() for user in users]), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/users', methods=['POST'])
def create_user():
    """Create new user (admin only)"""
    try:
        if session.get('role') != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403
        
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        role = data.get('role', 'employee')
        email = data.get('email')
        full_name = data.get('full_name')
        
        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400
        
        # Check if user exists
        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username already exists'}), 400
        
        # Create user
        password_hash = generate_password_hash(password)
        new_user = User(
            username=username,
            password_hash=password_hash,
            role=role,
            email=email,
            full_name=full_name
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'user': new_user.to_dict()
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """Update user (admin only)"""
    try:
        if session.get('role') != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        if 'role' in data:
            user.role = data['role']
        if 'email' in data:
            user.email = data['email']
        if 'full_name' in data:
            user.full_name = data['full_name']
        if 'is_active' in data:
            user.is_active = data['is_active']
        if 'password' in data:
            user.password_hash = generate_password_hash(data['password'])
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== STANDARDS MANAGEMENT ENDPOINTS ====================

@app.route('/api/standards', methods=['GET'])
def get_standards():
    """Get all active standards"""
    try:
        standards = Standard.query.filter_by(is_active=True).all()
        return jsonify([std.to_dict() for std in standards]), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/standards/<string:name>', methods=['GET'])
def get_standard(name):
    """Get specific standard by name"""
    try:
        standard = Standard.query.filter_by(name=name, is_active=True).first()
        if not standard:
            return jsonify({'error': 'Standard not found'}), 404
        
        return jsonify(standard.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/standards/save', methods=['POST'])
def save_standard():
    """Save or update standard (admin/manager only)"""
    try:
        # Check if user is logged in via session
        user_id = session.get('user_id')
        user_role = session.get('role')
        
        print(f"Save standard request - User ID: {user_id}, Role: {user_role}")
        print(f"Session data: {dict(session)}")
        
        if not user_id:
            return jsonify({'error': 'Not logged in - No session found'}), 401
        
        if user_role not in ['admin', 'manager']:
            return jsonify({'error': f'Unauthorized - Admin or Manager role required. Your role: {user_role}'}), 403
        
        data = request.get_json()
        name = data.get('name')
        standard_data = data.get('data')
        
        if not name or not standard_data:
            return jsonify({'error': 'Name and data required'}), 400
        
        # Check if standard exists
        existing = Standard.query.filter_by(name=name).first()
        
        if existing:
            # Update existing
            existing.data = json.dumps(standard_data)
            existing.tool = standard_data.get('tool')
            existing.updated_at = datetime.utcnow()
            existing.version += 1
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Standard updated',
                'standard': existing.to_dict()
            }), 200
        else:
            # Create new
            new_standard = Standard(
                name=name,
                tool=standard_data.get('tool'),
                data=json.dumps(standard_data),
                created_by_id=user_id
            )
            db.session.add(new_standard)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Standard created',
                'standard': new_standard.to_dict()
            }), 201
            
    except Exception as e:
        print(f"Error in save_standard: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/standards/<string:name>', methods=['DELETE'])
def delete_standard(name):
    """Delete standard (admin/manager only)"""
    try:
        user_role = session.get('role')
        if user_role not in ['admin', 'manager']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        standard = Standard.query.filter_by(name=name).first()
        if not standard:
            return jsonify({'error': 'Standard not found'}), 404
        
        # Soft delete
        standard.is_active = False
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Standard deleted'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== FOOTPRINT MANAGEMENT ENDPOINTS ====================

@app.route('/api/footprints/save', methods=['POST'])
def save_footprint():
    """Save generated footprint with metadata - Enhanced"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not logged in'}), 401
        
        data = request.get_json()
        
        # Validate required fields
        if not data.get('footprint_name'):
            return jsonify({'error': 'Footprint name is required'}), 400
        
        new_footprint = Footprint(
            part_number=data.get('part_number', 'N/A'),
            footprint_name=data.get('footprint_name'),
            data=json.dumps(data),
            standard_used=data.get('standard_used', 'Default'),
            tool=data.get('tool', 'Altium Designer'),
            created_by_id=user_id
        )
        
        db.session.add(new_footprint)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Footprint saved successfully',
            'footprint': new_footprint.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/footprints', methods=['GET'])
def get_footprints():
    """Get all footprints with optional filters - Enhanced for Library Database"""
    try:
        # Get query parameters for filtering
        search_term = request.args.get('search_term', '')
        search_by = request.args.get('search_by', 'part_number')  # part_number or footprint_name
        filter_type = request.args.get('filter_type', 'all')  # all, created_by, date
        created_by = request.args.get('created_by')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = int(request.args.get('limit', 1000))  # Increased default limit
        
        # Base query
        query = Footprint.query
        
        # Apply search term filter
        if search_term:
            if search_by == 'part_number':
                query = query.filter(Footprint.part_number.ilike(f'%{search_term}%'))
            elif search_by == 'footprint_name':
                query = query.filter(Footprint.footprint_name.ilike(f'%{search_term}%'))
        
        # Apply created_by filter
        if filter_type == 'created_by' and created_by:
            if created_by != 'All Users':
                user = User.query.filter_by(username=created_by).first()
                if user:
                    query = query.filter_by(created_by_id=user.id)
        
        # Apply date range filter
        if filter_type == 'date' and start_date and end_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
                # Add one day to end date to include the entire end date
                end = end + timedelta(days=1)
                query = query.filter(Footprint.created_at.between(start, end))
            except ValueError as ve:
                return jsonify({'error': f'Invalid date format: {str(ve)}'}), 400
        
        # Order by most recent first
        footprints = query.order_by(Footprint.created_at.desc()).limit(limit).all()
        
        # Convert to dictionary with enhanced info
        result = []
        for fp in footprints:
            fp_dict = fp.to_dict()
            # Add additional formatting for UI
            fp_dict['created_date'] = fp.created_at.strftime('%Y-%m-%d %H:%M:%S') if fp.created_at else 'N/A'
            fp_dict['standard'] = fp.standard_used or 'Default'
            fp_dict['creator'] = fp.creator.username if fp.creator else 'Unknown'
            result.append(fp_dict)
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"Error in get_footprints: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/footprints/<int:footprint_id>', methods=['GET'])
def get_footprint(footprint_id):
    """Get specific footprint"""
    try:
        footprint = Footprint.query.get(footprint_id)
        if not footprint:
            return jsonify({'error': 'Footprint not found'}), 404
        
        return jsonify(footprint.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/landpatterns/save', methods=['POST'])
def save_landpattern():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.json
    package_name = data.get('package_name', 'unnamed')
    # Save to database here
    return jsonify({'message': 'Saved', 'package_name': package_name}), 201



# ==================== ENHANCED FOOTPRINT ENDPOINTS ====================

@app.route('/api/footprints/creators', methods=['GET'])
def get_footprint_creators():
    """Get list of unique creators who have created footprints"""
    try:
        creators_query = db.session.query(User).join(
            Footprint, User.id == Footprint.created_by_id
        ).distinct().all()
        
        creators = [{'username': user.username, 'full_name': user.full_name} 
                   for user in creators_query]
        
        return jsonify(creators), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/footprints/daterange', methods=['GET'])
def get_footprint_date_range():
    """Get the earliest and latest footprint creation dates"""
    try:
        earliest = db.session.query(db.func.min(Footprint.created_at)).scalar()
        latest = db.session.query(db.func.max(Footprint.created_at)).scalar()
        
        return jsonify({
            'earliest': earliest.isoformat() if earliest else None,
            'latest': latest.isoformat() if latest else None
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/footprints/search', methods=['POST'])
def search_footprints_advanced():
    """Advanced search for footprints with multiple criteria"""
    try:
        data = request.get_json()
        
        query = Footprint.query
        
        # Apply filters
        if data.get('search_term'):
            term = f"%{data['search_term']}%"
            if data.get('search_by') == 'part_number':
                query = query.filter(Footprint.part_number.ilike(term))
            else:
                query = query.filter(Footprint.footprint_name.ilike(term))
        
        if data.get('creator_username'):
            user = User.query.filter_by(username=data['creator_username']).first()
            if user:
                query = query.filter_by(created_by_id=user.id)
        
        if data.get('start_date') and data.get('end_date'):
            start = datetime.fromisoformat(data['start_date'])
            end = datetime.fromisoformat(data['end_date']) + timedelta(days=1)
            query = query.filter(Footprint.created_at.between(start, end))
        
        if data.get('standard'):
            query = query.filter_by(standard_used=data['standard'])
        
        if data.get('tool'):
            query = query.filter_by(tool=data['tool'])
        
        # Execute query
        footprints = query.order_by(Footprint.created_at.desc()).all()
        
        # Format results
        result = []
        for fp in footprints:
            result.append({
                'id': fp.id,
                'part_number': fp.part_number or 'N/A',
                'footprint_name': fp.footprint_name,
                'created_date': fp.created_at.strftime('%Y-%m-%d %H:%M:%S') if fp.created_at else 'N/A',
                'standard': fp.standard_used or 'Default',
                'creator': fp.creator.username if fp.creator else 'Unknown',
                'tool': fp.tool
            })
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/footprints/export', methods=['POST'])
def export_footprints():
    """Export filtered footprints to Excel (server-side)"""
    try:
        data = request.get_json()
        footprint_ids = data.get('footprint_ids', [])
        
        if not footprint_ids:
            return jsonify({'error': 'No footprints selected'}), 400
        
        # Query footprints
        footprints = Footprint.query.filter(Footprint.id.in_(footprint_ids)).all()
        
        # Return data - client will handle Excel generation
        result = []
        for fp in footprints:
            result.append({
                'part_number': fp.part_number,
                'footprint_name': fp.footprint_name,
                'created_date': fp.created_at.strftime('%Y-%m-%d %H:%M:%S') if fp.created_at else 'N/A',
                'standard': fp.standard_used or 'Default',
                'creator': fp.creator.username if fp.creator else 'Unknown',
                'tool': fp.tool
            })
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== STATISTICS ENDPOINTS ====================

@app.route('/api/stats', methods=['GET'])
def get_statistics():
    """Get system statistics"""
    try:
        stats = {
            'total_users': User.query.filter_by(is_active=True).count(),
            'total_standards': Standard.query.filter_by(is_active=True).count(),
            'total_footprints': Footprint.query.count(),
            'active_sessions': Session.query.filter(Session.expires_at > datetime.utcnow()).count()
        }
        
        if session.get('role') == 'admin':
            stats['users_by_role'] = {
                'admin': User.query.filter_by(role='admin', is_active=True).count(),
                'manager': User.query.filter_by(role='manager', is_active=True).count(),
                'employee': User.query.filter_by(role='employee', is_active=True).count()
            }
        
        return jsonify(stats), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== DATABASE INITIALIZATION ====================

def init_database():
    """Initialize database with default admin user"""
    with app.app_context():
        db.create_all()
        
        # Check if admin exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            # Create default admin user
            admin_password = generate_password_hash('admin123')
            admin = User(
                username='admin',
                password_hash=admin_password,
                role='admin',
                email='admin@libsienna.com',
                full_name='System Administrator',
                is_active=True
            )
            db.session.add(admin)
            
            # Create default manager
            manager_password = generate_password_hash('manager123')
            manager = User(
                username='manager',
                password_hash=manager_password,
                role='manager',
                email='manager@libsienna.com',
                full_name='Default Manager',
                is_active=True
            )
            db.session.add(manager)
            
            # Create default employee
            employee_password = generate_password_hash('employee123')
            employee = User(
                username='employee',
                password_hash=employee_password,
                role='employee',
                email='employee@libsienna.com',
                full_name='Default Employee',
                is_active=True
            )
            db.session.add(employee)
            
            db.session.commit()
            
            print("Database initialized with default users:")
            print("  Admin: admin / admin123")
            print("  Manager: manager / manager123")
            print("  Employee: employee / employee123")

# ==================== MAIN ====================

if __name__ == '__main__':
    # Initialize database
    init_database()
    
    # Run server
    print("\n" + "="*60)
    print("LibSienna Central Server Starting... (ENHANCED)")
    print("="*60)
    print("Server URL: http://localhost:5000")
    print("API Base: http://localhost:5000/api")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)




















import sys
import os
import json
import math
import os
from pathlib import Path
import requests
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,QDialog,QListWidget,
                            QHBoxLayout, QGridLayout, QLabel, QLineEdit, QSizePolicy, QMenu,
                            QComboBox, QPushButton, QScrollArea, QFrame,QListWidgetItem,
                            QSpinBox, QDoubleSpinBox, QFileDialog, QMessageBox, QCheckBox,
                            QSplitter, QGroupBox, QToolBar,QDateEdit, QTabWidget,QStackedWidget)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QRectF, QPointF,QDate
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QPalette, QPolygonF, QAction, QPainterPath
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtSvg import QSvgRenderer
import struct
import decimal
from decimal import Decimal, getcontext, ROUND_HALF_UP, InvalidOperation


# Set decimal precision (adjust as needed for your application)
getcontext().prec = 5
getcontext().rounding = ROUND_HALF_UP

# Package types data structure with SVG paths
PACKAGE_TYPES = {
    'SOJ (Small Outline Package) - J Leads': 'svg/soj.svg',
    'SON (Small Outline No-Lead)': 'svg/son.svg',
    'SOP (Small Outline Package) - Gullwing Leads': 'svg/sop.svg',
    'SOT23 (Small Outline Transistor)': 'svg/sot23.svg',
    'SOT89 (Small Outline Transistor)': 'svg/sot89.svg',
    'SOT143_343 (Small Outline Transistor)': 'svg/sot143.svg',
    'SOT223 (Small Outline Transistor)': 'svg/sot223.svg',
    'SOTFL (Small Outline Transistor Flat-Lead)': 'svg/sotfl.svg',
    'BGA (Ball Grid Array)': 'svg/bga.svg',
    'BQFP (Bumpered Quad Flat Pack)': 'svg/bqfp.svg',
    'CAN (Thru-hole Metal Can)': 'svg/can.svg',
    'CAN-FM (Thru-hole Flange Mount CAN)': 'svg/can_fm.svg',
    'CAPAE (Electrolytic Aluminum Capacitor)': 'svg/capae.svg',
    'CFP (Dual Flat Pack)': 'svg/cfp.svg',
    'Chip Array (Chip Array)': 'svg/chip_array.svg',
    'Chip Components': 'svg/chip_components.svg',
    'CQFP (Ceramic Quad Flat Pack)': 'svg/cqfp.svg',
    'DFN (Dual Flat No-Lead)': 'svg/dfn.svg',
    'DIP (Thru-hole Dual-In-Line)': 'svg/dip.svg',
    'DPAK (Transistor outline)': 'svg/dpak.svg',
    'FM (Flange Mount)': 'svg/fm.svg',
    'LCC (Leadless Chip Carrier)': 'svg/lcc.svg',
    'LGA (Land Grid Array)': 'svg/lga.svg',
    'MELF': 'svg/melf.svg',
    'Molded Components (Capacitor Inductor Diode)': 'svg/molded.svg',
    'PCY (Thru-hole Plastic Cylinder Flat Index)': 'svg/pcy.svg',
    'PLCC (Leaded Chip Carrier)': 'svg/plcc.svg',
    'PQFN (Quad Flat No-Lead Pullback)': 'svg/pqfn.svg',
    'PQFP (Plastic Quad Flat Pack)': 'svg/pqfp.svg',
    'Precision Wire Wound_Inductor': 'svg/wire_wound.svg',
    'PSON (Small Outline No-lead Pullback)': 'svg/pson.svg',
    'QFN (Quad Flat No-Leads)': 'svg/qfn.svg',
    'QFN-2Rows (Quad Flat No-leads, 2 Rows, Square)': 'svg/qfn_2rows.svg',
    'SIP (Single Inline Package)': 'svg/sip.svg',
    'SODFL (Small Outline Diode Flat-Lead)': 'svg/sodfl.svg',
    'SOF (Small Outline Flat Leads)': 'svg/sof.svg',
    'SOIC (Small Outline Integrated Package)': 'svg/soic.svg',
}

IPC_CLASSES = ['Land Pattern', 'IPC Class A', 'IPC Class B', 'IPC Class C']

# ALTIUM LAYER MAPPING DICTIONARY
ALTIUM_LAYER_MAP = {
    # Body Layers
    "Top Assembly": "TopAssembly",
    "Bottom Assembly": "BottomAssembly",
    "Mechanical 1": "echanical1",
    "Mechanical 13": "Mechanical13",

    # Courtyard Layers
    "Mechanical 15": "Mechanical15",
    "Mechanical 16": "Mechanical16",
    "Top Courtyard": "TopCourtyard",
    "Bottom Courtyard": "BottomCourtyard",

    # Text/Overlay Layers
    "Top Overlay": "TopOverlay",
    "Bottom Overlay": "BottomOverlay",

    # Copper Layers
    "Top Layer": "TopLayer",
    "Bottom Layer": "BottomLayer",
    "All Layers": "MultiLayer",  # For through-hole items

    # Mask and Paste Layers
    "Top Solder": "TopSolder",
    "Bottom Solder": "BottomSolder",
    "Top Paste": "TopPaste",
    "Bottom Paste": "BottomPaste",

    # Additional Mechanical Layers (if needed)
    "Mechanical 2": "Mechanical2",
    "Mechanical 3": "Mechanical3",
    "Mechanical 4": "Mechanical4",
    "Mechanical 5": "Mechanical5",
    "Mechanical 6": "Mechanical6",
    "Mechanical 7": "Mechanical7",
    "Mechanical 8": "Mechanical8",
    "Mechanical 9": "Mechanical9",
    "Mechanical 10": "Mechanical10",
    "Mechanical 11": "Mechanical11",
    "Mechanical 12": "Mechanical12",
    "Mechanical 14": "Mechanical14",
    "Mechanical 15": "Mechanical15",
    "Mechanical 16": "Mechanical16",
}

def map_layer_to_altium(layer_name):
    """Map UI layer name to Altium script layer name"""
    if layer_name in ALTIUM_LAYER_MAP:
        return ALTIUM_LAYER_MAP[layer_name]
    
    # Fallback for Mechanical layers
    if "Mechanical" in layer_name:
        parts = layer_name.split()
        if len(parts) == 2 and parts[1].isdigit():
            return f"eMechanical{parts[1]}"
    
    return layer_name

def to_decimal(value, default=0):
    """Convert various input types to Decimal safely"""
    if value is None or value == "":
        return Decimal(str(default))
    try:
        if isinstance(value, str):
            if value.strip() == "":
                return Decimal(str(default))
            return Decimal(value)
        elif isinstance(value, (int, float)):
            return Decimal(str(value))
        elif isinstance(value, Decimal):
            return value
        else:
            return Decimal(str(default))
    except (ValueError, TypeError, decimal.InvalidOperation):
        return Decimal(str(default))

def convert_floats_to_decimals(data):
    """Recursively convert all float values in nested data structures to Decimal"""
    if isinstance(data, dict):
        return {k: convert_floats_to_decimals(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_floats_to_decimals(x) for x in data]
    elif isinstance(data, float):
        return Decimal(str(data))
    else:
        return data


class AccountManager:
    """Manages account settings separate from footprint data"""
    
    SETTINGS_FILE = "account_settings.json"
    
    @staticmethod
    def get_settings_path():
        """Get the path for account settings file"""
        # Store in user's home directory
        home_dir = os.path.expanduser("~")
        settings_dir = os.path.join(home_dir, ".libsienna")
        os.makedirs(settings_dir, exist_ok=True)
        return os.path.join(settings_dir, AccountManager.SETTINGS_FILE)
    
    @staticmethod
    def load_account_settings():
        """Load account settings from JSON file"""
        settings_path = AccountManager.get_settings_path()
        
        # Default settings
        default_settings = {
            'current_user': None,
            'altium_output_path': os.path.expanduser("~/Documents/Altium"),
            'allegro_output_path': os.path.expanduser("~/Documents/Allegro"),
            'pads_output_path': os.path.expanduser("~/Documents/PADS"),
            'xpedition_output_path': os.path.expanduser("~/Documents/Xpedition")
        }
        
        try:
            if os.path.exists(settings_path):
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    for key, value in default_settings.items():
                        if key not in settings:
                            settings[key] = value
                    return settings
            else:
                return default_settings
        except Exception as e:
            print(f"Error loading account settings: {e}")
            return default_settings
    
    @staticmethod
    def save_account_settings(settings):
        """Save account settings to JSON file"""
        settings_path = AccountManager.get_settings_path()
        
        try:
            with open(settings_path, 'w') as f:
                json.dump(settings, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving account settings: {e}")
            return False

class ServerConnection:
    """Handles communication with the central server"""
    
    def __init__(self, server_url='http://localhost:5000'):
        self.server_url = server_url
        self.api_url = f'{server_url}/api'
        self.session = requests.Session()  # Maintains cookies automatically
        self.session_token = None
        self.current_user = None
        self.user_role = None
        self.credentials_file = os.path.expanduser('~/.libsienna/credentials.json')
    
    def login(self, username, password, remember_me=False):
        """Authenticate user with server"""
        try:
            payload = {
                'username': username,
                'password': password,
                'remember_me': remember_me
            }
            
            response = self.session.post(
                f'{self.api_url}/login',
                json=payload,
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                self.session_token = data.get('token')
                self.current_user = username
                self.user_role = data.get('role')
                
                print(f"Login successful - User: {username}, Role: {self.user_role}")
                print(f"Session cookies: {self.session.cookies}")
                
                if remember_me and self.session_token:
                    self.save_credentials(username, self.session_token)
                
                return True, self.user_role
            else:
                error = response.json().get('error', 'Login failed')
                return False, error
                
        except Exception as e:
            return False, f"Connection error: {str(e)}"
    
    def verify_token(self, token):
        """Verify saved session token"""
        try:
            payload = {'token': token}
            response = self.session.post(f'{self.api_url}/verify_token', json=payload, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                self.session_token = token
                self.current_user = data.get('username')
                self.user_role = data.get('role')
                return True, self.user_role
            else:
                return False, 'Token invalid or expired'
        except Exception as e:
            return False, f'Connection error: {str(e)}'
    
    def logout(self):
        """Logout user"""
        try:
            if self.session_token:
                self.session.post(f'{self.api_url}/logout', timeout=5)
            
            self.session_token = None
            self.current_user = None
            self.user_role = None
            self.clear_credentials()
            return True, 'Logged out'
        except Exception as e:
            return False, f'Error: {str(e)}'
    
    def get_standards(self):
        """Fetch all standards from server"""
        try:
            response = self.session.get(f'{self.api_url}/standards', timeout=5)
            if response.status_code == 200:
                return True, response.json()
            return False, 'Failed to fetch standards'
        except Exception as e:
            return False, f'Connection error: {str(e)}'
    
    def save_standard(self, name, config):
        """Save standard to server"""
        try:
            payload = {
                'name': name,
                'data': config
            }
            
            # Session automatically sends cookies - no need for Authorization header
            print(f"Saving standard with session cookies: {self.session.cookies}")
            
            response = self.session.post(
                f'{self.api_url}/standards/save',
                json=payload,
                timeout=5
            )
            
            print(f"Save response status: {response.status_code}")
            print(f"Save response: {response.text}")
            
            if response.status_code in [200, 201]:
                return True, response.json()
            
            return False, response.json().get('error', 'Save failed')
            
        except Exception as e:
            print(f"Save standard error: {e}")
            return False, f"Connection error: {str(e)}"
            
    def delete_standard(self, name):
        """Delete standard from server"""
        try:
            # Add Authorization header
            headers = {}
            if self.session_token:
                headers['Authorization'] = f'Bearer {self.session_token}'
            
            response = self.session.delete(
                f'{self.api_url}/standards/delete/{name}',
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                return True, response.json()
            return False, response.json().get('error', 'Delete failed')
        except Exception as e:
            return False, f'Connection error: {str(e)}'
    
    def save_credentials(self, username, token):
        """Save credentials locally for auto-login"""
        try:
            cred_dir = os.path.dirname(self.credentials_file)
            os.makedirs(cred_dir, exist_ok=True)
            
            credentials = {
                'username': username,
                'token': token,
                'timestamp': datetime.now().isoformat()
            }
            
            with open(self.credentials_file, 'w') as f:
                json.dump(credentials, f)
        except Exception as e:
            print(f"Failed to save credentials: {e}")
    
    def load_saved_credentials(self):
        """Load saved credentials for auto-login"""
        try:
            if os.path.exists(self.credentials_file):
                with open(self.credentials_file, 'r') as f:
                    creds = json.load(f)
                    return creds
        except Exception as e:
            print(f"Failed to load credentials: {e}")
        return None
    
    def clear_credentials(self):
        """Clear saved credentials"""
        try:
            if os.path.exists(self.credentials_file):
                os.remove(self.credentials_file)
        except Exception as e:
            print(f"Failed to clear credentials: {e}")

    
  
    def save_footprint(self, footprint_data):
        """Save footprint with metadata"""
        try:
            response = requests.post(
                f'{self.api_url}/footprints/save',
                json=footprint_data,
                timeout=5
            )
            if response.status_code == 201:
                return True, response.json()
            return False, response.json().get('error', 'Save failed')
        except Exception as e:
            return False, f'Connection error: {str(e)}'

class AccountDialog(QDialog):
    """Account management dialog with server authentication"""
    
    login_success = pyqtSignal(str, str, str)  # token, role, username
    
    def __init__(self, parent=None, server_url='http://localhost:5000'):
        super().__init__(parent)
        self.setWindowTitle("Account Settings")
        self.setMinimumSize(500, 500)
        
        self.server = ServerConnection(server_url)
        self.server_url = server_url
        
        self.current_user = None
        self.user_role = None
        self.token = None
        
        self.setup_ui()
        self.load_settings()
        self.setup_styling()
        self.try_auto_login()
    
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("Account Settings")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # User Account Section
        self.setup_user_section(layout)
        
        # Separator
        self.add_separator(layout)
        
        # Output Paths Section
        self.setup_output_paths_section(layout)
        
        # Save button
        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)
        
        layout.addStretch()
    
    def setup_user_section(self, layout):
        """Setup user account and authentication section"""
        user_group = QGroupBox("User Account Authentication")
        user_layout = QVBoxLayout(user_group)
        
        # User display
        self.user_display = QLabel("Not logged in")
        self.user_display.setStyleSheet("color: #ffffff; margin: 5px; font-weight: bold;")
        user_layout.addWidget(self.user_display)
        
        # Login form
        self.login_frame = QFrame()
        login_layout = QGridLayout(self.login_frame)
        login_layout.setSpacing(10)
        
        login_layout.addWidget(QLabel("Username:"), 0, 0)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username")
        login_layout.addWidget(self.username_input, 0, 1)
        
        login_layout.addWidget(QLabel("Password:"), 1, 0)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Enter password")
        self.password_input.returnPressed.connect(self.handle_login)
        login_layout.addWidget(self.password_input, 1, 1)
        
        self.remember_me_check = QCheckBox("Remember Me")
        self.remember_me_check.setStyleSheet("color: #ffffff;")
        login_layout.addWidget(self.remember_me_check, 2, 0, 1, 2)
        
        self.login_btn = QPushButton("Login")
        self.login_btn.clicked.connect(self.handle_login)
        login_layout.addWidget(self.login_btn, 3, 0, 1, 2)
        
        user_layout.addWidget(self.login_frame)
        
        # Logout button
        self.logout_btn = QPushButton("Logout")
        self.logout_btn.clicked.connect(self.handle_logout)
        self.logout_btn.setVisible(False)
        user_layout.addWidget(self.logout_btn)
        
        # Role display
        self.role_display = QLabel()
        self.role_display.setStyleSheet("color: #aaaaaa; font-size: 11px; margin: 5px;")
        user_layout.addWidget(self.role_display)
        
        layout.addWidget(user_group)
    
    def setup_output_paths_section(self, layout):
        """Setup output paths configuration"""
        paths_group = QGroupBox("Script Output Paths")
        paths_layout = QGridLayout(paths_group)
        
        # Altium
        paths_layout.addWidget(QLabel("Altium Script Output:"), 0, 0)
        path_layout1 = QHBoxLayout()
        self.altium_output_path = QLineEdit()
        self.altium_output_path.setPlaceholderText("Select Altium output directory...")
        path_layout1.addWidget(self.altium_output_path)
        browse_btn1 = QPushButton("Browse...")
        browse_btn1.clicked.connect(lambda: self.browse_output_path(self.altium_output_path, "Altium"))
        browse_btn1.setMaximumWidth(80)
        path_layout1.addWidget(browse_btn1)
        paths_layout.addLayout(path_layout1, 0, 1)
        
        # Allegro
        paths_layout.addWidget(QLabel("Allegro Script Output:"), 1, 0)
        path_layout2 = QHBoxLayout()
        self.allegro_output_path = QLineEdit()
        self.allegro_output_path.setPlaceholderText("Select Allegro output directory...")
        path_layout2.addWidget(self.allegro_output_path)
        browse_btn2 = QPushButton("Browse...")
        browse_btn2.clicked.connect(lambda: self.browse_output_path(self.allegro_output_path, "Allegro"))
        browse_btn2.setMaximumWidth(80)
        path_layout2.addWidget(browse_btn2)
        paths_layout.addLayout(path_layout2, 1, 1)
        
        # PADS
        paths_layout.addWidget(QLabel("PADS Script Output:"), 2, 0)
        path_layout3 = QHBoxLayout()
        self.pads_output_path = QLineEdit()
        self.pads_output_path.setPlaceholderText("Select PADS output directory...")
        path_layout3.addWidget(self.pads_output_path)
        browse_btn3 = QPushButton("Browse...")
        browse_btn3.clicked.connect(lambda: self.browse_output_path(self.pads_output_path, "PADS"))
        browse_btn3.setMaximumWidth(80)
        path_layout3.addWidget(browse_btn3)
        paths_layout.addLayout(path_layout3, 2, 1)
        
        # Xpedition
        paths_layout.addWidget(QLabel("Xpedition Script Output:"), 3, 0)
        path_layout4 = QHBoxLayout()
        self.xpedition_output_path = QLineEdit()
        self.xpedition_output_path.setPlaceholderText("Select Xpedition output directory...")
        path_layout4.addWidget(self.xpedition_output_path)
        browse_btn4 = QPushButton("Browse...")
        browse_btn4.clicked.connect(lambda: self.browse_output_path(self.xpedition_output_path, "Xpedition"))
        browse_btn4.setMaximumWidth(80)
        path_layout4.addWidget(browse_btn4)
        paths_layout.addLayout(path_layout4, 3, 1)
        
        layout.addWidget(paths_group)
    
    def browse_output_path(self, line_edit, tool_name):
        """Browse for output directory"""
        path = QFileDialog.getExistingDirectory(self, f"Select {tool_name} Script Output Directory", line_edit.text())
        if path:
            line_edit.setText(path)
    
    def handle_login(self):
        """Handle login button click"""
        username = self.username_input.text().strip()
        password = self.password_input.text()
        remember_me = self.remember_me_check.isChecked()
        
        if not username or not password:
            QMessageBox.warning(self, 'Login', 'Please enter both username and password')
            return
        
        try:
            self.login_btn.setEnabled(False)
            self.login_btn.setText("Logging in...")
            
            success, result = self.server.login(username, password, remember_me)
            
            if success:
                self.current_user = username
                self.user_role = result
                self.token = self.server.session_token
                
                self.user_display.setText(f"Welcome, {username}")
                self.role_display.setText(f"Role: {result.capitalize()}")
                self.login_frame.setVisible(False)
                self.logout_btn.setVisible(True)
                self.password_input.clear()
                
                # Emit signal for parent window
                self.login_success.emit(self.token, self.user_role, self.current_user)
                
                if hasattr(self.parent(), 'update_standards_permissions'):
                    self.parent().update_standards_permissions()
                
                QMessageBox.information(self, 'Login', f'Successfully logged in as {result.capitalize()}')
            else:
                QMessageBox.warning(self, 'Login Failed', result)
                self.password_input.clear()
        
        finally:
            self.login_btn.setEnabled(True)
            self.login_btn.setText("Login")
    
    def handle_logout(self):
        """Handle logout"""
        success, message = self.server.logout()
        
        # Clear credentials file
        try:
            settings_path = os.path.join(os.path.expanduser('~/.libsienna'), 'credentials.json')
            if os.path.exists(settings_path):
                os.remove(settings_path)
        except:
            pass
        
        self.current_user = None
        self.user_role = None
        self.token = None
        
        self.user_display.setText("Not logged in")
        self.role_display.setText("")
        self.login_frame.setVisible(True)
        self.logout_btn.setVisible(False)
        self.username_input.clear()
        self.password_input.clear()
        self.remember_me_check.setChecked(False)
        
        if hasattr(self.parent(), 'update_standards_permissions'):
            self.parent().update_standards_permissions()
        
        QMessageBox.information(self, 'Logout', 'Successfully logged out')
    
    def try_auto_login(self):
        """Try to auto-login with saved credentials"""
        creds = self.server.load_saved_credentials()
        if creds and 'username' in creds and 'token' in creds:
            success, role = self.server.verify_token(creds['token'])
            if success:
                self.current_user = creds['username']
                self.user_role = role
                self.token = creds['token']
                
                self.user_display.setText(f"Welcome, {self.current_user}")
                self.role_display.setText(f"Role: {role.capitalize()}")
                self.login_frame.setVisible(False)
                self.logout_btn.setVisible(True)
                
                self.login_success.emit(self.token, self.user_role, self.current_user)
                
                if hasattr(self.parent(), 'update_standards_permissions'):
                    self.parent().update_standards_permissions()
    
    def load_settings(self):
        """Load account settings"""
        settings = AccountManager.load_account_settings()
        
        self.altium_output_path.setText(settings.get('altium_output_path', 
            os.path.expanduser('~/Documents/Altium')))
        self.allegro_output_path.setText(settings.get('allegro_output_path', 
            os.path.expanduser('~/Documents/Allegro')))
        self.pads_output_path.setText(settings.get('pads_output_path', 
            os.path.expanduser('~/Documents/PADS')))
        self.xpedition_output_path.setText(settings.get('xpedition_output_path', 
            os.path.expanduser('~/Documents/Xpedition')))
    
    def save_settings(self):
        """Save account settings"""
        settings = {
            'current_user': self.current_user,
            'user_role': self.user_role,
            'altium_output_path': self.altium_output_path.text(),
            'allegro_output_path': self.allegro_output_path.text(),
            'pads_output_path': self.pads_output_path.text(),
            'xpedition_output_path': self.xpedition_output_path.text(),
        }
        
        if AccountManager.save_account_settings(settings):
            QMessageBox.information(self, 'Success', 'Account settings saved successfully!')
            self.accept()
        else:
            QMessageBox.critical(self, 'Error', 'Failed to save account settings!')
    
    def add_separator(self, layout):
        """Add a separator line"""
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("color: #555;")
        layout.addWidget(separator)
    
    def setup_styling(self):
        """Apply dark theme styling"""
        self.setStyleSheet("""
            QDialog, QFrame {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QLineEdit {
                background-color: #3c3c3c;
                border: 1px solid #555;
                padding: 5px;
                border-radius: 3px;
                color: #ffffff;
            }
            QLineEdit:focus {
                border: 1px solid #0d47a1;
            }
            QPushButton {
                background-color: #4a4a4a;
                border: 1px solid #666;
                padding: 8px 15px;
                border-radius: 3px;
                color: #ffffff;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
            QCheckBox {
                color: #ffffff;
            }
            QCheckBox::indicator:checked {
                background-color: #0d47a1;
            }
            QGroupBox {
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                color: #ffffff;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                background-color: #2b2b2b;
            }
        """)

class LibSiennaFileFormat:
    """Custom file format handler for LibSienna footprint files"""
    MAGIC_HEADER = b'LSFP'
    VERSION = 1

    @staticmethod
    def save_footprint(data, filename):
        """Save footprint data in custom LibSienna format (excluding settings)"""
        try:
            # Create a copy of data without settings that should be stored separately
            footprint_data = data.copy()
            # Remove settings that should be stored separately
            footprint_data.pop('script_output_path', None)
            footprint_data.pop('current_user', None)
            
            with open(filename, 'wb') as f:
                # Write magic header and version
                f.write(LibSiennaFileFormat.MAGIC_HEADER)
                f.write(struct.pack('<I', LibSiennaFileFormat.VERSION))
                
                # Convert data to JSON and compress
                json_data = json.dumps(footprint_data, indent=2)
                compressed_data = json_data.encode('utf-8')
                
                # Write compressed data size and data
                f.write(struct.pack('<I', len(compressed_data)))
                f.write(compressed_data)
                
            print(f"Successfully saved file: {filename}")  # Debug info
            return True
        except Exception as e:
            print(f"Save error: {e}")
            return False

    @staticmethod
    def load_footprint(filename):
        """Load footprint data from custom LibSienna format"""
        try:
            print(f"Attempting to load file: {filename}")  # Debug info
            
            # Check if file exists
            if not os.path.exists(filename):
                print(f"File does not exist: {filename}")
                return None
                
            with open(filename, 'rb') as f:
                # Read and verify magic header
                magic = f.read(4)
                if magic != LibSiennaFileFormat.MAGIC_HEADER:
                    print(f"Invalid file format. Expected {LibSiennaFileFormat.MAGIC_HEADER}, got {magic}")
                    return None
                
                # Read version
                version_data = f.read(4)
                if len(version_data) != 4:
                    print("Could not read version")
                    return None
                    
                version = struct.unpack('<I', version_data)[0]
                print(f"File version: {version}")
                if version != LibSiennaFileFormat.VERSION:
                    print(f"Unsupported version {version}")
                    return None
                
                # Read data size
                size_data = f.read(4)
                if len(size_data) != 4:
                    print("Could not read data size")
                    return None
                    
                data_size = struct.unpack('<I', size_data)[0]
                print(f"Data size: {data_size}")
                
                # Read compressed data
                compressed_data = f.read(data_size)
                if len(compressed_data) != data_size:
                    print(f"Could not read all data. Expected {data_size}, got {len(compressed_data)}")
                    return None
                
                # Decompress and parse JSON
                json_data = compressed_data.decode('utf-8')
                data = json.loads(json_data)
                
                print("Successfully loaded and parsed data")
                return data
                
        except Exception as e:
            print(f"Load error: {e}")
            import traceback
            traceback.print_exc()  # Print full error traceback
            return None

class SettingsManager:
    """Manage application settings separately from footprint data"""
    
    @staticmethod
    def get_settings_file():
        """Get the path to the settings file"""
        home_dir = os.path.expanduser("~")
        settings_dir = os.path.join(home_dir, ".libsienna")
        os.makedirs(settings_dir, exist_ok=True)
        return os.path.join(settings_dir, "settings.json")
    
    @staticmethod
    def save_settings(settings):
        """Save settings to JSON file"""
        try:
            settings_file = SettingsManager.get_settings_file()
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False
    
    @staticmethod
    def load_settings():
        """Load settings from JSON file"""
        try:
            settings_file = SettingsManager.get_settings_file()
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Error loading settings: {e}")
            return {}

class SVGDisplayWidget(QWidget):
    """Widget to display SVG images"""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        

        
        # SVG display area with placeholder
        self.svg_container = QWidget()
        self.svg_container.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border: 2px solid #555;
                border-radius: 5px;
            }
        """)
        svg_layout = QVBoxLayout(self.svg_container)
        
        # Placeholder label
        self.placeholder_label = QLabel("Select a package type\nto view preview")
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_label.setStyleSheet("""
            QLabel {
                color: #888;
                font-size: 14px;
                padding: 50px;
            }
        """)
        svg_layout.addWidget(self.placeholder_label)
        
        # SVG widget (hidden initially)
        self.svg_widget = QSvgWidget()
        self.svg_widget.setVisible(False)
        svg_layout.addWidget(self.svg_widget)
        
        layout.addWidget(self.svg_container)
        
        # Info label
        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("""
            QLabel {
                color: #aaaaaa;
                font-size: 12px;
                padding: 10px;
            }
        """)
        layout.addWidget(self.info_label)
    
    def load_svg(self, svg_path, title="Package Preview"):
        """Load and display SVG file"""
        self.title_label.setText(title)
        
        if svg_path and os.path.exists(svg_path):
            self.svg_widget.load(svg_path)
            self.svg_widget.setVisible(True)
            self.placeholder_label.setVisible(False)
            self.info_label.setText(f"Package: {title}")
        else:
            # Show placeholder SVG or message
            self.svg_widget.setVisible(False)
            self.placeholder_label.setVisible(True)
            self.placeholder_label.setText(f"SVG Preview\n{title}\n\n(Preview file not found)")
            self.info_label.setText("Double-click to configure parameters")
    
    def clear(self):
        """Clear the display"""
        self.svg_widget.setVisible(False)
        self.placeholder_label.setVisible(True)
        self.placeholder_label.setText("Select a package type\nto view preview")
        self.info_label.setText("")

class PackageListWidget(QWidget):
    """Scrollable list of package types"""
    package_selected = pyqtSignal(str, str)  # package_name, svg_path
    package_double_clicked = pyqtSignal(str)  # package_name
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Search bar
        search_layout = QHBoxLayout()
        search_label = QLabel("🔍")
        search_label.setStyleSheet("font-size: 16px;")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search packages...")
        self.search_input.textChanged.connect(self.filter_packages)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)
        
        # Package list
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: #2b2b2b;
                border: 1px solid #555;
                font-size: 13px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #444;
                color: #ffffff;
            }
            QListWidget::item:hover {
                background-color: #3c3c3c;
            }
            QListWidget::item:selected {
                background-color: #0d47a1;
                color: #ffffff;
            }
        """)
        
        # Populate list
        for package_name, svg_path in PACKAGE_TYPES.items():
            item = QListWidgetItem(package_name)
            item.setData(Qt.ItemDataRole.UserRole, svg_path)
            self.list_widget.addItem(item)
        
        # Connect signals
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        layout.addWidget(self.list_widget)
    
    def filter_packages(self, text):
        """Filter package list based on search text"""
        search_text = text.lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item_text = item.text().lower()
            item.setHidden(search_text not in item_text)
    
    def on_item_clicked(self, item):
        """Handle single click - show preview"""
        package_name = item.text()
        svg_path = item.data(Qt.ItemDataRole.UserRole)
        self.package_selected.emit(package_name, svg_path)
    
    def on_item_double_clicked(self, item):
        """Handle double click - navigate to sub-options"""
        package_name = item.text()
        self.package_double_clicked.emit(package_name)

class SubOptionsPage(QWidget):
    """Page showing IPC class options for selected package"""
    back_clicked = pyqtSignal()
    option_selected = pyqtSignal(str)  # IPC class name
    option_double_clicked = pyqtSignal(str, str)  # package_name, ipc_class
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.package_name = ""
        layout = QVBoxLayout(self)
        
        # Header with back button
        header_layout = QHBoxLayout()
        self.back_btn = QPushButton("← Back")
        self.back_btn.setMaximumWidth(100)
        self.back_btn.clicked.connect(self.back_clicked.emit)
        self.back_btn.setStyleSheet("""
            QPushButton {
                background-color: #555;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #666;
            }
        """)
        header_layout.addWidget(self.back_btn)
        
        self.title_label = QLabel("")
        self.title_label.setFixedHeight(35)
        self.title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #00FFFF;
            }
        """)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Splitter for list and SVG
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left: IPC class list
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        label = QLabel("Select Configuration:")
        label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 5px;")
        left_layout.addWidget(label)
        
        self.option_list = QListWidget()
        self.option_list.setStyleSheet("""
            QListWidget {
                background-color: #2b2b2b;
                border: 1px solid #555;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 15px;
                border-bottom: 1px solid #444;
            }
            QListWidget::item:hover {
                background-color: #3c3c3c;
            }
            QListWidget::item:selected {
                background-color: #0d47a1;
            }
        """)
        
        for ipc_class in IPC_CLASSES:
            self.option_list.addItem(ipc_class)
        
        self.option_list.itemClicked.connect(self.on_option_clicked)
        self.option_list.itemDoubleClicked.connect(self.on_option_doubleclicked)
        
        left_layout.addWidget(self.option_list)
        splitter.addWidget(left_widget)
        
        # Right: SVG preview
        self.svg_display = SVGDisplayWidget()
        splitter.addWidget(self.svg_display)
        
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        layout.addWidget(splitter)
    
    def set_package(self, package_name, svg_path):
        """Set the package type"""
        self.package_name = package_name
        self.title_label.setText(f"Configure: {package_name}")
        self.svg_display.load_svg(svg_path, package_name)
    
    def on_option_clicked(self, item):
        """Handle single click - update SVG"""
        ipc_class = item.text()
        self.option_selected.emit(ipc_class)
        # Could load different SVG variant here
    
    def on_option_doubleclicked(self, item):
        """Handle double click - load form into PackageInputTab"""
        ipc_class = item.text()
        print(f"=== DEBUG: Double clicked IPC class: {ipc_class} ===")
        print(f"=== DEBUG: Package name: {self.packagename} ===")
        
        # Get the parent PackageInputTab
        parent_tab = self.parent()
        print(f"=== DEBUG: Parent tab: {parent_tab} ===")
        
        if parent_tab and hasattr(parent_tab, 'load_ipc_form_widget'):
            print("=== DEBUG: Found load_ipc_form_widget method ===")
            
            # Show the form page (index 2)
            if hasattr(parent_tab, 'stack'):
                print(f"=== DEBUG: Setting stack to index 2 ===")
                parent_tab.stack.setCurrentIndex(2)
            
            # Load the appropriate IPC class widget
            print(f"=== DEBUG: Calling load_ipc_form_widget({self.packagename}, {ipc_class}) ===")
            parent_tab.load_ipc_form_widget(self.packagename, ipc_class)
        else:
            print("=== DEBUG: ERROR - parent_tab doesn't have load_ipc_form_widget ===")
        
        self.option_doubleclicked.emit(self.packagename, ipc_class)


    def load_ipc_form_widget(self, package_name, ipc_class):
        """Load the appropriate IPC class widget into the left container"""
        print(f"\n=== DEBUG load_ipc_form_widget START ===")
        print(f"Package: {package_name}, IPC Class: {ipc_class}")
        
        # Clear existing widget in left container
        print(f"Left layout count before clear: {self.left_layout.count()}")
        while self.left_layout.count():
            item = self.left_layout.takeAt(0)
            if item.widget():
                print(f"Removing widget: {item.widget()}")
                item.widget().deleteLater()
        
        print(f"Left layout count after clear: {self.left_layout.count()}")
        
        # Create appropriate widget based on IPC class selection
        print(f"Creating widget for IPC class: {ipc_class}")
        
        if ipc_class == 'Land Pattern':
            print("Creating LandPatternClass...")
            form_widget = LandPatternClass(package_name)
            print(f"LandPatternClass created: {form_widget}")
        elif ipc_class == 'IPC Class A':
            print("Creating IPCClassA...")
            form_widget = IPCClassA(package_name)
        elif ipc_class == 'IPC Class B':
            print("Creating IPCClassB...")
            form_widget = IPCClassB(package_name)
        elif ipc_class == 'IPC Class C':
            print("Creating IPCClassC...")
            form_widget = IPCClassC(package_name)
        else:
            # Fallback placeholder
            print(f"Unknown IPC class, creating placeholder")
            form_widget = QLabel("Unknown IPC class")
            form_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        print(f"Widget type: {type(form_widget)}")
        print(f"Widget visible: {form_widget.isVisible()}")
        
        # Connect signal if widget has it
        if hasattr(form_widget, 'apply_to_footprint'):
            print("Connecting apply_to_footprint signal")
            form_widget.apply_to_footprint.connect(self.handle_footprint_data)
        
        # Add widget to left container
        print(f"Adding widget to left_layout...")
        self.left_layout.addWidget(form_widget)
        form_widget.show()  # Explicitly show
        
        print(f"Left layout count after add: {self.left_layout.count()}")
        print(f"Widget parent: {form_widget.parent()}")
        print("=== DEBUG load_ipc_form_widget END ===\n")
        
        # Update title
        self.form_title.setText(f"{package_name} - {ipc_class}")

class PadInputTab(QWidget):
    """Pad Input tab - Direct copy of existing left panel"""
    
    def __init__(self, parent_designer, parent=None):
        super().__init__(parent)
        self.parent_designer = parent_designer
        
        # Create the exact existing left panel here
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Use the existing create_left_panel logic directly
        left_panel_widget = self.create_existing_left_panel()
        layout.addWidget(left_panel_widget)
    
    def create_existing_left_panel(self):
        """Exact copy of FootprintDesigner.create_left_panel"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Header section
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        header_layout = QGridLayout(header_frame)

        # Header inputs - Row 0
        header_layout.addWidget(QLabel("Part Number:"), 0, 0)
        self.parent_designer.part_number = QLineEdit()
        header_layout.addWidget(self.parent_designer.part_number, 0, 1, 1, 2)
        header_layout.addWidget(QLabel("Footprint Name:"), 0, 3)
        self.parent_designer.footprint_name = QLineEdit()
        header_layout.addWidget(self.parent_designer.footprint_name, 0, 4, 1, 2)

        # Row 1 - Body dimensions and Origin Offset controls
        header_layout.addWidget(QLabel("Body Length:"), 1, 0)
        self.parent_designer.body_length = QLineEdit()
        self.parent_designer.body_length.setText("5.0")
        header_layout.addWidget(self.parent_designer.body_length, 1, 1)
        
        header_layout.addWidget(QLabel("Body Width:"), 1, 2)
        self.parent_designer.body_width = QLineEdit()
        self.parent_designer.body_width.setText("3.0")
        header_layout.addWidget(self.parent_designer.body_width, 1, 3)

        # NEW: Origin offset from top-left corner
        header_layout.addWidget(QLabel("Origin X Offset:"), 1, 4)
        self.parent_designer.origin_offset_x_input = QLineEdit()
        self.parent_designer.origin_offset_x_input.setText("2.5")
        header_layout.addWidget(self.parent_designer.origin_offset_x_input, 1, 5)

        # Row 2 - Body Height, Shape, and Y offset
        header_layout.addWidget(QLabel("Body Height:"), 2, 0)
        self.parent_designer.body_height = QLineEdit()
        self.parent_designer.body_height.setText("1.0")
        header_layout.addWidget(self.parent_designer.body_height, 2, 1)

        header_layout.addWidget(QLabel("Body Shape:"), 2, 2)
        self.parent_designer.body_shape_combobox = QComboBox()
        self.parent_designer.body_shape_combobox.addItems(["rectangle", "round"])
        self.parent_designer.body_shape_combobox.setCurrentIndex(0)
        header_layout.addWidget(self.parent_designer.body_shape_combobox, 2, 3)

        header_layout.addWidget(QLabel("Origin Y Offset:"), 2, 4)
        self.parent_designer.origin_offset_y_input = QLineEdit()
        self.parent_designer.origin_offset_y_input.setText("1.5")
        header_layout.addWidget(self.parent_designer.origin_offset_y_input, 2, 5)

        # Row 3 - Body Chamfer Settings
        header_layout.addWidget(QLabel("Body Chamfer:"), 3, 0)
        self.parent_designer.body_chamfer_input = QLineEdit()
        self.parent_designer.body_chamfer_input.setText("0")
        self.parent_designer.body_chamfer_input.textChanged.connect(self.parent_designer.on_data_changed)
        header_layout.addWidget(self.parent_designer.body_chamfer_input, 3, 1)

        # Corner checkboxes
        corner_layout = QHBoxLayout()
        self.parent_designer.chamfer_tl_checkbox = QCheckBox("TL")
        self.parent_designer.chamfer_tr_checkbox = QCheckBox("TR")
        self.parent_designer.chamfer_bl_checkbox = QCheckBox("BL")
        self.parent_designer.chamfer_br_checkbox = QCheckBox("BR")

        self.parent_designer.chamfer_tl_checkbox.stateChanged.connect(self.parent_designer.on_data_changed)
        self.parent_designer.chamfer_tr_checkbox.stateChanged.connect(self.parent_designer.on_data_changed)
        self.parent_designer.chamfer_bl_checkbox.stateChanged.connect(self.parent_designer.on_data_changed)
        self.parent_designer.chamfer_br_checkbox.stateChanged.connect(self.parent_designer.on_data_changed)

        corner_layout.addWidget(QLabel("Corners:"))
        corner_layout.addWidget(self.parent_designer.chamfer_tl_checkbox)
        corner_layout.addWidget(self.parent_designer.chamfer_tr_checkbox)
        corner_layout.addWidget(self.parent_designer.chamfer_bl_checkbox)
        corner_layout.addWidget(self.parent_designer.chamfer_br_checkbox)

        # Add RefDes input
        corner_layout.addSpacing(20)
        corner_layout.addWidget(QLabel("RefDes:"))
        self.parent_designer.ref_des = QLineEdit()
        self.parent_designer.ref_des.setPlaceholderText("U, IC, etc.")
        self.parent_designer.ref_des.setFixedWidth(80)
        corner_layout.addWidget(self.parent_designer.ref_des)

        corner_widget = QWidget()
        corner_widget.setLayout(corner_layout)
        header_layout.addWidget(corner_widget, 3, 2, 1, 4)

        layout.addWidget(header_frame)

        # Auto-update tracking
        self.parent_designer.auto_update_origin = True

        # Connect signals
        self.parent_designer.body_length.textChanged.connect(self.parent_designer.on_body_dimensions_changed)
        self.parent_designer.body_width.textChanged.connect(self.parent_designer.on_body_dimensions_changed)
        self.parent_designer.origin_offset_x_input.textChanged.connect(self.parent_designer.on_origin_manual_change)
        self.parent_designer.origin_offset_y_input.textChanged.connect(self.parent_designer.on_origin_manual_change)
        
        # Other connections
        self.parent_designer.part_number.textChanged.connect(self.parent_designer.on_data_changed)
        self.parent_designer.footprint_name.textChanged.connect(self.parent_designer.on_data_changed)
        self.parent_designer.body_height.textChanged.connect(self.parent_designer.on_data_changed)
        self.parent_designer.body_shape_combobox.currentTextChanged.connect(self.parent_designer.on_data_changed)

        # Scroll area for padstack, thermal vias, etc.
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.parent_designer.container = QWidget()
        self.parent_designer.container_layout = QVBoxLayout(self.parent_designer.container)
        self.parent_designer.container_layout.addStretch()

        scroll_area.setWidget(self.parent_designer.container)

        # Store reference if needed elsewhere
        self.scroll_area = scroll_area

        # Define auto-scroll method
        def scroll_to_bottom(min_val=None, max_val=None):
            """Auto-scroll to bottom whenever content changes"""
            self.scroll_area.verticalScrollBar().setValue(
                self.scroll_area.verticalScrollBar().maximum()
            )

        # Connect to rangeChanged signal
        scroll_area.verticalScrollBar().rangeChanged.connect(scroll_to_bottom)

        # Initial scroll to bottom
        QTimer.singleShot(0, scroll_to_bottom)

        layout.addWidget(scroll_area)


        # Initialize origin offset
        self.parent_designer.update_origin_offset_values()
        
        # Add initial padstack

        
        return widget

class PackageInputTab(QWidget):
    """Package Input tab with navigation - properly formatted"""
    
    def __init__(self, parent_designer, parent=None):
        super().__init__(parent)
        self.parent_designer = parent_designer 
        self.current_package = ""
        self.current_svg = ""
        self.current_ipc = ""
        
        # Stack widget for navigation
        self.stack = QStackedWidget()
        
        # Page 1: Package type selection
        self.selection_page = self.create_package_selection_page()
        self.stack.addWidget(self.selection_page)
        
        # Page 2: IPC class selection
        self.ipc_page = self.create_ipc_selection_page()
        self.stack.addWidget(self.ipc_page)
        
        # Page 3: Package input form WITH SVG
        self.input_page = self.create_package_input_form()
        self.stack.addWidget(self.input_page)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)
    
    def create_package_selection_page(self):
        """Create package type selection page with list and SVG preview"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(5)  # Reduce spacing between elements
        
        # Splitter for list and preview
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left: Package list with search
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(5, 0, 5, 0)  # Reduced top margin
        left_layout.setSpacing(5)
        
        # Search bar - MORE COMPACT
        search_container = QWidget()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(5)
        
        search_icon = QLabel("🔍")
        search_icon.setStyleSheet("font-size: 14px;")  # Smaller icon
        search_layout.addWidget(search_icon)
        
        self.package_search = QLineEdit()
        self.package_search.setPlaceholderText("Search packages...")
        self.package_search.setStyleSheet("""
            QLineEdit {
                padding: 6px;
                border: 1px solid #555;
                border-radius: 4px;
                background-color: #2b2b2b;
                color: white;
                font-size: 12px;
            }
        """)
        self.package_search.textChanged.connect(self.filter_packages)
        search_layout.addWidget(self.package_search)
        
        left_layout.addWidget(search_container)
        
        # Package list
        self.package_list = QListWidget()
        self.package_list.setStyleSheet("""
            QListWidget {
                background-color: #2b2b2b;
                border: 1px solid #555;
                font-size: 12px;
                padding: 2px;
                outline: none;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #444;
                color: #ffffff;
            }
            QListWidget::item:hover {
                background-color: #3c3c3c;
            }
            QListWidget::item:selected {
                background-color: #0d47a1;
                color: #ffffff;
            }
        """)
        
        # Populate list
        for package_name, svg_path in PACKAGE_TYPES.items():
            item = QListWidgetItem(package_name)
            item.setData(Qt.ItemDataRole.UserRole, svg_path)
            self.package_list.addItem(item)
        
        # Connect signals
        self.package_list.itemClicked.connect(self.on_package_clicked)
        self.package_list.itemDoubleClicked.connect(self.on_package_double_clicked)
        
        left_layout.addWidget(self.package_list)
        
        splitter.addWidget(left_container)
        
        # Right: SVG preview - MORE COMPACT
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(10, 0, 10, 10)  # Reduced top margin
        right_layout.setSpacing(5)
        
        # Title for preview - SMALLER
        self.preview_title = QLabel("SON (Small Outline No-Lead)")
        self.preview_title.setFixedHeight(35)
        self.preview_title.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #00FFFF;
                padding: 5px;
                background-color: transparent;
            }
        """)
        self.preview_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.preview_title)
        
        # SVG display frame
        svg_frame = QFrame()
        svg_frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 2px solid #555;
                border-radius: 8px;
            }
        """)
        svg_frame_layout = QVBoxLayout(svg_frame)
        svg_frame_layout.setContentsMargins(15, 15, 15, 15)  # Slightly reduced padding
        
        # Placeholder text
        self.svg_placeholder = QLabel("SVG Preview\nSON (Small Outline No-Lead)\n\n(Preview file not found)")
        self.svg_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.svg_placeholder.setStyleSheet("""
            QLabel {
                color: #888888;
                font-size: 12px;
                background-color: transparent;
            }
        """)
        svg_frame_layout.addWidget(self.svg_placeholder)
        
        # SVG widget (hidden initially)
        self.svg_widget_1 = QSvgWidget()
        self.svg_widget_1.setVisible(False)
        svg_frame_layout.addWidget(self.svg_widget_1)
        
        right_layout.addWidget(svg_frame)
        

        
        splitter.addWidget(right_container)
        
        # Set splitter sizes
        splitter.setStretchFactor(0, 2)  # List takes 2/5
        splitter.setStretchFactor(1, 3)  # Preview takes 3/5
        
        layout.addWidget(splitter)
        
        return widget
    
    def filter_packages(self, text):
        """Filter package list based on search text"""
        search_text = text.lower()
        for i in range(self.package_list.count()):
            item = self.package_list.item(i)
            item_text = item.text().lower()
            item.setHidden(search_text not in item_text)
    
    def on_package_clicked(self, item):
        """Handle package selection (single click)"""
        self.current_package = item.text()
        self.current_svg = item.data(Qt.ItemDataRole.UserRole)
        self.preview_title.setText(self.current_package)
        
        # Load SVG if exists
        if self.current_svg and os.path.exists(self.current_svg):
            self.svg_widget_1.load(self.current_svg)
            self.svg_widget_1.setVisible(True)
            self.svg_placeholder.setVisible(False)
        else:
            self.svg_widget_1.setVisible(False)
            self.svg_placeholder.setVisible(True)
            self.svg_placeholder.setText(f"SVG Preview\n{self.current_package}\n\n(Preview file not found)")
    
    def on_package_double_clicked(self, item):
        """Handle package double-click - show IPC classes"""
        self.current_package = item.text()
        self.current_svg = item.data(Qt.ItemDataRole.UserRole)
        
        print(f"=== Package double-clicked: {self.current_package} ===")
        
        # Update IPC page
        self.ipc_page_title.setText(f"Configure: {self.current_package}")
        
        # Load SVG if exists
        if self.current_svg and os.path.exists(self.current_svg):
            self.svg_widget_2.load(self.current_svg)
            self.svg_widget_2.setVisible(True)
            self.ipc_svg_placeholder.setVisible(False)
        else:
            self.svg_widget_2.setVisible(False)
            self.ipc_svg_placeholder.setVisible(True)
            self.ipc_svg_placeholder.setText(f"SVG Preview\n{self.current_package}\nPreview file not found")
        
        # Go to IPC selection page
        self.stack.setCurrentIndex(1)
    
    def create_ipc_selection_page(self):
        """Create IPC class selection page"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Header with back button
        header_layout = QHBoxLayout()
        
        back_btn = QPushButton("← Back")
        back_btn.setMaximumWidth(100)
        back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: #555;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #666;
            }
        """)
        header_layout.addWidget(back_btn)
        
        self.ipc_page_title = QLabel("")
        self.ipc_page_title.setFixedHeight(35)
        self.ipc_page_title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #00FFFF;
                padding: 5px;
            }
        """)
        header_layout.addWidget(self.ipc_page_title)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Splitter for IPC list and SVG
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left: IPC class list
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(5, 5, 5, 5)
        
        label = QLabel("Select Land Pattern Configuration:")
        label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px;")
        left_layout.addWidget(label)
        
        self.ipc_list = QListWidget()
        self.ipc_list.setStyleSheet("""
            QListWidget {
                background-color: #2b2b2b;
                border: 1px solid #555;
                font-size: 14px;
                outline: none;
            }
            QListWidget::item {
                padding: 18px;
                border-bottom: 1px solid #444;
            }
            QListWidget::item:hover {
                background-color: #3c3c3c;
            }
            QListWidget::item:selected {
                background-color: #0d47a1;
            }
        """)
        
        for ipc_class in IPC_CLASSES:
            self.ipc_list.addItem(ipc_class)
        
        self.ipc_list.itemClicked.connect(self.on_ipc_clicked)
        self.ipc_list.itemDoubleClicked.connect(self.on_ipc_double_clicked)
        
        left_layout.addWidget(self.ipc_list)
        splitter.addWidget(left_widget)
        
        # Right: SVG preview
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(10, 10, 10, 10)
        
        # SVG display frame
        svg_frame = QFrame()
        svg_frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 2px solid #555;
                border-radius: 8px;
            }
        """)
        svg_frame_layout = QVBoxLayout(svg_frame)
        svg_frame_layout.setContentsMargins(20, 20, 20, 20)
        
        # Placeholder
        self.ipc_svg_placeholder = QLabel("Select a configuration")
        self.ipc_svg_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ipc_svg_placeholder.setStyleSheet("""
            QLabel {
                color: #888888;
                font-size: 14px;
            }
        """)
        svg_frame_layout.addWidget(self.ipc_svg_placeholder)
        
        # SVG widget
        self.svg_widget_2 = QSvgWidget()
        self.svg_widget_2.setVisible(False)
        svg_frame_layout.addWidget(self.svg_widget_2)
        
        right_layout.addWidget(svg_frame)
        
        splitter.addWidget(right_container)
        
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        layout.addWidget(splitter)
        
        return widget
    
    def on_ipc_clicked(self, item):
        """Handle IPC class selection (single click)"""
        ipc_class = item.text()
        # SVG already loaded, just update if needed
    
    def on_ipc_double_clicked(self, item):
        """Handle IPC class double-click - load the form widget"""
        ipc_class = item.text()
        self.current_ipc = ipc_class
        
        print(f"\n=== IPC double-clicked: {ipc_class} ===")
        print(f"Package: {self.current_package}")
        
        # Update form title
        self.form_title.setText(f"{self.current_package} - {ipc_class}")
        
        # Load SVG in form page
        if self.current_svg and os.path.exists(self.current_svg):
            self.svg_widget_3.load(self.current_svg)
            self.svg_widget_3.setVisible(True)
            self.form_svg_placeholder.setVisible(False)
        else:
            self.svg_widget_3.setVisible(False)
            self.form_svg_placeholder.setVisible(True)
        
        # Load the appropriate IPC form widget
        print(f"Calling loadipcformwidget...")
        self.load_ipc_form_widget(self.current_package, ipc_class)
        
        # Go to form page
        print(f"Setting stack to index 2")
        self.stack.setCurrentIndex(2)

    
    def create_package_input_form(self):
        """Create package input form with dynamic IPC class input"""
        widget = QWidget()
        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Header with back button
        header_layout = QHBoxLayout()
        
        back_btn = QPushButton("← Back")
        back_btn.setMaximumWidth(100)
        back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: #555;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #666;
            }
        """)
        header_layout.addWidget(back_btn)
        
        self.form_title = QLabel("Package Configuration")
        self.form_title.setFixedHeight(35)
        self.form_title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #00FFFF;
                padding: 5px;
            }
        """)
        header_layout.addWidget(self.form_title)
        header_layout.addStretch()
        
        main_layout.addLayout(header_layout)
        
        # Main splitter: Left (inputs) and Right (SVG)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # LEFT SIDE: Container for dynamic form widgets
        self.left_container = QWidget()
        self.left_layout = QVBoxLayout(self.left_container)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Placeholder - will be replaced by IPC class widgets
        placeholder = QLabel("Select a package and IPC class to begin")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("color: #888888; font-size: 14px; padding: 50px;")
        self.left_layout.addWidget(placeholder)
        
        main_splitter.addWidget(self.left_container)
        
        # RIGHT SIDE: SVG Preview (stays the same)
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(10, 10, 10, 10)
        
        svg_title = QLabel("Package Preview")
        svg_title.setFixedHeight(25)
        svg_title.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #00FFFF;
                padding: 5px;
            }
        """)
        svg_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(svg_title)
        
        # SVG display frame
        svg_frame = QFrame()
        svg_frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 2px solid #555;
                border-radius: 8px;
            }
        """)
        svg_frame_layout = QVBoxLayout(svg_frame)
        svg_frame_layout.setContentsMargins(20, 20, 20, 20)
        
        # Placeholder
        self.form_svg_placeholder = QLabel("Package preview")
        self.form_svg_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.form_svg_placeholder.setStyleSheet("""
            QLabel {
                color: #888888;
                font-size: 14px;
            }
        """)
        svg_frame_layout.addWidget(self.form_svg_placeholder)
        
        # SVG widget
        self.svg_widget_3 = QSvgWidget()
        self.svg_widget_3.setVisible(False)
        svg_frame_layout.addWidget(self.svg_widget_3)
        
        right_layout.addWidget(svg_frame)
        
        main_splitter.addWidget(right_container)
        
        # Set splitter sizes: inputs take 60%, SVG takes 40%
        main_splitter.setStretchFactor(0, 3)
        main_splitter.setStretchFactor(1, 2)
        
        main_layout.addWidget(main_splitter)
        
        return widget


    def load_ipc_form_widget(self, package_name, ipc_class):
        """Load the appropriate IPC class widget into the left container"""
        print(f"\n=== load_ipc_form_widget START ===")
        print(f"Package: {package_name}, IPC Class: {ipc_class}")
        
        # Check if left_layout exists
        if not hasattr(self, 'left_layout'):
            print("ERROR: left_layout not found!")
            return
        
        print(f"left_layout exists: {self.left_layout}")
        print(f"left_layout count before clear: {self.left_layout.count()}")
        
        # Clear existing widget in left container
        while self.left_layout.count():
            item = self.left_layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                print(f"Removing widget: {widget}")
                widget.setParent(None)
                widget.deleteLater()
        
        print(f"left_layout count after clear: {self.left_layout.count()}")
        
        # Create appropriate widget based on IPC class selection
        print(f"Creating widget for: {ipc_class}")
        
        try:
            if ipc_class == 'Land Pattern':
                print("Creating LandPatternClass...")
                form_widget = LandPatternClass(package_name)
            elif ipc_class == 'IPC Class A':
                print("Creating IPCClassA...")
                form_widget = IPCClassA(package_name)
            elif ipc_class == 'IPC Class B':
                print("Creating IPCClassB...")
                form_widget = IPCClassB(package_name)
            elif ipc_class == 'IPC Class C':
                print("Creating IPCClassC...")
                form_widget = IPCClassC(package_name)
            else:
                print(f"Unknown IPC class: {ipc_class}")
                form_widget = QLabel(f"Unknown IPC class: {ipc_class}")
                form_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
                form_widget.setStyleSheet("color: #FF0000; font-size: 16px;")
            
            print(f"Widget created: {form_widget}")
            print(f"Widget type: {type(form_widget)}")
            
            # IMPORTANT: Pass designer reference to the widget
            if hasattr(self, 'parent_designer'):
                form_widget.designer = self.parent_designer
                print(f"Set designer reference: {self.parent_designer}")
            else:
                print("WARNING: parent_designer not found in PackageInputTab")
            
            # Connect signal if widget has it
            if hasattr(form_widget, 'apply_to_footprint'):
                print("Connecting apply_to_footprint signal...")
                form_widget.apply_to_footprint.connect(self.handle_footprint_data)
            
            # Add widget to left container
            print(f"Adding widget to left_layout...")
            self.left_layout.addWidget(form_widget)
            
            # Force update
            form_widget.show()
            form_widget.update()
            self.left_container.update()
            
            print(f"left_layout count after add: {self.left_layout.count()}")
            print(f"Widget visible: {form_widget.isVisible()}")
            print(f"Widget parent: {form_widget.parent()}")
            print("=== load_ipc_form_widget END ===\n")
            
        except Exception as e:
            print(f"ERROR creating widget: {e}")
            import traceback
            traceback.print_exc()


    def handle_footprint_data(self, data):
        """Handle data emitted from IPC class widgets"""
        print(f"\n=== Footprint data received ===")
        print(f"Data: {data}")
        
        QMessageBox.information(
            self,
            "Footprint Data Ready",
            f"Package: {data.get('package_type', 'N/A')}\n"
            f"IPC Class: {data.get('ipc_class', 'N/A')}\n"
            f"Part Number: {data.get('part_number', 'N/A')}\n"
            f"Footprint Name: {data.get('footprint_name', 'N/A')}\n"
            f"Body: {data.get('body_length', 0)}x{data.get('body_width', 0)}x{data.get('body_height', 0)} mm"
        )


    def generate_package_footprint(self):
        """Generate footprint from package parameters"""
        package_data = {
            'package_type': self.current_package,
            'ipc_class': self.current_ipc,
            'name': self.package_name_input.text(),
            'part_number': self.package_part_input.text(),
            'body_length': float(self.pkg_length_input.text()),
            'body_width': float(self.pkg_width_input.text()),
            'body_height': float(self.pkg_height_input.text()),
            'standoff': float(self.pkg_standoff_input.text()),
            'lead_count': self.lead_count_input.value(),
            'lead_pitch': float(self.lead_pitch_input.text()),
            'lead_width': float(self.lead_width_input.text()),
            'lead_length': float(self.lead_length_input.text()),
            'thermal_width': float(self.thermal_width_input.text()),
            'thermal_height': float(self.thermal_height_input.text()),
        }
        
        print(f"Generating package footprint: {package_data}")
        
        QMessageBox.information(self, "Success", 
                            f"Package footprint generated:\n{self.current_package} - {self.current_ipc}")

# ============================================================================
# IPC CALCULATION ENGINE
# ============================================================================

class IPCCalculationEngine:
    """Base calculation engine for IPC-7351 formulas"""
    
    def __init__(self, ipc_class='B'):
        self.ipc_class = ipc_class
        self.set_tolerances()
    
    def set_tolerances(self):
        """Set IPC tolerance values based on class"""
        if self.ipc_class == 'A':
            self.courtyard_excess = 0.50
            self.J_toe = 0.55
            self.J_heel = 0.45
            self.J_side = 0.05
        elif self.ipc_class == 'B':
            self.courtyard_excess = 0.25
            self.J_toe = 0.35
            self.J_heel = 0.35
            self.J_side = 0.03
        else:
            self.courtyard_excess = 0.10
            self.J_toe = 0.15
            self.J_heel = 0.25
            self.J_side = 0.01
    
    def calculate_qfp_pads(self, lead_length, lead_width, lead_span, pitch):
        """Calculate QFP pad dimensions"""
        CL_tol = 0.10
        CW_tol = 0.05
        CS_tol = 0.10
        
        Zmax = lead_span + CS_tol
        Lmin = lead_length - CL_tol
        Wmin = lead_width - CW_tol
        
        pad_length = (Zmax - 2 * Lmin) / 2 + self.J_toe + self.J_heel
        pad_width = Wmin + 2 * self.J_side
        pad_spacing = Zmax - 2 * pad_length
        
        return round(pad_length, 3), round(pad_width, 3), round(pad_spacing, 3)
    
    def calculate_bga_pads(self, ball_diameter):
        """Calculate BGA pad diameter"""
        if self.ipc_class == 'A':
            return round(ball_diameter * 1.0, 3)
        elif self.ipc_class == 'B':
            return round(ball_diameter * 0.85, 3)
        else:
            return round(ball_diameter * 0.75, 3)


# ============================================================================
# LAND PATTERN CLASS - COMPLETE IMPLEMENTATION
# ============================================================================

class LandPatternClass(QWidget):
    """Land Pattern - Manual entry for selected package type"""
    apply_to_footprint = pyqtSignal(dict)
    
    def __init__(self, package_name, parent=None):
        super().__init__(parent)
        self.package_name = package_name
        self.setup_ui()
    
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Scroll area for all inputs
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #2b2b2b; }")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("QWidget { background-color: #2b2b2b; }")
        self.form_layout = QVBoxLayout(scroll_content)
        self.form_layout.setSpacing(10)
        
        # Add all sections
        self.add_common_inputs()
        self.add_padstack_section()
        self.add_package_specific_inputs()
        
        self.form_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        
        # Apply Button
        apply_btn = QPushButton("✓ Generate Package Footprint")
        apply_btn.clicked.connect(self.generate_and_populate)
        apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #0d47a1;
                color: white;
                font-weight: bold;
                padding: 12px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1565c0;
            }
        """)
        main_layout.addWidget(apply_btn)
    
    def add_common_inputs(self):
        """Add common inputs - REMOVED Package Name, ADDED Footprint Name"""
        common_group = QGroupBox("Package Information")
        common_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                color: #00FFFF;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        common_layout = QGridLayout(common_group)
        common_layout.setSpacing(10)
        
        # Package Type (Read-only display)
        common_layout.addWidget(QLabel("Package Type:"), 0, 0)
        package_display = QLabel(self.package_name)
        package_display.setStyleSheet("QLabel { background-color: #3c3c3c; color: #00FFFF; padding: 5px; font-weight: bold; }")
        common_layout.addWidget(package_display, 0, 1)
        
        # Footprint Name
        common_layout.addWidget(QLabel("Footprint Name:"), 0, 2)
        self.footprint_name = QLineEdit()
        self.footprint_name.setPlaceholderText("e.g., QFP64_0.5mm")
        self.footprint_name.setStyleSheet("QLineEdit { background-color: #3c3c3c; color: white; padding: 5px; }")
        common_layout.addWidget(self.footprint_name, 0, 3)
        
        # Part Number
        common_layout.addWidget(QLabel("Part Number:"), 1, 0)
        self.part_number = QLineEdit()
        self.part_number.setPlaceholderText("e.g., STM32F407VGT6")
        self.part_number.setStyleSheet("QLineEdit { background-color: #3c3c3c; color: white; padding: 5px; }")
        common_layout.addWidget(self.part_number, 1, 1, 1, 3)
        
        self.form_layout.addWidget(common_group)
        
        # Body Dimensions group
        body_group = QGroupBox("Body Dimensions")
        body_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                color: #00FFFF;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        body_layout = QGridLayout(body_group)
        body_layout.setSpacing(10)
        
        # Length
        body_layout.addWidget(QLabel("Length (L) mm:"), 0, 0)
        self.body_length = QDoubleSpinBox()
        self.body_length.setRange(0.1, 100.0)
        self.body_length.setValue(5.0)
        self.body_length.setDecimals(3)
        self.body_length.setStyleSheet("QDoubleSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
        body_layout.addWidget(self.body_length, 0, 1)
        
        # Width
        body_layout.addWidget(QLabel("Width (W) mm:"), 0, 2)
        self.body_width = QDoubleSpinBox()
        self.body_width.setRange(0.1, 100.0)
        self.body_width.setValue(5.0)
        self.body_width.setDecimals(3)
        self.body_width.setStyleSheet("QDoubleSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
        body_layout.addWidget(self.body_width, 0, 3)
        
        # Height
        body_layout.addWidget(QLabel("Height (H) mm:"), 1, 0)
        self.body_height = QDoubleSpinBox()
        self.body_height.setRange(0.1, 20.0)
        self.body_height.setValue(1.0)
        self.body_height.setDecimals(3)
        self.body_height.setStyleSheet("QDoubleSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
        body_layout.addWidget(self.body_height, 1, 1)
        
        
        self.form_layout.addWidget(body_group)
    
    def add_padstack_section(self):
        """Add PadStackRow components"""
        padstack_group = QGroupBox("Pad Configuration")
        padstack_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                color: #00FFFF;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        padstack_layout = QVBoxLayout(padstack_group)
        padstack_layout.setSpacing(10)
        
        # Pad Type and Geometry Row
        type_row = QHBoxLayout()
        
        # Pad Type
        type_group = QGroupBox("Pad Type")
        type_layout = QHBoxLayout(type_group)
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            'square', 'rectangle', 'rounded_rectangle', 'round', 
            'SMD-oblong', 'D-shape', 'PTH', 'NPTH'
        ])
        self.type_combo.setStyleSheet("QComboBox { background-color: #3c3c3c; color: white; padding: 5px; }")
        self.type_combo.currentTextChanged.connect(self.update_geometry_inputs)
        type_layout.addWidget(self.type_combo)
        type_row.addWidget(type_group)
        
        # Geometry
        self.geometry_group = QGroupBox("Geometry")
        self.geometry_layout = QHBoxLayout(self.geometry_group)
        type_row.addWidget(self.geometry_group)
        
        padstack_layout.addLayout(type_row)
        
        # Layer Properties
        layer_group = QGroupBox("Layer Properties")
        layer_layout = QGridLayout(layer_group)
        layer_layout.setSpacing(10)
        
        layer_layout.addWidget(QLabel("Mask Expansion:"), 0, 0)
        self.mask_expansion = QLineEdit("0")
        self.mask_expansion.setMaximumWidth(100)
        self.mask_expansion.setStyleSheet("QLineEdit { background-color: #3c3c3c; color: white; padding: 5px; }")
        layer_layout.addWidget(self.mask_expansion, 0, 1)
        
        layer_layout.addWidget(QLabel("Paste Expansion:"), 0, 2)
        self.paste_expansion = QLineEdit("0")
        self.paste_expansion.setMaximumWidth(100)
        self.paste_expansion.setStyleSheet("QLineEdit { background-color: #3c3c3c; color: white; padding: 5px; }")
        layer_layout.addWidget(self.paste_expansion, 0, 3)
        
        layer_layout.addWidget(QLabel("Mask Enabled:"), 1, 0)
        self.mask_enabled = QCheckBox()
        self.mask_enabled.setChecked(True)
        layer_layout.addWidget(self.mask_enabled, 1, 1)
        
        layer_layout.addWidget(QLabel("Paste Enabled:"), 1, 2)
        self.paste_enabled = QCheckBox()
        self.paste_enabled.setChecked(True)
        layer_layout.addWidget(self.paste_enabled, 1, 3)
        
        padstack_layout.addWidget(layer_group)
        self.form_layout.addWidget(padstack_group)
        
        # Initialize geometry
        self.update_geometry_inputs()
    
    def update_geometry_inputs(self):
        """Update geometry based on pad type"""
        # Clear existing
        while self.geometry_layout.count():
            item = self.geometry_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        pad_type = self.type_combo.currentText()
        
        if pad_type == 'square':
            self.geometry_layout.addWidget(QLabel("Size:"))
            self.size_input = QLineEdit("1.0")
            self.size_input.setMaximumWidth(100)
            self.size_input.setStyleSheet("QLineEdit { background-color: #3c3c3c; color: white; padding: 5px; }")
            self.geometry_layout.addWidget(self.size_input)
            
        elif pad_type in ['rectangle', 'rounded_rectangle', 'SMD-oblong']:
            self.geometry_layout.addWidget(QLabel("Length:"))
            self.length_input = QLineEdit("1.5")
            self.length_input.setMaximumWidth(100)
            self.length_input.setStyleSheet("QLineEdit { background-color: #3c3c3c; color: white; padding: 5px; }")
            self.geometry_layout.addWidget(self.length_input)
            
            self.geometry_layout.addWidget(QLabel("Width:"))
            self.width_input = QLineEdit("0.3")
            self.width_input.setMaximumWidth(100)
            self.width_input.setStyleSheet("QLineEdit { background-color: #3c3c3c; color: white; padding: 5px; }")
            self.geometry_layout.addWidget(self.width_input)
            
        elif pad_type == 'round':
            self.geometry_layout.addWidget(QLabel("Diameter:"))
            self.diameter_input = QLineEdit("1.0")
            self.diameter_input.setMaximumWidth(100)
            self.diameter_input.setStyleSheet("QLineEdit { background-color: #3c3c3c; color: white; padding: 5px; }")
            self.geometry_layout.addWidget(self.diameter_input)
            
        elif pad_type in ['PTH', 'NPTH']:
            self.geometry_layout.addWidget(QLabel("Hole Ø:"))
            self.hole_diameter_input = QLineEdit("0.8")
            self.hole_diameter_input.setMaximumWidth(100)
            self.hole_diameter_input.setStyleSheet("QLineEdit { background-color: #3c3c3c; color: white; padding: 5px; }")
            self.geometry_layout.addWidget(self.hole_diameter_input)
            
            if pad_type == 'PTH':
                self.geometry_layout.addWidget(QLabel("Pad Ø:"))
                self.pad_diameter_input = QLineEdit("1.2")
                self.pad_diameter_input.setMaximumWidth(100)
                self.pad_diameter_input.setStyleSheet("QLineEdit { background-color: #3c3c3c; color: white; padding: 5px; }")
                self.geometry_layout.addWidget(self.pad_diameter_input)
        
        self.geometry_layout.addStretch()
    
    def add_package_specific_inputs(self):
        """Add package-specific inputs - EXPANDED with all missing packages"""
        package_group = QGroupBox(f"{self.package_name} Parameters")
        package_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                color: #00FFFF;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        package_layout = QGridLayout(package_group)
        package_layout.setSpacing(10)
        
        # SOT23/SOT89/SOT143/SOT223/SOTFL packages
        if any(pkg in self.package_name for pkg in ['SOT23', 'SOT89', 'SOT143', 'SOT223', 'SOTFL']):
            package_layout.addWidget(QLabel("Pin Count:"), 0, 0)
            self.pin_count = QSpinBox()
            self.pin_count.setRange(3, 8)
            self.pin_count.setValue(3)
            self.pin_count.setStyleSheet("QSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.pin_count, 0, 1)
            
            package_layout.addWidget(QLabel("Pin Pitch mm:"), 0, 2)
            self.pin_pitch = QDoubleSpinBox()
            self.pin_pitch.setRange(0.5, 2.54)
            self.pin_pitch.setValue(0.95)
            self.pin_pitch.setDecimals(3)
            self.pin_pitch.setStyleSheet("QDoubleSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.pin_pitch, 0, 3)
            
            package_layout.addWidget(QLabel("Lead Width mm:"), 1, 0)
            self.lead_width = QDoubleSpinBox()
            self.lead_width.setRange(0.2, 2.0)
            self.lead_width.setValue(0.6)
            self.lead_width.setDecimals(3)
            self.lead_width.setStyleSheet("QDoubleSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.lead_width, 1, 1)
            
            package_layout.addWidget(QLabel("Lead Length mm:"), 1, 2)
            self.lead_length = QDoubleSpinBox()
            self.lead_length.setRange(0.3, 2.0)
            self.lead_length.setValue(1.0)
            self.lead_length.setDecimals(3)
            self.lead_length.setStyleSheet("QDoubleSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.lead_length, 1, 3)
        
        # DPAK packages
        elif 'DPAK' in self.package_name:
            package_layout.addWidget(QLabel("Pin Count:"), 0, 0)
            self.pin_count = QSpinBox()
            self.pin_count.setRange(3, 5)
            self.pin_count.setValue(3)
            self.pin_count.setStyleSheet("QSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.pin_count, 0, 1)
            
            package_layout.addWidget(QLabel("Pin Pitch mm:"), 0, 2)
            self.pin_pitch = QDoubleSpinBox()
            self.pin_pitch.setRange(1.0, 3.0)
            self.pin_pitch.setValue(2.286)
            self.pin_pitch.setDecimals(3)
            self.pin_pitch.setStyleSheet("QDoubleSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.pin_pitch, 0, 3)
            
            package_layout.addWidget(QLabel("Tab Width mm:"), 1, 0)
            self.tab_width = QDoubleSpinBox()
            self.tab_width.setRange(3.0, 10.0)
            self.tab_width.setValue(5.6)
            self.tab_width.setDecimals(3)
            self.tab_width.setStyleSheet("QDoubleSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.tab_width, 1, 1)
            
            package_layout.addWidget(QLabel("Tab Length mm:"), 1, 2)
            self.tab_length = QDoubleSpinBox()
            self.tab_length.setRange(3.0, 10.0)
            self.tab_length.setValue(5.7)
            self.tab_length.setDecimals(3)
            self.tab_length.setStyleSheet("QDoubleSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.tab_length, 1, 3)
        
        # SOJ/SOP/SOIC packages
        elif any(pkg in self.package_name for pkg in ['SOJ', 'SOP', 'SOIC', 'SOF']):
            package_layout.addWidget(QLabel("Lead Count:"), 0, 0)
            self.lead_count = QSpinBox()
            self.lead_count.setValue(16)
            self.lead_count.setStyleSheet("QSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.lead_count, 0, 1)
            
            package_layout.addWidget(QLabel("Pitch mm:"), 0, 2)
            self.lead_pitch = QLineEdit()
            self.lead_pitch.setText("1.27")
            self.lead_pitch.setStyleSheet("QDoubleSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.lead_pitch, 0, 3)
            
            package_layout.addWidget(QLabel("Lead X Span mm:"), 1, 0)
            self.lead_x_span = QLineEdit()
            self.lead_x_span.setText("5.4")
            self.lead_x_span.setStyleSheet("QDoubleSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.lead_x_span, 1, 1)
            
        

        # QFP/LQFP/BQFP/PQFP/CQFP packages
        elif any(pkg in self.package_name for pkg in ['QFP', 'LQFP', 'BQFP', 'PQFP', 'CQFP', 'CFP']):
            # Lead counts
            package_layout.addWidget(QLabel("Lead Count X:"), 0, 0)
            self.lead_countx = QSpinBox()
            self.lead_countx.setRange(2, 64)
            self.lead_countx.setValue(8)
            self.lead_countx.setStyleSheet("QSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.lead_countx, 0, 1)

            package_layout.addWidget(QLabel("Lead Count Y:"), 0, 2)
            self.lead_county = QSpinBox()
            self.lead_county.setRange(2, 64)
            self.lead_county.setValue(8)
            self.lead_county.setStyleSheet("QSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.lead_county, 0, 3)

            # Pitch between pads on same side
            package_layout.addWidget(QLabel("Pitch X mm:"), 1, 0)
            self.lead_pitchx = QLineEdit()
            self.lead_pitchx.setText("0.5")
            self.lead_pitchx.setStyleSheet("QLineEdit { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.lead_pitchx, 1, 1)

            package_layout.addWidget(QLabel("Pitch Y mm:"), 1, 2)
            self.lead_pitchy = QLineEdit()
            self.lead_pitchy.setText("0.5")
            self.lead_pitchy.setStyleSheet("QLineEdit { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.lead_pitchy, 1, 3)

            # Distance between opposite sides (row-to-row, column-to-column)
            package_layout.addWidget(QLabel("Lead X Span mm:"), 2, 0)
            self.lead_x_pitch = QLineEdit()
            self.lead_x_pitch.setText("7.0")
            self.lead_x_pitch.setStyleSheet("QLineEdit { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.lead_x_pitch, 2, 1)

            package_layout.addWidget(QLabel("Lead Y Span mm:"), 2, 2)
            self.lead_y_pitch = QLineEdit()
            self.lead_y_pitch.setText("7.0")
            self.lead_y_pitch.setStyleSheet("QLineEdit { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.lead_y_pitch, 2, 3)      

        
        # BGA packages
        elif 'BGA' in self.package_name:
            # Ball Rows
            package_layout.addWidget(QLabel("Ball Rows:"), 0, 0)
            self.ball_rows = QSpinBox()
            self.ball_rows.setRange(2, 50)
            self.ball_rows.setValue(10)
            self.ball_rows.setStyleSheet("QSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.ball_rows, 0, 1)
            
            # Ball Columns
            package_layout.addWidget(QLabel("Ball Columns:"), 0, 2)
            self.ball_columns = QSpinBox()
            self.ball_columns.setRange(2, 50)
            self.ball_columns.setValue(10)
            self.ball_columns.setStyleSheet("QSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.ball_columns, 0, 3)
            
            # Ball Pitch X (horizontal spacing)
            package_layout.addWidget(QLabel("Ball Pitch X mm:"), 1, 0)
            self.ball_pitch_x = QDoubleSpinBox()
            self.ball_pitch_x.setRange(0.3, 2.0)
            self.ball_pitch_x.setValue(0.8)
            self.ball_pitch_x.setDecimals(3)
            self.ball_pitch_x.setStyleSheet("QDoubleSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.ball_pitch_x, 1, 1)
            
            # Ball Pitch Y (vertical spacing)
            package_layout.addWidget(QLabel("Ball Pitch Y mm:"), 1, 2)
            self.ball_pitch_y = QDoubleSpinBox()
            self.ball_pitch_y.setRange(0.3, 2.0)
            self.ball_pitch_y.setValue(0.8)
            self.ball_pitch_y.setDecimals(3)
            self.ball_pitch_y.setStyleSheet("QDoubleSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.ball_pitch_y, 1, 3)
        
        # QFN/SON/DFN/PQFN/PSON packages
        elif any(pkg in self.package_name for pkg in ['QFN', 'SON', 'DFN', 'PQFN', 'PSON']):
            package_layout.addWidget(QLabel("Pin Count:"), 0, 0)
            self.pin_count = QSpinBox()
            self.pin_count.setRange(6, 128)
            self.pin_count.setValue(32)
            self.pin_count.setStyleSheet("QSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.pin_count, 0, 1)
            
            package_layout.addWidget(QLabel("Pin Pitch mm:"), 0, 2)
            self.pin_pitch = QDoubleSpinBox()
            self.pin_pitch.setRange(0.35, 1.0)
            self.pin_pitch.setValue(0.5)
            self.pin_pitch.setDecimals(3)
            self.pin_pitch.setStyleSheet("QDoubleSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.pin_pitch, 0, 3)
            
            package_layout.addWidget(QLabel("Pad Width mm:"), 1, 0)
            self.pad_width_input = QDoubleSpinBox()
            self.pad_width_input.setRange(0.15, 0.5)
            self.pad_width_input.setValue(0.25)
            self.pad_width_input.setDecimals(3)
            self.pad_width_input.setStyleSheet("QDoubleSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.pad_width_input, 1, 1)
            
            package_layout.addWidget(QLabel("Pad Length mm:"), 1, 2)
            self.pad_length_input = QDoubleSpinBox()
            self.pad_length_input.setRange(0.3, 1.0)
            self.pad_length_input.setValue(0.6)
            self.pad_length_input.setDecimals(3)
            self.pad_length_input.setStyleSheet("QDoubleSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.pad_length_input, 1, 3)
        
        # LCC/PLCC packages
        elif any(pkg in self.package_name for pkg in ['LCC', 'PLCC']):
            package_layout.addWidget(QLabel("Contact Count:"), 0, 0)
            self.contact_count = QSpinBox()
            self.contact_count.setRange(20, 84)
            self.contact_count.setValue(44)
            self.contact_count.setStyleSheet("QSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.contact_count, 0, 1)
            
            package_layout.addWidget(QLabel("Contact Pitch mm:"), 0, 2)
            self.contact_pitch = QDoubleSpinBox()
            self.contact_pitch.setRange(1.0, 1.27)
            self.contact_pitch.setValue(1.27)
            self.contact_pitch.setDecimals(3)
            self.contact_pitch.setStyleSheet("QDoubleSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.contact_pitch, 0, 3)
        
        # LGA packages
        elif 'LGA' in self.package_name:
            package_layout.addWidget(QLabel("Pad Rows:"), 0, 0)
            self.pad_rows = QSpinBox()
            self.pad_rows.setRange(2, 20)
            self.pad_rows.setValue(5)
            self.pad_rows.setStyleSheet("QSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.pad_rows, 0, 1)
            
            package_layout.addWidget(QLabel("Pad Columns:"), 0, 2)
            self.pad_columns = QSpinBox()
            self.pad_columns.setRange(2, 20)
            self.pad_columns.setValue(5)
            self.pad_columns.setStyleSheet("QSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.pad_columns, 0, 3)
            
            package_layout.addWidget(QLabel("Pad Pitch mm:"), 1, 0)
            self.pad_pitch = QDoubleSpinBox()
            self.pad_pitch.setRange(0.5, 2.0)
            self.pad_pitch.setValue(0.8)
            self.pad_pitch.setDecimals(3)
            self.pad_pitch.setStyleSheet("QDoubleSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.pad_pitch, 1, 1)
        
        # DIP/SIP packages (Through-hole)
        elif any(pkg in self.package_name for pkg in ['DIP', 'SIP']):
            package_layout.addWidget(QLabel("Pin Count:"), 0, 0)
            self.pin_count = QSpinBox()
            self.pin_count.setRange(4, 64)
            self.pin_count.setValue(16)
            self.pin_count.setStyleSheet("QSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.pin_count, 0, 1)
            
            package_layout.addWidget(QLabel("Pin Pitch mm:"), 0, 2)
            self.pin_pitch = QDoubleSpinBox()
            self.pin_pitch.setRange(2.0, 2.54)
            self.pin_pitch.setValue(2.54)
            self.pin_pitch.setDecimals(3)
            self.pin_pitch.setStyleSheet("QDoubleSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.pin_pitch, 0, 3)
            
            package_layout.addWidget(QLabel("Hole Diameter mm:"), 1, 0)
            self.hole_diameter = QDoubleSpinBox()
            self.hole_diameter.setRange(0.6, 1.5)
            self.hole_diameter.setValue(0.8)
            self.hole_diameter.setDecimals(3)
            self.hole_diameter.setStyleSheet("QDoubleSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.hole_diameter, 1, 1)
            
            package_layout.addWidget(QLabel("Pad Diameter mm:"), 1, 2)
            self.pad_diameter_input = QDoubleSpinBox()
            self.pad_diameter_input.setRange(1.0, 2.5)
            self.pad_diameter_input.setValue(1.5)
            self.pad_diameter_input.setDecimals(3)
            self.pad_diameter_input.setStyleSheet("QDoubleSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.pad_diameter_input, 1, 3)
        
        # CAN/CAN-FM packages
        elif any(pkg in self.package_name for pkg in ['CAN', 'PCY']):
            package_layout.addWidget(QLabel("Pin Count:"), 0, 0)
            self.pin_count = QSpinBox()
            self.pin_count.setRange(3, 12)
            self.pin_count.setValue(3)
            self.pin_count.setStyleSheet("QSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.pin_count, 0, 1)
            
            package_layout.addWidget(QLabel("Pin Circle Ø mm:"), 0, 2)
            self.pin_circle_diameter = QDoubleSpinBox()
            self.pin_circle_diameter.setRange(3.0, 15.0)
            self.pin_circle_diameter.setValue(5.08)
            self.pin_circle_diameter.setDecimals(3)
            self.pin_circle_diameter.setStyleSheet("QDoubleSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.pin_circle_diameter, 0, 3)
        
        # MELF/SODFL packages
        elif any(pkg in self.package_name for pkg in ['MELF', 'SODFL']):
            package_layout.addWidget(QLabel("Pad Width mm:"), 0, 0)
            self.pad_width_input = QDoubleSpinBox()
            self.pad_width_input.setRange(0.5, 2.0)
            self.pad_width_input.setValue(1.0)
            self.pad_width_input.setDecimals(3)
            self.pad_width_input.setStyleSheet("QDoubleSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.pad_width_input, 0, 1)
            
            package_layout.addWidget(QLabel("Pad Length mm:"), 0, 2)
            self.pad_length_input = QDoubleSpinBox()
            self.pad_length_input.setRange(0.5, 2.0)
            self.pad_length_input.setValue(1.2)
            self.pad_length_input.setDecimals(3)
            self.pad_length_input.setStyleSheet("QDoubleSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.pad_length_input, 0, 3)
            
            package_layout.addWidget(QLabel("Pad Spacing mm:"), 1, 0)
            self.pad_spacing = QDoubleSpinBox()
            self.pad_spacing.setRange(1.0, 5.0)
            self.pad_spacing.setValue(2.5)
            self.pad_spacing.setDecimals(3)
            self.pad_spacing.setStyleSheet("QDoubleSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.pad_spacing, 1, 1)
        
        # Chip Components/Chip Array/CAPAE/Molded packages
        elif any(pkg in self.package_name for pkg in ['Chip', 'CAPAE', 'Molded', 'Precision Wire']):
            package_layout.addWidget(QLabel("Terminal Width mm:"), 0, 0)
            self.terminal_width = QDoubleSpinBox()
            self.terminal_width.setRange(0.2, 3.0)
            self.terminal_width.setValue(0.6)
            self.terminal_width.setDecimals(3)
            self.terminal_width.setStyleSheet("QDoubleSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.terminal_width, 0, 1)
            
            package_layout.addWidget(QLabel("Terminal Length mm:"), 0, 2)
            self.terminal_length = QDoubleSpinBox()
            self.terminal_length.setRange(0.2, 2.0)
            self.terminal_length.setValue(0.5)
            self.terminal_length.setDecimals(3)
            self.terminal_length.setStyleSheet("QDoubleSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.terminal_length, 0, 3)
        
        # FM (Flange Mount) packages
        elif 'FM' in self.package_name:
            package_layout.addWidget(QLabel("Mounting Holes:"), 0, 0)
            self.mounting_holes = QSpinBox()
            self.mounting_holes.setRange(2, 4)
            self.mounting_holes.setValue(2)
            self.mounting_holes.setStyleSheet("QSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.mounting_holes, 0, 1)
            
            package_layout.addWidget(QLabel("Hole Diameter mm:"), 0, 2)
            self.hole_diameter = QDoubleSpinBox()
            self.hole_diameter.setRange(2.0, 5.0)
            self.hole_diameter.setValue(3.2)
            self.hole_diameter.setDecimals(3)
            self.hole_diameter.setStyleSheet("QDoubleSpinBox { background-color: #3c3c3c; color: white; padding: 5px; }")
            package_layout.addWidget(self.hole_diameter, 0, 3)
        
        self.form_layout.addWidget(package_group)
        
    
    def calculate_pad_positions(self):
        """Calculate pad positions based on package type - EXPANDED for all packages"""
        positions = []
        
        # ========== SOT23/SOT89/SOT143/SOT223/SOTFL ==========
        if any(pkg in self.package_name for pkg in ['SOT23', 'SOT89', 'SOT143', 'SOT223', 'SOTFL']):
            pin_count = self.pin_count.value()
            pitch = self.pin_pitch.value()
            body_width = self.body_width.value()
            
            try:
                pad_length = float(self.length_input.text()) if hasattr(self, 'length_input') else 1.0
            except:
                pad_length = 1.0
            
            if pin_count == 3:
                # SOT-23-3: 2 pins on one side, 1 on the other
                positions.append({'pin': 1, 'x': -pitch/2, 'y': -body_width/2 - pad_length/2})
                positions.append({'pin': 2, 'x': pitch/2, 'y': -body_width/2 - pad_length/2})
                positions.append({'pin': 3, 'x': 0, 'y': body_width/2 + pad_length/2})
            elif pin_count == 5:
                # SOT-23-5: 3 pins on one side, 2 on the other
                for i in range(3):
                    x = -pitch + i * pitch
                    y = -body_width/2 - pad_length/2
                    positions.append({'pin': i+1, 'x': round(x, 3), 'y': round(y, 3)})
                for i in range(2):
                    x = -pitch/2 + i * pitch
                    y = body_width/2 + pad_length/2
                    positions.append({'pin': 3+i+1, 'x': round(x, 3), 'y': round(y, 3)})
            elif pin_count == 6:
                # SOT-23-6: 3 pins on each side
                for i in range(3):
                    x = -pitch + i * pitch
                    y = -body_width/2 - pad_length/2
                    positions.append({'pin': i+1, 'x': round(x, 3), 'y': round(y, 3)})
                for i in range(3):
                    x = pitch - i * pitch
                    y = body_width/2 + pad_length/2
                    positions.append({'pin': 3+i+1, 'x': round(x, 3), 'y': round(y, 3)})
            else:
                # Generic SOT with even distribution
                pads_per_side = pin_count // 2
                for i in range(pads_per_side):
                    x = -(pads_per_side-1)*pitch/2 + i * pitch
                    y = -body_width/2 - pad_length/2
                    positions.append({'pin': i+1, 'x': round(x, 3), 'y': round(y, 3)})
                for i in range(pin_count - pads_per_side):
                    x = (pads_per_side-1)*pitch/2 - i * pitch
                    y = body_width/2 + pad_length/2
                    positions.append({'pin': pads_per_side+i+1, 'x': round(x, 3), 'y': round(y, 3)})
        
        # ========== DPAK ==========
        elif 'DPAK' in self.package_name:
            pin_count = self.pin_count.value()
            pitch = self.pin_pitch.value()
            tab_width = self.tab_width.value()
            
            try:
                pad_length = float(self.length_input.text()) if hasattr(self, 'length_input') else 2.0
            except:
                pad_length = 2.0
            
            # Small pins (usually 2)
            small_pins = pin_count - 1
            for i in range(small_pins):
                x = -(small_pins-1)*pitch/2 + i * pitch
                y = -5.0  # Typical DPAK offset
                positions.append({'pin': i+1, 'x': round(x, 3), 'y': round(y, 3)})
            
            # Large tab (drain/collector)
            positions.append({'pin': pin_count, 'x': 0, 'y': 2.0})
        
        # ========== SOJ/SOP/SOIC/SOF ==========
        elif any(pkg in self.package_name for pkg in ['SOJ', 'SOP', 'SOIC', 'SOF']):
            # Get lead count from UI (QSpinBox)
            lead_count = self.lead_count.value()  # Total number of leads (e.g., 16)
            
            # Get pitch from UI with try-except (QLineEdit)
            try:
                pitch = float(self.lead_pitch.text())  # Pitch between leads (e.g., 1.27 mm)
            except:
                pitch = 1.27  # Default if input is invalid
            
            # Get lead X span from UI with try-except (QLineEdit)
            try:
                lead_x_span = float(self.lead_x_span.text())  # Distance between lead centers (e.g., 5.4 mm)
            except:
                lead_x_span = 5.4  # Default if input is invalid
            
            # Calculate number of pads per side
            pads_per_side = lead_count // 2
            
            # Calculate starting Y position (centered at 0)
            total_height = (pads_per_side - 1) * pitch
            start_y = total_height / 2
            
            # LEFT side pads (pins 1 to pads_per_side) - TOP to BOTTOM - No rotation (0°)
            for i in range(pads_per_side):
                pin = i + 1
                x = -lead_x_span / 2  # Left side X position
                y = start_y - (i * pitch)  # Start from top, go down
                
                positions.append({
                    'pin': pin,
                    'x': round(x, 3),
                    'y': round(y, 3),
                    'rotation': 0
                })
            
            # RIGHT side pads (pins pads_per_side+1 to lead_count) - BOTTOM to TOP - No rotation (0°)
            for i in range(pads_per_side):
                pin = pads_per_side + i + 1
                x = lead_x_span / 2  # Right side X position
                y = -start_y + (i * pitch)  # Start from bottom, go up
                
                positions.append({
                    'pin': pin,
                    'x': round(x, 3),
                    'y': round(y, 3),
                    'rotation': 0
                })
                    

       # ========== QFP/LQFP/BQFP/PQFP/CQFP/CFP ==========
        elif any(pkg in self.package_name for pkg in ['QFP', 'LQFP', 'BQFP', 'PQFP', 'CQFP', 'CFP']):
            lead_count_x = self.lead_countx.value()  # Pads on top/bottom
            lead_count_y = self.lead_county.value()  # Pads on left/right

            try:
                pitch_x = float(self.lead_pitchx.text())  # Spacing between pads on top/bottom
            except:
                pitch_x = 0.5

            try:
                pitch_y = float(self.lead_pitchy.text())  # Spacing between pads on left/right
            except:
                pitch_y = 0.5

            try:
                span_x = float(self.lead_x_pitch.text())  # Distance between left and right columns
            except:
                span_x = 7.0

            try:
                span_y = float(self.lead_y_pitch.text())  # Distance between top and bottom rows
            except:
                span_y = 7.0

            try:
                pad_length = float(self.length_input.text()) if hasattr(self, 'length_input') else 0.6
            except:
                pad_length = 0.6

            # LEFT side (pins 1 to lead_count_y) - TOP to BOTTOM - No rotation (0°)
            for i in range(lead_count_y):
                x = -span_x / 2
                y = (lead_count_y - 1) * pitch_y / 2 - i * pitch_y
                positions.append({'pin': i + 1, 'x': round(x, 3), 'y': round(y, 3), 'rotation': 0})

            # BOTTOM side (pins lead_count_y+1 to lead_count_y+lead_count_x) - LEFT to RIGHT - 90° rotation
            for i in range(lead_count_x):
                x = -(lead_count_x - 1) * pitch_x / 2 + i * pitch_x
                y = -span_y / 2
                positions.append({'pin': lead_count_y + i + 1, 'x': round(x, 3), 'y': round(y, 3), 'rotation': 90})

            # RIGHT side (pins lead_count_y+lead_count_x+1 to 2*lead_count_y+lead_count_x) - BOTTOM to TOP - No rotation (0°)
            for i in range(lead_count_y):
                x = span_x / 2
                y = -(lead_count_y - 1) * pitch_y / 2 + i * pitch_y
                positions.append({'pin': lead_count_y + lead_count_x + i + 1, 'x': round(x, 3), 'y': round(y, 3), 'rotation': 0})

            # TOP side (pins 2*lead_count_y+lead_count_x+1 to 2*lead_count_y+2*lead_count_x) - RIGHT to LEFT - 90° rotation
            for i in range(lead_count_x):
                x = (lead_count_x - 1) * pitch_x / 2 - i * pitch_x
                y = span_y / 2
                positions.append({'pin': 2 * lead_count_y + lead_count_x + i + 1, 'x': round(x, 3), 'y': round(y, 3), 'rotation': 90})



        # ========== BGA ==========
        elif 'BGA' in self.package_name:
            # Get inputs from UI
            rows = self.ball_rows.value()
            cols = self.ball_columns.value()
            pitch_x = self.ball_pitch_x.value()  # Horizontal spacing
            pitch_y = self.ball_pitch_y.value()  # Vertical spacing
            
            # Calculate starting positions (centered at 0,0)
            start_x = -(cols - 1) * pitch_x / 2
            start_y = -(rows - 1) * pitch_y / 2
            
            # Generate ball positions
            pin = 1
            for row in range(rows):
                for col in range(cols):
                    x = start_x + col * pitch_x  # Use pitch_x for horizontal spacing
                    y = start_y + row * pitch_y  # Use pitch_y for vertical spacing
                    
                    positions.append({
                        'pin': pin,
                        'x': round(x, 3),
                        'y': round(y, 3),
                        'rotation': 0
                    })
                    pin += 1

        
        # ========== QFN/SON/DFN/PQFN/PSON ==========
        elif any(pkg in self.package_name for pkg in ['QFN', 'SON', 'DFN', 'PQFN', 'PSON']):
            pin_count = self.pin_count.value()
            pitch = self.pin_pitch.value()
            body_len = self.body_length.value()
            body_wid = self.body_width.value()
            
            try:
                pad_length = float(self.pad_length_input.value()) if hasattr(self, 'pad_length_input') else 0.6
            except:
                pad_length = 0.6
            
            pads_per_side = pin_count // 4
            
            # Bottom side
            for i in range(pads_per_side):
                x = -(pads_per_side-1)*pitch/2 + i * pitch
                y = -body_wid/2
                positions.append({'pin': i+1, 'x': round(x, 3), 'y': round(y, 3)})
            
            # Right side
            for i in range(pads_per_side):
                x = body_len/2
                y = -(pads_per_side-1)*pitch/2 + i * pitch
                positions.append({'pin': pads_per_side+i+1, 'x': round(x, 3), 'y': round(y, 3)})
            
            # Top side
            for i in range(pads_per_side):
                x = (pads_per_side-1)*pitch/2 - i * pitch
                y = body_wid/2
                positions.append({'pin': 2*pads_per_side+i+1, 'x': round(x, 3), 'y': round(y, 3)})
            
            # Left side
            for i in range(pads_per_side):
                x = -body_len/2
                y = (pads_per_side-1)*pitch/2 - i * pitch
                positions.append({'pin': 3*pads_per_side+i+1, 'x': round(x, 3), 'y': round(y, 3)})
        
        # ========== LCC/PLCC ==========
        elif any(pkg in self.package_name for pkg in ['LCC', 'PLCC']):
            contact_count = self.contact_count.value()
            pitch = self.contact_pitch.value()
            body_len = self.body_length.value()
            body_wid = self.body_width.value()
            
            pads_per_side = contact_count // 4
            
            # Similar to QFP but pads are on the edge
            for i in range(pads_per_side):
                x = -(pads_per_side-1)*pitch/2 + i * pitch
                y = -body_wid/2
                positions.append({'pin': i+1, 'x': round(x, 3), 'y': round(y, 3)})
            
            for i in range(pads_per_side):
                x = body_len/2
                y = -(pads_per_side-1)*pitch/2 + i * pitch
                positions.append({'pin': pads_per_side+i+1, 'x': round(x, 3), 'y': round(y, 3)})
            
            for i in range(pads_per_side):
                x = (pads_per_side-1)*pitch/2 - i * pitch
                y = body_wid/2
                positions.append({'pin': 2*pads_per_side+i+1, 'x': round(x, 3), 'y': round(y, 3)})
            
            for i in range(pads_per_side):
                x = -body_len/2
                y = (pads_per_side-1)*pitch/2 - i * pitch
                positions.append({'pin': 3*pads_per_side+i+1, 'x': round(x, 3), 'y': round(y, 3)})
        
        # ========== LGA ==========
        elif 'LGA' in self.package_name:
            rows = self.pad_rows.value()
            cols = self.pad_columns.value()
            pitch = self.pad_pitch.value()
            
            start_x = -(cols - 1) * pitch / 2
            start_y = -(rows - 1) * pitch / 2
            
            pin = 1
            for row in range(rows):
                for col in range(cols):
                    x = start_x + col * pitch
                    y = start_y + row * pitch
                    positions.append({'pin': pin, 'x': round(x, 3), 'y': round(y, 3)})
                    pin += 1
        
        # ========== DIP/SIP (Through-hole) ==========
        elif any(pkg in self.package_name for pkg in ['DIP', 'SIP']):
            pin_count = self.pin_count.value()
            pitch = self.pin_pitch.value()
            
            if 'DIP' in self.package_name:
                # Dual-inline: two rows
                pads_per_side = pin_count // 2
                row_spacing = 7.62  # Standard 300 mil spacing
                
                for i in range(pads_per_side):
                    x = -row_spacing/2
                    y = -(pads_per_side-1)*pitch/2 + i * pitch
                    positions.append({'pin': i+1, 'x': round(x, 3), 'y': round(y, 3)})
                
                for i in range(pads_per_side):
                    x = row_spacing/2
                    y = (pads_per_side-1)*pitch/2 - i * pitch
                    positions.append({'pin': pads_per_side+i+1, 'x': round(x, 3), 'y': round(y, 3)})
            else:
                # SIP: single row
                for i in range(pin_count):
                    x = 0
                    y = -(pin_count-1)*pitch/2 + i * pitch
                    positions.append({'pin': i+1, 'x': round(x, 3), 'y': round(y, 3)})
        
        # ========== CAN/PCY (Circular) ==========
        elif any(pkg in self.package_name for pkg in ['CAN', 'PCY']):
            pin_count = self.pin_count.value()
            circle_diameter = self.pin_circle_diameter.value()
            radius = circle_diameter / 2
            
            import math
            angle_step = 360 / pin_count
            
            for i in range(pin_count):
                angle = math.radians(i * angle_step)
                x = radius * math.cos(angle)
                y = radius * math.sin(angle)
                positions.append({'pin': i+1, 'x': round(x, 3), 'y': round(y, 3)})
        
        # ========== MELF/SODFL (2-terminal) ==========
        elif any(pkg in self.package_name for pkg in ['MELF', 'SODFL']):
            spacing = self.pad_spacing.value()
            
            positions.append({'pin': 1, 'x': -spacing/2, 'y': 0})
            positions.append({'pin': 2, 'x': spacing/2, 'y': 0})
        
        # ========== Chip Components (2-terminal) ==========
        elif any(pkg in self.package_name for pkg in ['Chip', 'CAPAE', 'Molded', 'Precision Wire']):
            body_length = self.body_length.value()
            
            try:
                pad_length = float(self.terminal_length.value()) if hasattr(self, 'terminal_length') else 0.5
            except:
                pad_length = 0.5
            
            spacing = body_length + pad_length
            
            positions.append({'pin': 1, 'x': -spacing/2, 'y': 0})
            positions.append({'pin': 2, 'x': spacing/2, 'y': 0})
        
        # ========== FM (Flange Mount) ==========
        elif 'FM' in self.package_name:
            # This typically needs custom positioning based on specific device
            # Placeholder: 4 mounting holes at corners
            mounting_holes = self.mounting_holes.value()
            hole_spacing = 10.0  # Default spacing
            
            if mounting_holes == 2:
                positions.append({'pin': 1, 'x': -hole_spacing/2, 'y': 0})
                positions.append({'pin': 2, 'x': hole_spacing/2, 'y': 0})
            elif mounting_holes == 4:
                positions.append({'pin': 1, 'x': -hole_spacing/2, 'y': -hole_spacing/2})
                positions.append({'pin': 2, 'x': hole_spacing/2, 'y': -hole_spacing/2})
                positions.append({'pin': 3, 'x': hole_spacing/2, 'y': hole_spacing/2})
                positions.append({'pin': 4, 'x': -hole_spacing/2, 'y': hole_spacing/2})
        
        return positions
    
    def generate_and_populate(self):
        """Generate footprint and populate PadInputTab"""
        
        # STEP 1: Collect geometry data FIRST (before any widget changes)
        pad_type = self.type_combo.currentText()
        geometry_data = {}
        
        if pad_type == 'square':
            if hasattr(self, 'size_input'):
                geometry_data['pad_length'] = self.size_input.text()
                geometry_data['pad_diameter'] = self.size_input.text()
        
        elif pad_type in ['rectangle', 'rounded_rectangle', 'SMD-oblong']:
            if hasattr(self, 'length_input'):
                geometry_data['pad_length'] = self.length_input.text()
            if hasattr(self, 'width_input'):
                geometry_data['pad_width'] = self.width_input.text()
            if hasattr(self, 'rotation_input'):
                geometry_data['rotation'] = self.rotation_input.text()  # NEW

        
        elif pad_type == 'round':
            if hasattr(self, 'diameter_input'):
                geometry_data['pad_diameter'] = self.diameter_input.text()
        
        elif pad_type in ['PTH', 'NPTH']:
            if hasattr(self, 'hole_diameter_input'):
                geometry_data['hole_diameter'] = self.hole_diameter_input.text()
            if pad_type == 'PTH' and hasattr(self, 'pad_diameter_input'):
                geometry_data['pad_diameter'] = self.pad_diameter_input.text()
        
        # STEP 2: Calculate pad positions
        pad_positions = self.calculate_pad_positions()
        
        # STEP 3: Collect all other data
        data = {
            'package_type': self.package_name,
            'footprint_name': self.footprint_name.text(),
            'part_number': self.part_number.text(),
            'body_length': self.body_length.value(),
            'body_width': self.body_width.value(),
            'body_height': self.body_height.value(),
            'pad_type': pad_type,
            'mask_expansion': self.mask_expansion.text(),
            'paste_expansion': self.paste_expansion.text(),
            'pad_positions': pad_positions
        }
        
        # STEP 4: Add the pre-collected geometry data
        data.update(geometry_data)
        
        print(f"\n=== GENERATE AND POPULATE ===")
        print(f"Package: {self.package_name}")
        print(f"Pads: {len(pad_positions)}")
        print(f"Geometry data: {geometry_data}")
        
        # Use stored designer reference
        if hasattr(self, 'designer'):
            print(f"Using stored designer: {self.designer}")
            self.populate_pad_input_tab(self.designer, data)
            
            # Switch to Pad Input tab
            main_window = self.window()
            if hasattr(main_window, 'tabs'):
                main_window.tabs.setCurrentIndex(0)
            
            QMessageBox.information(
                self,
                "Success",
                f"Generated {len(pad_positions)} pads\n"
                f"Footprint: {data['footprint_name']}"
            )
        else:
            print("ERROR: No designer reference found!")
            QMessageBox.warning(
                self,
                "Error",
                "Could not find designer reference.\n"
                "Please ensure the widget is properly initialized."
            )
        
        # Emit signal
        self.apply_to_footprint.emit(data)


    def populate_pad_input_tab(self, designer, data):
        """Populate PadInputTab with generated data - CORRECTED attribute names"""
        print(f"\n=== POPULATE PAD INPUT TAB ===")
        print(f"Designer: {designer}")
        print(f"Designer type: {type(designer)}")
        
        # The text fields are attributes OF designer, created by PadInputTab
        # Set basic info
        if hasattr(designer, 'part_number'):
            designer.part_number.setText(data.get('part_number', ''))
            print(f"✓ Set part number: {data.get('part_number')}")
        
        if hasattr(designer, 'footprint_name'):
            designer.footprint_name.setText(data.get('footprint_name', ''))
            print(f"✓ Set footprint name: {data.get('footprint_name')}")
        
        if hasattr(designer, 'body_length'):
            designer.body_length.setText(str(data.get('body_length', 0)))
            print(f"✓ Set body length: {data.get('body_length')}")
        
        if hasattr(designer, 'body_width'):
            designer.body_width.setText(str(data.get('body_width', 0)))
            print(f"✓ Set body width: {data.get('body_width')}")
        
        if hasattr(designer, 'body_height'):
            designer.body_height.setText(str(data.get('body_height', 0)))
            print(f"✓ Set body height: {data.get('body_height')}")
        
        # Clear existing padstack rows
        if hasattr(designer, 'padstack_rows'):
            print(f"Clearing {len(designer.padstack_rows)} existing rows")
            for row in designer.padstack_rows[:]:
                row.setParent(None)
                row.deleteLater()
            designer.padstack_rows.clear()
        
        # Add padstack rows
        pad_positions = data.get('pad_positions', [])
        pad_type = data.get('pad_type', 'round')
        print(f"Adding {len(pad_positions)} padstack rows with type '{pad_type}'")
        
        if not hasattr(designer, 'add_padstack_row'):
            print("ERROR: add_padstack_row method not found!")
            return
        
        
        for idx, pos in enumerate(pad_positions):
            if idx < 3:
                print(f"\n--- Pad {idx+1}: Pin {pos['pin']} at ({pos['x']}, {pos['y']}) ---")
            
            designer.add_padstack_row()
            
            if not hasattr(designer, 'padstack_rows') or not designer.padstack_rows:
                print("ERROR: padstack_rows empty after add!")
                continue
            
            row = designer.padstack_rows[-1]
            
            # Set pad type FIRST
            if hasattr(row, 'type_combo'):
                row.type_combo.setCurrentText(pad_type)
            
            # Process events to create geometry widgets
            QApplication.processEvents()
            
            # Set pin and position
            if hasattr(row, 'pin_number'):
                row.pin_number.setText(str(pos['pin']))
            
            if hasattr(row, 'x_offset'):
                row.x_offset.setText(str(pos['x']))
            
            if hasattr(row, 'y_offset'):
                row.y_offset.setText(str(pos['y']))
            
            # Set geometry based on pad type
            if pad_type == 'round':
                diameter = data.get('pad_diameter', '1.0')
                # Try to find the diameter input widget
                if hasattr(row, 'diameter_input'):
                    row.diameter_input.setText(str(diameter))
                    if idx < 3:
                        print(f"  ✓ Set diameter_input: {diameter}")
                elif hasattr(row, 'sizeinput'):
                    row.sizeinput.setText(str(diameter))
                    if idx < 3:
                        print(f"  ✓ Set sizeinput: {diameter}")
            
            elif pad_type in ['rectangle', 'rounded_rectangle', 'SMD-oblong']:
                if hasattr(row, 'length_input') and data.get('pad_length'):
                    row.length_input.setText(str(data.get('pad_length')))
                if hasattr(row, 'width_input') and data.get('pad_width'):
                    row.width_input.setText(str(data.get('pad_width')))
                # NEW: Set rotation with priority
                rotation = pos.get('rotation', data.get('rotation', '0'))
                if hasattr(row, 'rotation_input'):
                    row.rotation_input.setText(str(rotation))

            
            # Set mask/paste
            if hasattr(row, 'mask_expansion'):
                row.mask_expansion.setText(data.get('mask_expansion', '0'))
            if hasattr(row, 'paste_expansion'):
                row.paste_expansion.setText(data.get('paste_expansion', '0'))
        
        print(f"\n=== POPULATE COMPLETE - Added {len(pad_positions)} rows ===\n")

# IPC Class A, B, C inherit from LandPatternClass
class IPCClassA(LandPatternClass):
    def __init__(self, package_name, parent=None):
        self.calculator = IPCCalculationEngine('A')
        super().__init__(package_name, parent)

class IPCClassB(LandPatternClass):
    def __init__(self, package_name, parent=None):
        self.calculator = IPCCalculationEngine('B')
        super().__init__(package_name, parent)

class IPCClassC(LandPatternClass):
    def __init__(self, package_name, parent=None):
        self.calculator = IPCCalculationEngine('C')
        super().__init__(package_name, parent)

class AILibrarianTab(QWidget):
    """AI Librarian tab - under development"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Icon
        icon_label = QLabel("🤖")
        icon_label.setStyleSheet("font-size: 64px;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)
        
        # Title
        title = QLabel("AI Librarian")
        title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #00FFFF;
                margin: 20px;
            }
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Message
        message = QLabel("This option is under development")
        message.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #aaaaaa;
                margin: 10px;
            }
        """)
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(message)
        
        # Description
        description = QLabel(
            "The AI Librarian will automatically extract component\n"
            "specifications from datasheets and generate optimized\n"
            "PCB footprints using advanced machine learning."
        )
        description.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #888888;
                margin: 20px;
                padding: 20px;
                border: 1px dashed #555;
                border-radius: 5px;
            }
        """)
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setWordWrap(True)
        layout.addWidget(description)
        
        layout.addStretch()

class PolygonLineRow(QWidget):
    data_changed = pyqtSignal()
    delete_requested = pyqtSignal(object)

    def __init__(self, line_number=1):
        super().__init__()
        self.line_number = line_number
        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(5)

        # Line number label
        self.line_label = QLabel(f"Line {self.line_number}:")
        self.line_label.setMinimumWidth(60)
        layout.addWidget(self.line_label)

        # Line size
        layout.addWidget(QLabel("Size:"))
        self.line_size = QLineEdit()
        self.line_size.setText("1.0")
        self.line_size.setMaximumWidth(80)
        layout.addWidget(self.line_size)

        # Direction
        layout.addWidget(QLabel("Direction:"))
        self.direction = QComboBox()
        self.direction.addItems(['right', 'down', 'left', 'up'])
        self.direction.setMaximumWidth(80)
        layout.addWidget(self.direction)

        # Corner type
        layout.addWidget(QLabel("Corner:"))
        self.corner_type = QComboBox()
        self.corner_type.addItems(['90-degree', 'chamfer', 'fillet'])
        self.corner_type.setMaximumWidth(100)
        layout.addWidget(self.corner_type)

        # Corner size
        layout.addWidget(QLabel("Corner Size:"))
        self.corner_size = QLineEdit()
        self.corner_size.setText("0")
        self.corner_size.setMaximumWidth(80)
        layout.addWidget(self.corner_size)

        # Delete button
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setMaximumWidth(60)
        layout.addWidget(self.delete_btn)

        layout.addStretch()

    def connect_signals(self):
        self.line_size.textChanged.connect(self.data_changed.emit)
        self.direction.currentTextChanged.connect(self.data_changed.emit)
        self.corner_type.currentTextChanged.connect(self.data_changed.emit)
        self.corner_size.textChanged.connect(self.data_changed.emit)
        self.delete_btn.clicked.connect(lambda: self.delete_requested.emit(self))

    def get_data(self):
        return {
            'line_size': to_decimal(self.line_size.text()) if self.line_size.text() else 1.0,
            'direction': self.direction.currentText(),
            'corner_type': self.corner_type.currentText(),
            'corner_size': to_decimal(self.corner_size.text()) if self.corner_size.text() else 0.0
        }

    def set_data(self, data):
        self.line_size.setText(str(data.get('line_size', 1.0)))
        self.direction.setCurrentText(data.get('direction', 'right'))
        self.corner_type.setCurrentText(data.get('corner_type', '90-degree'))
        self.corner_size.setText(str(data.get('corner_size', 0)))

class CustomPolygonWidget(QWidget):
    data_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.polygon_lines = []
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Header
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Custom Polygon Definition:"))
        
        add_line_btn = QPushButton("+ Add Line")
        add_line_btn.clicked.connect(self.add_polygon_line)
        add_line_btn.setMaximumWidth(100)
        header_layout.addWidget(add_line_btn)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)

        # Lines container
        self.lines_widget = QWidget()
        self.lines_layout = QVBoxLayout(self.lines_widget)
        self.lines_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.lines_widget)

        # Add initial line
        self.add_polygon_line()

    def add_polygon_line(self):
        line_row = PolygonLineRow(len(self.polygon_lines) + 1)
        line_row.data_changed.connect(self.data_changed.emit)
        line_row.delete_requested.connect(self.delete_polygon_line)
        
        self.polygon_lines.append(line_row)
        self.lines_layout.addWidget(line_row)

    def delete_polygon_line(self, line_row):
        if len(self.polygon_lines) > 1: # Keep at least one line
            self.polygon_lines.remove(line_row)
            line_row.setParent(None)
            self.update_line_numbers()

    def update_line_numbers(self):
        """Update line numbers after add/delete operations"""
        for i, line_row in enumerate(self.polygon_lines):
            line_row.line_number = i + 1
            # Update the label text
            line_row.layout().itemAt(0).widget().setText(f"Line {i + 1}:")

    def get_data(self):
        """Get polygon data"""
        return {
            'lines': [line.get_data() for line in self.polygon_lines]
        }

    def set_data(self, data):
        """Set polygon data"""
        # Clear existing lines
        for line in self.polygon_lines[:]:
            self.delete_polygon_line(line)
        
        # Add lines from data
        lines_data = data.get('lines', [{'line_size': 1.0, 'direction': 'right', 'corner_type': '90-degree', 'corner_size': 0}])
        for line_data in lines_data:
            self.add_polygon_line()
            self.polygon_lines[-1].set_data(line_data)

class FootprintRenderer(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(400, 400)
        self.footprint_data = {}
        self.auto_fit = True

        self.zoom_factor = Decimal('1.0')
        self.offset_x = Decimal('0.0')
        self.offset_y = Decimal('0.0')
        self.origin_offset_x = Decimal('0.0')
        self.origin_offset_y = Decimal('0.0')
        self.show_noprob_top = False
        self.show_noprob_bottom = False
        
        self.setStyleSheet("background-color: #2b2b2b; border: 1px solid #555;")
        self.selected_pads = set()
        self.setup_dimension_controls()


    def setup_dimension_controls(self):
        """Create overlay dimension control widgets"""
        # Air Gap Dimensions toggle
        self.show_airgap_checkbox = QCheckBox("Air Gap Dimensions ", self)
        self.show_airgap_checkbox.setChecked(True)
        self.show_airgap_checkbox.move(10, 10)
        self.show_airgap_checkbox.setStyleSheet("""
        QCheckBox {
            color: #00FFFF;
            background-color: rgba(0,0,0,180);
            padding: 4px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 11px;
        }
        QCheckBox::indicator {
            width: 14px;
            height: 14px;
        }
        QCheckBox::indicator:checked {
            background-color: #00FFFF;
        }
        """)

        # Pitch Dimensions toggle
        self.show_pitch_checkbox = QCheckBox(" Pitch Dimensions", self)
        self.show_pitch_checkbox.setChecked(False)
        self.show_pitch_checkbox.move(10, 40)
        self.show_pitch_checkbox.setStyleSheet("""
        QCheckBox {
            color: #FFA500;
            background-color: rgba(0,0,0,180);
            padding: 4px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 11px;
        }
        QCheckBox::indicator {
            width: 14px;
            height: 14px;
        }
        QCheckBox::indicator:checked {
            background-color: #FFA500;
        }
        """)


        # Clear All Dimensions button
        self.clear_dims_btn = QPushButton("Clear All Dimensions", self)
        self.clear_dims_btn.move(10, 70)  # Move down to make room for DFA toggle
        self.clear_dims_btn.setMaximumWidth(160)
        self.clear_dims_btn.setStyleSheet("""
        QPushButton {
            background-color: rgba(68,68,68,200);
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 11px;
            border: 1px solid #666;
        }
        QPushButton:hover {
            background-color: rgba(88,88,88,220);
        }
        QPushButton:pressed {
            background-color: rgba(48,48,48,200);
        }
        """)

        # Show DFA Bond toggle - NEW
        self.show_dfa_bond_checkbox = QCheckBox("DFA Bond", self)
        self.show_dfa_bond_checkbox.setChecked(False)  # Hidden by default
        self.show_dfa_bond_checkbox.move(10, 100)
        self.show_dfa_bond_checkbox.setStyleSheet("""
        QCheckBox {
            color: #FF8C00;
            background-color: rgba(0,0,0,180);
            padding: 4px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 11px;
        }
        QCheckBox::indicator {
            width: 14px;
            height: 14px;
        }
        QCheckBox::indicator:checked {
            background-color: #FF8C00;
        }
        """)

        # NEW: Via Keepout toggle
        self.show_via_keepout_checkbox = QCheckBox("Via Kpout All", self)
        self.show_via_keepout_checkbox.setChecked(False) # Hidden by default
        self.show_via_keepout_checkbox.move(10, 130)
        self.show_via_keepout_checkbox.setStyleSheet("""
            QCheckBox {
                color: #FF4500;
                background-color: rgba(0,0,0,180);
                padding: 4px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
            }
            QCheckBox::indicator:checked {
                background-color: #FF4500;
            }
        """)
        
        # NEW: Package Keepout toggle
        self.show_package_keepout_checkbox = QCheckBox("Pkg Kpout Btm", self)
        self.show_package_keepout_checkbox.setChecked(False) # Hidden by default
        self.show_package_keepout_checkbox.move(10, 160)
        self.show_package_keepout_checkbox.setStyleSheet("""
            QCheckBox {
                color: #8B4513;
                background-color: rgba(0,0,0,180);
                padding: 4px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
            }
            QCheckBox::indicator:checked {
                background-color: #8B4513;
            }
        """)
        
        # NEW: Route Keepout toggle
        self.show_route_keepout_checkbox = QCheckBox("Route Kpout All", self)
        self.show_route_keepout_checkbox.setChecked(False) # Hidden by default
        self.show_route_keepout_checkbox.move(10, 190)
        self.show_route_keepout_checkbox.setStyleSheet("""
            QCheckBox {
                color: #DC143C;
                background-color: rgba(0,0,0,180);
                padding: 4px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
            }
            QCheckBox::indicator:checked {
                background-color: #DC143C;
            }
        """)
        


        # Connect signals
        self.show_airgap_checkbox.stateChanged.connect(self.on_dimension_toggle)
        self.show_pitch_checkbox.stateChanged.connect(self.on_dimension_toggle)
        self.show_dfa_bond_checkbox.stateChanged.connect(self.on_dimension_toggle)  # NEW
        self.clear_dims_btn.clicked.connect(self.on_clear_dimensions)
        # Connect new signals
        self.show_via_keepout_checkbox.stateChanged.connect(self.on_dimension_toggle)
        self.show_package_keepout_checkbox.stateChanged.connect(self.on_dimension_toggle)
        self.show_route_keepout_checkbox.stateChanged.connect(self.on_dimension_toggle)





    def mousePressEvent(self, event):
        """Handle mouse clicks for pad selection"""
        pos = event.position()
        
        # Convert all coordinates to Decimal before arithmetic
        center_x = to_decimal(str(self.width() / 2))
        center_y = to_decimal(str(self.height() / 2))
        
        # Convert PyQt position coordinates to Decimal
        pos_x = to_decimal(str(pos.x()))
        pos_y = to_decimal(str(pos.y()))
        
        # Account for zoom and offset - ALL DECIMAL ARITHMETIC
        world_x = (pos_x - center_x - self.offset_x) / self.zoom_factor
        world_y = -(pos_y - center_y - self.offset_y) / self.zoom_factor  # Y-axis flipped

        # Check if click is on any pad
        pad_bounds_list = self.get_individual_pad_bounds_absolute()
        clicked_pad = None
        
        # Convert world coordinates to float for comparison with pad bounds
        world_x_float = float(world_x)
        world_y_float = float(world_y)
        
        for i, bounds in enumerate(pad_bounds_list):
            if bounds:
                min_x, min_y, max_x, max_y = bounds
                if min_x <= world_x_float <= max_x and min_y <= world_y_float <= max_y:
                    clicked_pad = i
                    break

        if clicked_pad is not None:
            # Toggle pad selection
            if clicked_pad in self.selected_pads:
                self.selected_pads.remove(clicked_pad)
            else:
                # Limit to 2 pads maximum
                if len(self.selected_pads) >= 2:
                    # Remove oldest selection (FIFO)
                    oldest_pad = next(iter(self.selected_pads))
                    self.selected_pads.remove(oldest_pad)
                self.selected_pads.add(clicked_pad)
        else:
            # Click outside pads - clear selection
            self.selected_pads.clear()

        self.update()  # Repaint to show selection changes
    # Repaint to show selection changes


    def resizeEvent(self, event):
        """Handle resize events to position settings button"""
        super().resizeEvent(event)
        # Position settings button in top right corner
        if hasattr(self, 'settings_btn'):
            self.settings_btn.move(self.width() - 90, 10)


    def on_dimension_toggle(self):
        """Handle dimension toggle changes"""
        self.update()  # Trigger repaint

    def on_clear_dimensions(self):
        """Clear all dimension displays and selections"""
        self.show_airgap_checkbox.setChecked(False)
        self.show_pitch_checkbox.setChecked(False)
        self.selected_pads.clear()  # Clear pad selections
        self.update()

    def update_footprint(self, data):
        self.footprint_data = data
        # Clear cached absolute positions when data changes
        self._absolute_positions = None
        if self.auto_fit:
            self.fit_to_view()
        self.update()

    def on_fit_to_view(self):
        """Handle fit to view button click"""
        self.auto_fit = True
        self.fit_to_view()
        self.update()        

    def fit_to_view(self):
        if not self.footprint_data.get('padstacks') and not all(k in self.footprint_data for k in ['body_length', 'body_width']):
            return

        # Reset offsets for auto-fit
        self.offset_x = Decimal('0.0')
        self.offset_y = Decimal('0.0')

        # Calculate body bounds
        body_bounds = None
        if all(k in self.footprint_data for k in ['body_length', 'body_width']):
            length = to_decimal(self.footprint_data['body_length'])
            width = to_decimal(self.footprint_data['body_width'])
            half_length = length / Decimal('2')
            half_width = width / Decimal('2')
            body_bounds = [-half_length, -half_width, half_length, half_width]

        # Calculate pad bounds
        pad_bounds = self.calculate_all_pads_bounds()

        # Determine outermost bounds
        if body_bounds and pad_bounds:
            min_x = min(body_bounds[0], pad_bounds[0])
            min_y = min(body_bounds[1], pad_bounds[1])
            max_x = max(body_bounds[2], pad_bounds[2])
            max_y = max(body_bounds[3], pad_bounds[3])
        elif body_bounds:
            min_x, min_y, max_x, max_y = body_bounds
        elif pad_bounds:
            min_x, min_y, max_x, max_y = pad_bounds
        else:
            return

        # Add courtyard expansion
        courtyard = to_decimal(self.footprint_data.get('noprob_expansion', '0.51'))
        min_x -= courtyard
        max_x += courtyard
        min_y -= courtyard
        max_y += courtyard

        # Calculate zoom to fit
        if max_x > min_x and max_y > min_y:
            margin = Decimal('20')
            width_available = Decimal(str(self.width())) - Decimal('2') * margin
            height_available = Decimal(str(self.height())) - Decimal('2') * margin
            
            zoom_x = width_available / (max_x - min_x)
            zoom_y = height_available / (max_y - min_y)
            self.zoom_factor = min(zoom_x, zoom_y, Decimal('110'))  # Max zoom limit

        self.update()

    def calculate_pad_bounds(self, pad):
        """Calculate bounding box for a pad"""
        try:
            x = to_decimal(pad.get('x_offset', 0))
            y = to_decimal(pad.get('y_offset', 0))
        except (ValueError, TypeError):
            x, y = Decimal('0'), Decimal('0')  # Changed from 0, 0

        pad_type = pad['type']

        if pad_type == 'square':
            try:
                size = to_decimal(pad.get('size', 1))
                return [x - size/2, y - size/2, x + size/2, y + size/2]
            except (ValueError, TypeError):
                return [x - Decimal('0.5'), y - Decimal('0.5'), x + Decimal('0.5'), y + Decimal('0.5')]  # Fixed

        elif pad_type == 'rectangle':
            try:
                length = to_decimal(pad.get('length', 1))
                width = to_decimal(pad.get('width', 1))
                # D-shape can also be rotated, so handle rotation here too
                rotation = pad.get('rotation', 0)
                try:
                    rotation_rad = math.radians(float(to_decimal(str(rotation))))
                except (ValueError, TypeError):
                    rotation_rad = 0

                if rotation_rad != 0:
                    return self._calculate_rotated_bounds(x, y, length, width, rotation_rad)
                else:
                    return [x - length/2, y - width/2, x + length/2, y + width/2]
            except (ValueError, TypeError):
                return [x - Decimal('0.5'), y - Decimal('0.5'), x + Decimal('0.5'), y + Decimal('0.5')]  # Fixed


        elif pad_type == 'rounded_rectangle':
            try:
                length = to_decimal(pad.get('length', 1))
                width = to_decimal(pad.get('width', 1))
                # D-shape can also be rotated, so handle rotation here too
                rotation = pad.get('rotation', 0)
                try:
                    rotation_rad = math.radians(float(to_decimal(str(rotation))))
                except (ValueError, TypeError):
                    rotation_rad = 0

                if rotation_rad != 0:
                    return self._calculate_rotated_bounds(x, y, length, width, rotation_rad)
                else:
                    return [x - length/2, y - width/2, x + length/2, y + width/2]
            except (ValueError, TypeError):
                return [x - Decimal('0.5'), y - Decimal('0.5'), x + Decimal('0.5'), y + Decimal('0.5')]  # Fixed                

        elif pad_type == 'rounded_rectangle':
            try:
                length = to_decimal(pad.get('length', 1))
                width = to_decimal(pad.get('width', 1))
                rotation = pad.get('rotation', 0)
                try:
                    rotation_rad = math.radians(float(to_decimal(str(rotation))))
                except (ValueError, TypeError):
                    rotation_rad = 0

                if rotation_rad != 0:
                    return self._calculate_rotated_bounds(x, y, length, width, rotation_rad)
                else:
                    return [x - length/2, y - width/2, x + length/2, y + width/2]
            except (ValueError, TypeError):
                return [x - Decimal('0.5'), y - Decimal('0.5'), x + Decimal('0.5'), y + Decimal('0.5')]  # Fixed

        elif pad_type in ['round']:
            try:
                diameter = to_decimal(pad.get('diameter', 1))
                return [x - diameter/2, y - diameter/2, x + diameter/2, y + diameter/2]
            except (ValueError, TypeError):
                return [x - Decimal('0.5'), y - Decimal('0.5'), x + Decimal('0.5'), y + Decimal('0.5')]  # Fixed

        elif pad_type == 'D-shape':
            try:
                length = to_decimal(pad.get('length', 1))
                width = to_decimal(pad.get('width', 1))
                # D-shape can also be rotated, so handle rotation here too
                rotation = pad.get('rotation', 0)
                try:
                    rotation_rad = math.radians(float(to_decimal(str(rotation))))
                except (ValueError, TypeError):
                    rotation_rad = 0

                if rotation_rad != 0:
                    return self._calculate_rotated_bounds(x, y, length, width, rotation_rad)
                else:
                    return [x - length/2, y - width/2, x + length/2, y + width/2]
            except (ValueError, TypeError):
                return [x - Decimal('0.5'), y - Decimal('0.5'), x + Decimal('0.5'), y + Decimal('0.5')]  # Fixed

        elif pad_type == 'PTH_rectangle':
            try:
                pad_length = to_decimal(pad.get('pad_length', 2.0))
                pad_width = to_decimal(pad.get('pad_width', 1.2))
                # Handle rotation
                rotation = pad.get('rotation', 0)
                try:
                    rotation_rad = math.radians(float(to_decimal(str(rotation))))
                except (ValueError, TypeError):
                    rotation_rad = 0

                if rotation_rad != 0:
                    return self._calculate_rotated_bounds(x, y, pad_length, pad_width, rotation_rad)
                else:
                    return [x - pad_length/2, y - pad_width/2, x + pad_length/2, y + pad_width/2]
            except (ValueError, TypeError):
                return [x - Decimal('1.0'), y - Decimal('0.6'), x + Decimal('1.0'), y + Decimal('0.6')]  # Fixed

        elif pad_type == 'NPTH_rectangle':
            try:
                hole_length = to_decimal(pad.get('hole_length', 1.5))
                hole_width = to_decimal(pad.get('hole_width', 0.8))
                # Handle rotation
                rotation = pad.get('rotation', 0)
                try:
                    rotation_rad = math.radians(float(to_decimal(str(rotation))))
                except (ValueError, TypeError):
                    rotation_rad = 0

                if rotation_rad != 0:
                    return self._calculate_rotated_bounds(x, y, hole_length, hole_width, rotation_rad)
                else:
                    return [x - hole_length/2, y - hole_width/2, x + hole_length/2, y + hole_width/2]
            except (ValueError, TypeError):
                return [x - Decimal('0.75'), y - Decimal('0.4'), x + Decimal('0.75'), y + Decimal('0.4')]  # Fixed

        elif pad_type in ['PTH', 'NPTH']:
            try:
                if pad_type == 'PTH':
                    diameter = to_decimal(pad.get('pad_diameter', 1.2))
                else:
                    diameter = to_decimal(pad.get('hole_diameter', 0.8))
                return [x - diameter/2, y - diameter/2, x + diameter/2, y + diameter/2]
            except (ValueError, TypeError):
                return [x - Decimal('0.5'), y - Decimal('0.5'), x + Decimal('0.5'), y + Decimal('0.5')]  # Fixed

        elif pad_type in ['PTH_oblong', 'NPTH_oblong']:
            try:
                if pad_type == 'PTH_oblong':
                    length = to_decimal(pad.get('pad_length', 2.0))
                    width = to_decimal(pad.get('pad_width', 1.2))
                else:
                    length = to_decimal(pad.get('hole_length', 1.5))
                    width = to_decimal(pad.get('hole_width', 0.8))

                # Handle rotation
                rotation = pad.get('rotation', 0)
                try:
                    rotation_rad = math.radians(float(to_decimal(str(rotation))))
                except (ValueError, TypeError):
                    rotation_rad = 0

                if rotation_rad != 0:
                    return self._calculate_rotated_bounds(x, y, length, width, rotation_rad)
                else:
                    return [x - length/2, y - width/2, x + length/2, y + width/2]
            except (ValueError, TypeError):
                return [x - Decimal('0.5'), y - Decimal('0.5'), x + Decimal('0.5'), y + Decimal('0.5')]  # Fixed
            
        elif pad_type == 'PTH_square':
                hole_diameter = to_decimal(pad.get('hole_diameter', 0.8))
                pad_size = to_decimal(pad.get('pad_size', 1.5))
                # Returns bounds based on square pad size
                return [x - pad_size/2, y - pad_size/2, x + pad_size/2, y + pad_size/2]

        elif pad_type == 'PTH_oblong_rect':
            # Handle oblong hole with rectangular pad
            pad_length = to_decimal(pad.get('pad_length', 2.5))
            pad_width = to_decimal(pad.get('pad_width', 1.5))
            # Includes rotation handling
            return [x - pad_length/2, y - pad_width/2, x + pad_length/2, y + pad_width/2]


        elif pad_type == 'custom':
            # Calculate bounds for custom polygon
            polygon_points = self.calculate_polygon_points(pad)
            if polygon_points:
                xs = [p.x() for p in polygon_points]
                ys = [p.y() for p in polygon_points]
                return [min(xs), min(ys), max(xs), max(ys)]
            
            return [x - Decimal('0.5'), y - Decimal('0.5'), x + Decimal('0.5'), y + Decimal('0.5')]  # Fixed

    def _calculate_rotated_bounds(self, center_x, center_y, length, width, rotation_rad):
        """Helper method to calculate bounds for a rotated rectangle"""
        try:
            # Calculate half dimensions
            half_length = length / 2
            half_width = width / 2
            
            # Define the four corners of the rectangle relative to center
            corners = [
                (-half_length, -half_width),  # bottom-left
                (half_length, -half_width),   # bottom-right
                (half_length, half_width),    # top-right
                (-half_length, half_width)    # top-left
            ]
            
            # Rotate each corner
            cos_r = math.cos(rotation_rad)
            sin_r = math.sin(rotation_rad)
            
            rotated_corners = []
            for cx, cy in corners:
                # Apply rotation matrix
                rx = float(cx) * cos_r - float(cy) * sin_r
                ry = float(cx) * sin_r + float(cy) * cos_r
                rotated_corners.append((rx, ry))
            
            # Find bounding box of rotated corners
            xs = [corner[0] for corner in rotated_corners]
            ys = [corner[1] for corner in rotated_corners]
            
            min_x = center_x + to_decimal(str(min(xs)))
            max_x = center_x + to_decimal(str(max(xs)))
            min_y = center_y + to_decimal(str(min(ys)))
            max_y = center_y + to_decimal(str(max(ys)))
            
            return [min_x, min_y, max_x, max_y]
            
        except Exception as e:
            print(f"Error calculating rotated bounds: {e}")
            # Fallback to original rectangle bounds - FIXED
            half_length = length / Decimal('2')
            half_width = width / Decimal('2')
            return [center_x - half_length, center_y - half_width, center_x + half_length, center_y + half_width]


    def calculate_polygon_points(self, pad):
        """Calculate polygon points from line definitions with proper corner handling"""
        lines_data = pad.get('polygon_data', {}).get('lines', [])
        if not lines_data:
            return []

        raw_points = []
        try:
            current_x = to_decimal(pad.get('x_offset', 0))
            current_y = to_decimal(pad.get('y_offset', 0))
        except (ValueError, TypeError):
            current_x, current_y = 0, 0
            
        raw_points.append((current_x, current_y))

        for line_data in lines_data:
            try:
                line_size = to_decimal(line_data.get('line_size', 1.0))
            except (ValueError, TypeError):
                line_size = 1.0
                
            direction = line_data.get('direction', 'right')

            if direction == 'right':
                current_x += line_size
            elif direction == 'down':
                current_y -= line_size
            elif direction == 'left':
                current_x -= line_size
            elif direction == 'up':
                current_y += line_size

            raw_points.append((current_x, current_y))

        final_points = []
        # Fix these lines:
        final_points.append(QPointF(raw_points[0][0], raw_points[0][1]))  # was missing 


        for i in range(1, len(raw_points) - 1):
            prev_point = raw_points[i-1]
            curr_point = raw_points[i]
            next_point = raw_points[i+1]

            line_data = lines_data[i-1]
            corner_type = line_data.get('corner_type', '90-degree')
            try:
                corner_size = to_decimal(line_data.get('corner_size', 0))
            except (ValueError, TypeError):
                corner_size = 0

            if corner_type == '90-degree' or corner_size == 0:
                final_points.append(QPointF(curr_point[0], curr_point[1]))
            elif corner_type == 'chamfer':
                chamfer_points = self.calculate_chamfer_points(
                    QPointF(prev_point[0], prev_point[1]),  # FIXED
                    QPointF(curr_point[0], curr_point[1]),  # FIXED
                    QPointF(next_point[0], next_point[1]),  # FIXED,
                    corner_size
                )
                final_points.extend(chamfer_points)
            elif corner_type == 'fillet':
                fillet_points = self.calculate_fillet_points(
                    QPointF(prev_point[0], prev_point[1]),   # FIXED
                    QPointF(curr_point[0], curr_point[1]),   # FIXED
                    QPointF(next_point[0], next_point[1]),   #
                    corner_size
                )
                final_points.extend(fillet_points)

        final_points.append(QPointF(raw_points[-1][0], raw_points[-1][1]))
        return final_points

    def calculate_all_pads_bounds(self):
        """Calculate bounding box for all copper pads"""
        if not self.footprint_data.get('padstacks'):
            return None

        min_x = min_y = to_decimal('inf')
        max_x = max_y = to_decimal('-inf')

        for pad in self.footprint_data['padstacks']:
            pad_bounds = self.calculate_pad_bounds(pad)
            if pad_bounds:
                min_x = min(min_x, pad_bounds[0])
                min_y = min(min_y, pad_bounds[1])
                max_x = max(max_x, pad_bounds[2])
                max_y = max(max_y, pad_bounds[3])
        if min_x == to_decimal('inf'):
            return None

        return [min_x, min_y, max_x, max_y]

    def get_individual_pad_bounds(self):
        """Get bounding box for each individual pad using relative positions"""
        if not self.footprint_data.get('padstacks'):
            return []

        pad_bounds_list = []
        for pad in self.footprint_data['padstacks']:
            pad_bounds = self.calculate_pad_bounds(pad)
            if pad_bounds:
                pad_bounds_list.append(pad_bounds)
        return pad_bounds_list



    def get_individual_pad_bounds_absolute(self):
        """Get bounding box for each individual pad using absolute positions"""
        if not self.footprint_data.get('padstacks'):
            return []

        pad_bounds_list = []
        for i, pad in enumerate(self.footprint_data['padstacks']):
            pad_bounds = self.calculate_pad_bounds_absolute(pad, i)
            if pad_bounds:
                pad_bounds_list.append(pad_bounds)
        
        return pad_bounds_list

    def calculate_pad_bounds_absolute(self, pad, pad_index):
        """Calculate bounding box for a pad using absolute position"""
        absolute_positions = getattr(self, '_absolute_positions', None)
        if absolute_positions is None:
            absolute_positions = self.calculate_pad_absolute_positions()
            self._absolute_positions = absolute_positions

        if pad_index in absolute_positions:
            x, y = absolute_positions[pad_index]
        else:
            try:
                x = to_decimal(pad.get('x_offset', 0))
                y = to_decimal(pad.get('y_offset', 0))
            except (ValueError, TypeError):
                x, y = 0, 0

        pad_type = pad['type']

        if pad_type == 'square':
            try:
                size = to_decimal(pad.get('size', 1))
                return [x - size/2, y - size/2, x + size/2, y + size/2]
            except (ValueError, TypeError):
                return [x - 0.5, y - 0.5, x + 0.5, y + 0.5]

        elif pad_type == 'rectangle':
            try:
                length = to_decimal(pad.get('length', 1))
                width = to_decimal(pad.get('width', 1))
                rotation = pad.get('rotation', 0)
                try:
                    rotation_rad = math.radians(float(to_decimal(str(rotation))))
                except (ValueError, TypeError):
                    rotation_rad = 0
                    
                if rotation_rad != 0:
                    return self._calculate_rotated_bounds(x, y, length, width, rotation_rad)
                else:
                    return [x - length/2, y - width/2, x + length/2, y + width/2]
            except (ValueError, TypeError):
                return [x - 0.5, y - 0.5, x + 0.5, y + 0.5]

        elif pad_type == 'rounded_rectangle':
            try:
                length = to_decimal(pad.get('length', 1))
                width = to_decimal(pad.get('width', 1))
                rotation = pad.get('rotation', 0)
                try:
                    rotation_rad = math.radians(float(to_decimal(str(rotation))))
                except (ValueError, TypeError):
                    rotation_rad = 0
                    
                if rotation_rad != 0:
                    return self._calculate_rotated_bounds(x, y, length, width, rotation_rad)
                else:
                    return [x - length/2, y - width/2, x + length/2, y + width/2]
            except (ValueError, TypeError):
                return [x - 0.5, y - 0.5, x + 0.5, y + 0.5]

        elif pad_type == 'SMD-oblong':
            try:
                length = to_decimal(pad.get('length', 1))
                width = to_decimal(pad.get('width', 1))
                rotation = pad.get('rotation', 0)
                try:
                    rotation_rad = math.radians(float(to_decimal(str(rotation))))
                except (ValueError, TypeError):
                    rotation_rad = 0
                    
                if rotation_rad != 0:
                    return self._calculate_rotated_bounds(x, y, length, width, rotation_rad)
                else:
                    return [x - length/2, y - width/2, x + length/2, y + width/2]
            except (ValueError, TypeError):
                return [x - 0.5, y - 0.5, x + 0.5, y + 0.5]



        elif pad_type in ['round']:
            try:
                diameter = to_decimal(pad.get('diameter', 1))
                return [x - diameter/2, y - diameter/2, x + diameter/2, y + diameter/2]
            except (ValueError, TypeError):
                return [x - 0.5, y - 0.5, x + 0.5, y + 0.5]

        elif pad_type == 'D-shape':
            try:
                length = to_decimal(pad.get('length', 1))
                width = to_decimal(pad.get('width', 1))
                # ADD ROTATION HANDLING FOR D-SHAPE
                rotation = pad.get('rotation', 0)
                try:
                    rotation_rad = math.radians(float(to_decimal(str(rotation))))
                except (ValueError, TypeError):
                    rotation_rad = 0
                    
                if rotation_rad != 0:
                    return self._calculate_rotated_bounds(x, y, length, width, rotation_rad)
                else:
                    return [x - length/2, y - width/2, x + length/2, y + width/2]
            except (ValueError, TypeError):
                return [x - 0.5, y - 0.5, x + 0.5, y + 0.5]

        elif pad_type in ['PTH', 'NPTH']:
            try:
                if pad_type == 'PTH':
                    diameter = to_decimal(pad.get('pad_diameter', 1.2))
                else:
                    diameter = to_decimal(pad.get('hole_diameter', 0.8))
                return [x - diameter/2, y - diameter/2, x + diameter/2, y + diameter/2]
            except (ValueError, TypeError):
                return [x - 0.6, y - 0.6, x + 0.6, y + 0.6]

        elif pad_type == 'PTH_rectangle':  # ADD ROTATION HANDLING
            try:
                pad_length = to_decimal(pad.get('pad_length', 2.0))
                pad_width = to_decimal(pad.get('pad_width', 1.2))
                
                # Handle rotation
                rotation = pad.get('rotation', 0)
                try:
                    rotation_rad = math.radians(float(to_decimal(str(rotation))))
                except (ValueError, TypeError):
                    rotation_rad = 0
                    
                if rotation_rad != 0:
                    return self._calculate_rotated_bounds(x, y, pad_length, pad_width, rotation_rad)
                else:
                    return [x - pad_length/2, y - pad_width/2, x + pad_length/2, y + pad_width/2]
            except (ValueError, TypeError):
                return [x - 1.0, y - 0.6, x + 1.0, y + 0.6]

        elif pad_type in ['PTH_oblong', 'NPTH_oblong']:  # ADD ROTATION HANDLING
            try:
                if pad_type == 'PTH_oblong':
                    length = to_decimal(pad.get('pad_length', 2.0))
                    width = to_decimal(pad.get('pad_width', 1.2))
                else:
                    length = to_decimal(pad.get('hole_length', 1.5))
                    width = to_decimal(pad.get('hole_width', 0.8))
                
                # Handle rotation
                rotation = pad.get('rotation', 0)
                try:
                    rotation_rad = math.radians(float(to_decimal(str(rotation))))
                except (ValueError, TypeError):
                    rotation_rad = 0
                    
                if rotation_rad != 0:
                    return self._calculate_rotated_bounds(x, y, length, width, rotation_rad)
                else:
                    return [x - length/2, y - width/2, x + length/2, y + width/2]
            except (ValueError, TypeError):
                return [x - 1.0, y - 0.6, x + 1.0, y + 0.6]
            
        elif pad_type == 'NPTH_rectangle':
            try:
                hole_length = to_decimal(pad.get('hole_length', 1.5))
                hole_width = to_decimal(pad.get('hole_width', 0.8))
                rotation = pad.get('rotation', 0)
                                
                try:
                    rotation_rad = math.radians(float(to_decimal(str(rotation))))
                except (ValueError, TypeError):
                    rotation_rad = 0

                if rotation_rad != 0:
                    bounds = self._calculate_rotated_bounds(x, y, hole_length, hole_width, rotation_rad)
                    return bounds
                else:
                    bounds = [x - hole_length/2, y - hole_width/2, x + hole_length/2, y + hole_width/2]
                    return bounds
            except (ValueError, TypeError):
                half_l = Decimal('0.75')
                half_w = Decimal('0.4')
                return [x - half_l, y - half_w, x + half_l, y + half_w]
        
        elif pad_type == 'custom':
            # Handle custom polygon pads with absolute positioning
            polygon_points = self.calculate_polygon_points_absolute(pad, x, y)
            if polygon_points:
                xs = [p.x() for p in polygon_points]
                ys = [p.y() for p in polygon_points]
                return [min(xs), min(ys), max(xs), max(ys)]

        half = Decimal('0.5')
        return [x - half, y - half, x + half, y + half]

    def calculate_polygon_points_absolute(self, pad, abs_x, abs_y):
        """Calculate polygon points using absolute position"""
        lines_data = pad.get('polygon_data', {}).get('lines', [])
        if not lines_data:
            return []

        raw_points = []
        current_x = abs_x
        current_y = abs_y
        raw_points.append((current_x, current_y))

        for line_data in lines_data:
            try:
                line_size = to_decimal(line_data.get('line_size', 1.0))
            except (ValueError, TypeError):
                line_size = 1.0
                
            direction = line_data.get('direction', 'right')

            if direction == 'right':
                current_x += line_size
            elif direction == 'down':
                current_y -= line_size
            elif direction == 'left':
                current_x -= line_size
            elif direction == 'up':
                current_y += line_size

            raw_points.append((current_x, current_y))

        final_points = []
        final_points.append(QPointF(raw_points[0][0], raw_points[0][1]))

        for i in range(1, len(raw_points) - 1):
            prev_point = raw_points[i-1]
            curr_point = raw_points[i]
            next_point = raw_points[i+1]

            line_data = lines_data[i-1]
            corner_type = line_data.get('corner_type', '90-degree')
            try:
                corner_size = to_decimal(line_data.get('corner_size', 0))
            except (ValueError, TypeError):
                corner_size = 0

            if corner_type == '90-degree' or corner_size == 0:
                final_points.append(QPointF(curr_point[0], curr_point[1]))
            elif corner_type == 'chamfer':
                chamfer_points = self.calculate_chamfer_points(
                    QPointF(prev_point[0], prev_point[1]),
                    QPointF(curr_point[0], curr_point[1]),
                    QPointF(next_point[0], next_point[1]),
                    corner_size
                )
                final_points.extend(chamfer_points)
            elif corner_type == 'fillet':
                fillet_points = self.calculate_fillet_points(
                    QPointF(prev_point[0], prev_point[1]),
                    QPointF(curr_point[0], curr_point[1]),
                    QPointF(next_point[0], next_point[1]),
                    corner_size
                )
                final_points.extend(fillet_points)

        final_points.append(QPointF(raw_points[-1][0], raw_points[-1][1]))
        return final_points

    def calculate_pad_absolute_positions(self):
        """Calculate absolute positions for all pads considering offset_from"""
        if not self.footprint_data.get('padstacks'):
            return {}

        pads = self.footprint_data['padstacks']
        resolver = PadPositionResolver(pads)
        positions = {}

        for i, pad in enumerate(pads):
            try:
                abs_x, abs_y = resolver.get_absolute_position(pad)  # This will now work safely
                positions[i] = (abs_x, abs_y)
            except Exception as e:
                print(f"Error calculating position for pad {i}: {e}")
                # Fallback to direct offset
                try:
                    x = to_decimal(pad.get('x_offset', 0))
                    y = to_decimal(pad.get('y_offset', 0))
                    positions[i] = (x, y)
                except (ValueError, TypeError):
                    positions[i] = (0, 0)

        return positions

    def calculate_chamfer_points(self, p1, p2, p3, chamfer_size):
        """Calculate chamfer points for corner at p2"""
        def point_along_line(p_start, p_end, dist):
            vx = p_end.x() - p_start.x()
            vy = p_end.y() - p_start.y()
            length = math.sqrt(vx*vx + vy*vy)
            if length == 0:
                return p_start
            scale = to_decimal(str(dist)) / to_decimal(str(length))
            return QPointF(
            float(to_decimal(str(p_start.x())) + to_decimal(str(vx)) * scale), 
            float(to_decimal(str(p_start.y())) + to_decimal(str(vy)) * scale)
        )

        cp1 = point_along_line(p2, p1, chamfer_size)
        cp2 = point_along_line(p2, p3, chamfer_size)
        return [cp1, cp2]

    def calculate_fillet_points(self, p1, p2, p3, radius, segments=8):
        """Calculate arc points for fillet at corner p2"""
        def normalize(v):
            length = math.sqrt(v[0]**2 + v[1]**2)
            if length == 0:
                return (0.0, 0.0)
            return (v[0] / length, v[1] / length)

        v1 = (p1.x() - p2.x(), p1.y() - p2.y())
        v2 = (p3.x() - p2.x(), p3.y() - p2.y())

        n1 = normalize(v1)
        n2 = normalize(v2)

        # Dot product
        dot = max(min(n1[0] * n2[0] + n1[1] * n2[1], 1), -1)
        angle = math.acos(dot)

        if angle < 0.01:
            return [p2]

        # FIX: Convert all math results to Decimal before arithmetic
        radius_decimal = to_decimal(str(radius))
        angle_half = angle / 2
        tan_half_angle = math.tan(angle_half)
        
        # Convert tan result to Decimal before division
        tangent_length = radius_decimal / to_decimal(str(tan_half_angle))

        tp1 = QPointF(
            float(to_decimal(str(p2.x())) + to_decimal(str(n1[0])) * tangent_length), 
            float(to_decimal(str(p2.y())) + to_decimal(str(n1[1])) * tangent_length)
        )
        tp2 = QPointF(
            float(to_decimal(str(p2.x())) + to_decimal(str(n2[0])) * tangent_length),
            float(to_decimal(str(p2.y())) + to_decimal(str(n2[1])) * tangent_length)
        )

        # Bisector
        bisector = normalize(((n1[0] + n2[0]) / 2, (n1[1] + n2[1]) / 2))
        
        # FIX: Convert sin result to Decimal before division
        sin_half_angle = math.sin(angle_half)
        dist_to_center = radius_decimal / to_decimal(str(sin_half_angle))

        center = QPointF(
            float(to_decimal(str(p2.x())) + to_decimal(str(bisector[0])) * dist_to_center),
            float(to_decimal(str(p2.y())) + to_decimal(str(bisector[1])) * dist_to_center)
        )

        start_angle = math.atan2(tp1.y() - center.y(), tp1.x() - center.x())
        end_angle = math.atan2(tp2.y() - center.y(), tp2.x() - center.x())

        cross = (tp1.x() - center.x()) * (tp2.y() - center.y()) - (tp1.y() - center.y()) * (tp2.x() - center.x())

        points = []
        for i in range(segments + 1):
            t = i / segments
            if cross > 0:
                angle_t = start_angle + t * (end_angle - start_angle)
            else:
                if end_angle > start_angle:
                    end_angle -= 2 * math.pi
                angle_t = start_angle + t * (end_angle - start_angle)

            # FIX: Convert trigonometric results to Decimal before arithmetic
            cos_result = math.cos(angle_t)
            sin_result = math.sin(angle_t)
            
            x = float(to_decimal(str(center.x())) + radius_decimal * to_decimal(str(cos_result)))
            y = float(to_decimal(str(center.y())) + radius_decimal * to_decimal(str(sin_result)))
            
            points.append(QPointF(x, y))

        return points

    def draw_selected_pads_highlight(self, painter):
        """Draw selection highlights on selected pads"""
        if not self.selected_pads:
            return

        # Draw selection highlights
        painter.setPen(QPen(QColor("#FF00FF"), 3/self.zoom_factor)) # Magenta highlight
        painter.setBrush(QBrush()) # No fill

        pad_bounds_list = self.get_individual_pad_bounds_absolute()

        for pad_index in self.selected_pads:
            if pad_index < len(pad_bounds_list):
                bounds = pad_bounds_list[pad_index]
                if bounds:
                    # Convert bounds to Decimal for consistent arithmetic
                    min_x = to_decimal(str(bounds[0]))
                    min_y = to_decimal(str(bounds[1]))
                    max_x = to_decimal(str(bounds[2]))
                    max_y = to_decimal(str(bounds[3]))
                    
                    # Draw highlight rectangle slightly larger than pad
                    margin = to_decimal('0.1')
                    painter.drawRect(QRectF(
                        float(min_x - margin),
                        float(min_y - margin),
                        float(max_x - min_x + 2*margin),
                        float(max_y - min_y + 2*margin)
                    ))

    def draw_fiducials(self, painter):
        """Draw fiducial markers with keepout - only 2 at top-right and bottom-left corners"""
        if not self.footprint_data.get('fiducials_enabled', False):
            return

        # Get settings from the settings panel directly
        try:
            diameter = to_decimal(self.footprint_data.get('settings', {}).get('fiducial_diameter', 1.0))
            mask_opening = to_decimal(self.footprint_data.get('settings', {}).get('fiducial_mask_opening', 2.0))
            keepout_diameter = to_decimal(self.footprint_data.get('settings', {}).get('fiducial_keepout_diameter', 3.0))
            x_offset = to_decimal(self.footprint_data.get('settings', {}).get('fiducial_x_offset', 2.0))
            y_offset = to_decimal(self.footprint_data.get('settings', {}).get('fiducial_y_offset', 2.0))
            body_length = to_decimal(self.footprint_data.get('body_length', 5.0))
            body_width = to_decimal(self.footprint_data.get('body_width', 3.0))
        except (ValueError, TypeError):
            # Use default values if settings are invalid
            diameter = 1.0
            mask_opening = 2.0
            keepout_diameter = 3.0
            x_offset = 2.0
            y_offset = 2.0
            body_length = 5.0
            body_width = 3.0

        # Calculate body corners considering origin offset
        body_left = self.origin_offset_x
        body_right = self.origin_offset_x + body_length
        body_bottom = self.origin_offset_y - body_width  # Y-axis is flipped
        body_top = self.origin_offset_y

        # Calculate fiducial positions - top-right and bottom-left corners with offset
        positions = [
            (body_right + x_offset, body_top + y_offset),    # Top-right corner + offset
            (body_left - x_offset, body_bottom - y_offset),  # Bottom-left corner - offset
        ]

        for x, y in positions:
            # Draw keepout area first (largest circle)
            painter.setPen(QPen(QColor("#FF4500"), 2/self.zoom_factor))  # Orange Red for keepout
            painter.setBrush(QBrush())  # No fill
            painter.drawEllipse(QRectF(x - keepout_diameter/2, y - keepout_diameter/2, 
                                    keepout_diameter, keepout_diameter))

            # Draw mask opening (medium circle)
            painter.setPen(QPen(QColor("#8A2BE2"), 1/self.zoom_factor))  # Purple for mask
            painter.setBrush(QBrush())
            painter.drawEllipse(QRectF(x - mask_opening/2, y - mask_opening/2, 
                                    mask_opening, mask_opening))

            # Draw copper pad (smallest circle)
            painter.setPen(QPen(QColor("#FFD700"), 2/self.zoom_factor))  # Gold for fiducial
            # Create semi-transparent gold color correctly
            fiducial_color = QColor("#FFD700")
            fiducial_color.setAlpha(100)  # Semi-transparent
            painter.setBrush(QBrush(fiducial_color))
            painter.drawEllipse(QRectF(x - diameter/2, y - diameter/2, diameter, diameter))

            # Draw center cross
            cross_size = diameter / 4
            painter.setPen(QPen(QColor("#000000"), 1/self.zoom_factor))
            painter.drawLine(QPointF(x - cross_size, y), QPointF(x + cross_size, y))
            painter.drawLine(QPointF(x, y - cross_size), QPointF(x, y + cross_size))

    def draw_keepout_layers(self, painter):
        """Draw all keepout layers with proper merging"""
        settings = self.footprint_data.get('settings', {}) if hasattr(self, 'footprint_data') else {}
        
        # Get expansion values
        via_expansion = to_decimal(settings.get('via_keepout_expansion', '0.1'))
        package_expansion = to_decimal(settings.get('package_keepout_expansion', '0.05'))
        route_expansion = to_decimal(settings.get('route_keepout_expansion', '0.15'))
        
        # Draw keepout layers based on toggle states
        if self.show_via_keepout_checkbox.isChecked():
            self.draw_via_keepout_layer(painter, via_expansion)
        
        if self.show_package_keepout_checkbox.isChecked():
            self.draw_package_keepout_layer(painter, package_expansion)
            
        if self.show_route_keepout_checkbox.isChecked():
            self.draw_route_keepout_layer(painter, route_expansion)

    def draw_via_keepout_layer(self, painter, expansion):
        """Draw merged Via Keepout All layer for PTH and NPTH padstacks"""
        if not hasattr(self, 'footprint_data') or not self.footprint_data.get('padstacks'):
            return
        
        # Collect all via keepout shapes
        keepout_shapes = []
        
        for i, pad in enumerate(self.footprint_data['padstacks']):
            pad_type = pad['type']
            
            # Via keepout applies to PTH and NPTH padstacks
            if pad_type in ['PTH', 'PTH_oblong', 'PTH_rectangle', 'PTH_square', 'PTH_oblong_rect',
                        'NPTH', 'NPTH_oblong', 'NPTH_rectangle']:
                
                # Get absolute position
                absolute_positions = self.calculate_pad_absolute_positions()
                if i in absolute_positions:
                    x, y = absolute_positions[i]
                else:
                    continue
                
                # Create keepout shape based on pad type and expansion
                keepout_shape = self.create_keepout_shape(pad, x, y, expansion, 'via')
                if keepout_shape:
                    keepout_shapes.append(keepout_shape)
        
        # Merge overlapping shapes and draw
        if keepout_shapes:
            merged_path = self.merge_keepout_shapes(keepout_shapes)
            painter.setPen(QPen(QColor("#FF4500"), 1/self.zoom_factor))
            via_color = QColor("#FF4500")
            via_color.setAlpha(60)
            painter.setBrush(QBrush(via_color)) # Semi-transparent fill
            painter.drawPath(merged_path)

    def draw_package_keepout_layer(self, painter, expansion):
        """Draw merged Package Keepout Bottom layer for PTH and NPTH padstacks"""
        if not hasattr(self, 'footprint_data') or not self.footprint_data.get('padstacks'):
            return
            
        # Collect all package keepout shapes
        keepout_shapes = []
        
        for i, pad in enumerate(self.footprint_data['padstacks']):
            pad_type = pad['type']
            
            # Package keepout applies to PTH and NPTH padstacks
            if pad_type in ['PTH', 'PTH_oblong', 'PTH_rectangle', 'PTH_square', 'PTH_oblong_rect',
                        'NPTH', 'NPTH_oblong', 'NPTH_rectangle']:
                
                # Get absolute position
                absolute_positions = self.calculate_pad_absolute_positions()
                if i in absolute_positions:
                    x, y = absolute_positions[i]
                else:
                    continue
                
                # Create keepout shape based on pad type and expansion
                keepout_shape = self.create_keepout_shape(pad, x, y, expansion, 'package')
                if keepout_shape:
                    keepout_shapes.append(keepout_shape)
        
        # Merge overlapping shapes and draw
        if keepout_shapes:
            merged_path = self.merge_keepout_shapes(keepout_shapes)
            painter.setPen(QPen(QColor("#8B4513"), 1/self.zoom_factor))
            package_color = QColor("#8B4513")
            package_color.setAlpha(60)
            painter.setBrush(QBrush(package_color)) # Semi-transparent fill
# Semi-transparent fill            
            painter.drawPath(merged_path)

    def draw_route_keepout_layer(self, painter, expansion):
        """Draw Route Keepout All layer for NPTH padstacks only"""
        if not hasattr(self, 'footprint_data') or not self.footprint_data.get('padstacks'):
            return
            
        # Collect all route keepout shapes
        keepout_shapes = []
        
        for i, pad in enumerate(self.footprint_data['padstacks']):
            pad_type = pad['type']
            
            # Route keepout applies only to NPTH padstacks
            if pad_type in ['NPTH', 'NPTH_oblong', 'NPTH_rectangle']:
                
                # Get absolute position
                absolute_positions = self.calculate_pad_absolute_positions()
                if i in absolute_positions:
                    x, y = absolute_positions[i]
                else:
                    continue
                
                # Create keepout shape based on hole size and expansion
                keepout_shape = self.create_route_keepout_shape(pad, x, y, expansion)
                if keepout_shape:
                    keepout_shapes.append(keepout_shape)
        
        # Draw individual shapes (no merging needed for route keepout typically)
        painter.setPen(QPen(QColor("#DC143C"), 2/self.zoom_factor))
        painter.setBrush(QBrush()) # No fill, outline only
        
        for shape in keepout_shapes:
            painter.drawPath(shape)

    def create_keepout_shape(self, pad, x, y, expansion, keepout_type):
        """Create keepout shape based on pad type and expansion source"""
        pad_type = pad.get('type', 'square')
        path = QPainterPath()

        try:
            if keepout_type == 'via' or keepout_type == 'package':
                # FORCE RECTANGULAR SHAPES FOR VIA AND PACKAGE KEEPOUTS
                
                # Calculate rectangular bounds based on pad type
                if pad_type in ['PTH', 'NPTH']:
                    if pad_type == 'PTH':
                        pad_diameter = to_decimal(pad.get('pad_diameter', 1.2))
                        size = pad_diameter
                    else:
                        hole_diameter = to_decimal(pad.get('hole_diameter', 0.8))
                        size = hole_diameter
                    
                    # Create square keepout based on diameter
                    half_size = (size / 2) + expansion
                    path.addRect(QRectF(x - half_size, y - half_size, 2*half_size, 2*half_size))
                    
                elif pad_type == 'PTH_square':
                    pad_size = to_decimal(pad.get('pad_size', 1.5))
                    half_size = (pad_size / 2) + expansion
                    path.addRect(QRectF(x - half_size, y - half_size, 2*half_size, 2*half_size))
                    
                elif pad_type in ['PTH_oblong', 'PTH_rectangle', 'PTH_oblong_rect']:
                    pad_length = to_decimal(pad.get('pad_length', 2.0))
                    pad_width = to_decimal(pad.get('pad_width', 1.2))
                    half_length = (pad_length / 2) + expansion
                    half_width = (pad_width / 2) + expansion
                    
                    # Always create rectangle (no rounding for oblong)
                    path.addRect(QRectF(x - half_length, y - half_width, 2*half_length, 2*half_width))
                    
                elif pad_type in ['NPTH_oblong', 'NPTH_rectangle']:
                    hole_length = to_decimal(pad.get('hole_length', 1.5))
                    hole_width = to_decimal(pad.get('hole_width', 0.8))
                    half_length = (hole_length / 2) + expansion
                    half_width = (hole_width / 2) + expansion
                    
                    # Always create rectangle (no rounding for oblong)
                    path.addRect(QRectF(x - half_length, y - half_width, 2*half_length, 2*half_width))
                    
                else:
                    # Fallback to square for any other pad types
                    default_size = Decimal('1.0')
                    half_size = (default_size / 2) + expansion
                    path.addRect(QRectF(x - half_size, y - half_size, 2*half_size, 2*half_size))
                    
            else:
                # ORIGINAL SHAPE-FOLLOWING LOGIC FOR OTHER KEEPOUT TYPES
                # (Keep the existing logic for route keepout, etc.)
                if pad_type in ['PTH', 'NPTH', 'PTH_oblong', 'NPTH_oblong', 'PTH_rectangle', 'NPTH_rectangle', 'PTH_square', 'PTH_oblong_rect']:
                    # Expand from pad dimensions for PTH types, hole dimensions for NPTH types
                    if pad_type in ['PTH', 'PTH_oblong', 'PTH_rectangle', 'PTH_square', 'PTH_oblong_rect']:
                        # Expand from pad dimensions
                        if pad_type == 'PTH':
                            pad_diameter = to_decimal(pad.get('pad_diameter', 1.2))
                            radius = (pad_diameter / 2) + expansion
                            path.addEllipse(QRectF(x - radius, y - radius, 2*radius, 2*radius))
                        elif pad_type == 'PTH_square':
                            pad_size = to_decimal(pad.get('pad_size', 1.5))
                            half_size = (pad_size / 2) + expansion
                            path.addRect(QRectF(x - half_size, y - half_size, 2*half_size, 2*half_size))
                        elif pad_type in ['PTH_oblong', 'PTH_rectangle', 'PTH_oblong_rect']:
                            pad_length = to_decimal(pad.get('pad_length', 2.0))
                            pad_width = to_decimal(pad.get('pad_width', 1.2))
                            half_length = (pad_length / 2) + expansion
                            half_width = (pad_width / 2) + expansion
                            if pad_type in ['PTH_oblong', 'PTH_oblong_rect']:
                                # Create rounded rectangle for oblong
                                radius = min(half_width, half_length)
                                path.addRoundedRect(QRectF(x - half_length, y - half_width,
                                                        2*half_length, 2*half_width), radius, radius)
                            else:
                                # Rectangle for PTH_rectangle
                                path.addRect(QRectF(x - half_length, y - half_width,
                                                2*half_length, 2*half_width))

                    elif pad_type in ['NPTH', 'NPTH_oblong', 'NPTH_rectangle']:
                        # Expand from hole dimensions
                        if pad_type == 'NPTH':
                            hole_diameter = to_decimal(pad.get('hole_diameter', 0.8))
                            radius = (hole_diameter / 2) + expansion
                            path.addEllipse(QRectF(x - radius, y - radius, 2*radius, 2*radius))
                        elif pad_type in ['NPTH_oblong', 'NPTH_rectangle']:
                            hole_length = to_decimal(pad.get('hole_length', 1.5))
                            hole_width = to_decimal(pad.get('hole_width', 0.8))
                            half_length = (hole_length / 2) + expansion
                            half_width = (hole_width / 2) + expansion
                            if pad_type == 'NPTH_oblong':
                                # Create rounded rectangle for oblong
                                radius = min(half_width, half_length)
                                path.addRoundedRect(QRectF(x - half_length, y - half_width,
                                                        2*half_length, 2*half_width), radius, radius)
                            else:
                                # Rectangle for NPTH_rectangle
                                path.addRect(QRectF(x - half_length, y - half_width,
                                                2*half_length, 2*half_width))

        except (ValueError, TypeError):
            # Fallback to simple rectangle
            default_size = Decimal('1.0')
            half_size = (default_size / 2) + expansion
            path.addRect(QRectF(x - half_size, y - half_size, 2*half_size, 2*half_size))

        return path

    def create_route_keepout_shape(self, pad, x, y, expansion):
        """Create route keepout shape based on hole size and shape"""
        pad_type = pad['type']
        path = QPainterPath()
        
        try:
            if pad_type == 'NPTH':
                # Circle shape for round holes
                hole_diameter = to_decimal(pad.get('hole_diameter', 0.8))
                radius = (hole_diameter / 2) + expansion
                path.addEllipse(QRectF(x - radius, y - radius, 2*radius, 2*radius))
                
            elif pad_type == 'NPTH_oblong':
                # Oblong shape for oblong holes
                hole_length = to_decimal(pad.get('hole_length', 1.5))
                hole_width = to_decimal(pad.get('hole_width', 0.8))
                half_length = (hole_length / 2) + expansion
                half_width = (hole_width / 2) + expansion
                radius = min(half_width, half_length)
                path.addRoundedRect(QRectF(x - half_length, y - half_width,
                                        2*half_length, 2*half_width), radius, radius)
                                        
            elif pad_type == 'NPTH_rectangle':
                # Rectangle shape for rectangular holes
                hole_length = to_decimal(pad.get('hole_length', 1.5))
                hole_width = to_decimal(pad.get('hole_width', 0.8))
                half_length = (hole_length / 2) + expansion
                half_width = (hole_width / 2) + expansion
                path.addRect(QRectF(x - half_length, y - half_width,
                                2*half_length, 2*half_width))
                                
        except (ValueError, TypeError):
            # Fallback to simple circle
            default_radius = Decimal('0.5') + expansion
            path.addEllipse(QRectF(x - default_radius, y - default_radius,
                                2*default_radius, 2*default_radius))
        
        return path

    def merge_keepout_shapes(self, shapes):
        """Merge overlapping keepout shapes into a single unified path"""
        if not shapes:
            return QPainterPath()
        
        # Start with the first shape
        merged_path = shapes[0]
        
        # Union with all other shapes
        for shape in shapes[1:]:
            merged_path = merged_path.united(shape)
        
        # Simplify the result to clean up the outline
        return merged_path.simplified()



    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Get center point and apply offset
        center_x = self.width() // 2
        center_y = self.height() // 2

        # Apply translation with offset for cursor-centered zoom
        painter.translate(center_x + self.offset_x, center_y + self.offset_y)
        painter.scale(self.zoom_factor, -self.zoom_factor)  # Flip Y axis

        # ADD THIS NEW LINE TO APPLY ORIGIN OFFSET:
        
        # Clear cached positions when data changes
        self._absolute_positions = None

        # Rest of the paintEvent method remains the same...


        # Draw origin first
        self.draw_origin(painter)
        self.draw_fiducials(painter)

        # Draw body outline with shape support
        # Draw body outline with shape support
        body_bounds = None
        if all(k in self.footprint_data for k in ['body_length', 'body_width']):
            try:
                length = to_decimal(self.footprint_data['body_length'])
                width = to_decimal(self.footprint_data['body_width'])
                body_shape = self.footprint_data.get('body_shape', 'rectangle')
                
                painter.setPen(QPen(QColor("#FF69B4"), 2/self.zoom_factor)) # Pink
                painter.setBrush(QBrush()) # No fill
                
                # APPLY ORIGIN OFFSET ONLY TO BODY DRAWING
                painter.save()  # Save current state
                painter.translate(self.origin_offset_x, self.origin_offset_y)
                
                # In body drawing section, replace the rectangle drawing with:
                if body_shape == 'rectangle':
                    # Check if chamfers are enabled
                    chamfer_size = to_decimal(self.footprint_data.get('body_chamfer', '0'))
                    chamfer_corners = self.footprint_data.get('chamfer_corners', {})
                    
                    if chamfer_size > 0 and any(chamfer_corners.values()):
                        # Draw body with chamfers
                        self.draw_chamfered_body(painter, length, width, chamfer_size, chamfer_corners)
                    else:
                        # Draw regular rectangle
                        painter.drawRect(QRectF(0, -width, length, width))
                elif body_shape == 'round':
                    diameter = max(length, width)
                    # Draw body with top-left corner at origin (0,0) - account for Y-flip
                    painter.drawEllipse(QRectF(0, -diameter, diameter, diameter))

                    
                painter.restore()  # Restore original state
                
                # Calculate body_bounds WITHOUT offset (for other calculations)

                # Calculate body_bounds with top-left at origin (0,0)
                if body_shape == 'rectangle':
                    body_bounds = [0, -width, length, 0]  # [min_x, min_y, max_x, max_y]
                elif body_shape == 'round':
                    diameter = max(length, width)
                    body_bounds = [0, -diameter, diameter, 0]


                    
            except (ValueError, TypeError):
                pass


        # Get individual pad bounds for silkscreen calculation
        individual_pad_bounds = self.get_individual_pad_bounds_absolute()

        # Calculate overall pad bounds for courtyard
        pad_bounds = self.calculate_all_pads_bounds_absolute()

        # Draw silkscreen layer with gaps where pads overlap
        if body_bounds and self.footprint_data.get('silkscreen_enabled', True):
            try:
                airgap = to_decimal(self.footprint_data.get('silkscreen_airgap', 0.15))
            except (ValueError, TypeError):
                airgap = 0.15
            self.draw_silkscreen(painter, body_bounds, individual_pad_bounds, airgap)

        # Draw courtyard based on outermost bounds
        self.draw_courtyard(painter, body_bounds, pad_bounds)
        self.draw_noprob(painter, body_bounds, pad_bounds)

        # Draw pads with absolute positioning
        for i, pad in enumerate(self.footprint_data.get('padstacks', [])):
            self.draw_pad(painter, pad, i)

        self.draw_custom_layers(painter)
        
        # Draw thermal vias  
        self.draw_thermal_vias(painter)
        
        self.draw_dfa_bond_layer(painter)
            # NEW: Draw unique padstack names below footprint
        self.draw_unique_padstack_names(painter)

            # NEW: Draw keepout layers
        self.draw_keepout_layers(painter)
        # NEW: Draw selection highlights
        self.draw_selected_pads_highlight(painter)

        self.draw_ref_des(painter)

        # Draw dimensions based on overlay control states and selections
        if self.show_airgap_checkbox.isChecked():
            self.draw_all_airgap_dimensions(painter)
        
        if self.show_pitch_checkbox.isChecked():
            self.draw_all_pitch_dimensions(painter)

        # NEW: Draw instruction text
        self.draw_selection_instructions(painter)

    def draw_chamfered_body(self, painter, length, width, chamfer_size, chamfer_corners):
        """Draw body rectangle with selective corner chamfers"""
        path = QPainterPath()
        
        # Define corner points
        tl = (0, 0)  # Top-left
        tr = (length, 0)  # Top-right  
        bl = (0, -width)  # Bottom-left
        br = (length, -width)  # Bottom-right
        
        # Start at top-left, moving clockwise
        if chamfer_corners.get('tl', False):
            path.moveTo(chamfer_size, 0)
            path.lineTo(0, -chamfer_size)
        else:
            path.moveTo(0, 0)
        
        # Left edge to bottom-left
        if chamfer_corners.get('bl', False):
            path.lineTo(0, -width + chamfer_size)
            path.lineTo(chamfer_size, -width)
        else:
            path.lineTo(0, -width)
        
        # Bottom edge to bottom-right  
        if chamfer_corners.get('br', False):
            path.lineTo(length - chamfer_size, -width)
            path.lineTo(length, -width + chamfer_size)
        else:
            path.lineTo(length, -width)
        
        # Right edge to top-right
        if chamfer_corners.get('tr', False):
            path.lineTo(length, -chamfer_size)
            path.lineTo(length - chamfer_size, 0)
        else:
            path.lineTo(length, 0)
        
        # Top edge back to start
        if chamfer_corners.get('tl', False):
            path.lineTo(chamfer_size, 0)
        else:
            path.lineTo(0, 0)
        
        path.closeSubpath()
        painter.drawPath(path)



    def draw_selection_instructions(self, painter):
        """Draw instruction text for pad selection"""
        painter.save()
        painter.resetTransform()  # Switch to screen coordinates

        instructions = []
        if self.show_airgap_checkbox.isChecked() or self.show_pitch_checkbox.isChecked():
            if len(self.selected_pads) == 0:
                instructions.append("Click on 2 pads to measure dimensions")
            elif len(self.selected_pads) == 1:
                instructions.append("Click on 1 more pad to measure")
            elif len(self.selected_pads) == 2:
                instructions.append("Dimensions shown between selected pads")
                instructions.append("Click elsewhere to clear selection")

        if instructions:
            # Position at bottom-left
            y_start = self.height() - 60
            painter.setPen(QPen(QColor("#FFFFFF"), 1))
            font = QFont("Arial", 10)
            painter.setFont(font)

            for i, instruction in enumerate(instructions):
                # Draw background for better visibility
                text_rect = painter.fontMetrics().boundingRect(instruction)
                text_rect.moveTo(10, y_start + i * 20)
                text_rect.adjust(-3, -1, 3, 1)

                painter.setBrush(QBrush(QColor(0, 0, 0, 150)))
                painter.drawRect(text_rect)
                painter.setBrush(QBrush())
                painter.drawText(10, y_start + i * 20 + 15, instruction)

        painter.restore()

    def calculate_all_pads_bounds_absolute(self):
        """Calculate the outer bounding box of all pads using absolute pad bounds"""
        pad_bounds_list = self.get_individual_pad_bounds_absolute()
        if not pad_bounds_list:
            return None

        min_x = min(pb[0] for pb in pad_bounds_list)
        min_y = min(pb[1] for pb in pad_bounds_list)
        max_x = max(pb[2] for pb in pad_bounds_list)
        max_y = max(pb[3] for pb in pad_bounds_list)

        return [min_x, min_y, max_x, max_y]

    def draw_dfa_bond_layer(self, painter):
        """Draw DFA bond layer covering body + only extending pad portions (with dotted fill)"""
        if not self.show_dfa_bond_checkbox.isChecked():
            return
        
        # Fixed expansion (no settings panel needed)
        expansion = Decimal('0.0')  # 0.1mm expansion
        line_width = Decimal('0.5')  # 0.05mm line width
        
        # Calculate body bounds with origin offset
        body_bounds = None
        if all(k in self.footprint_data for k in ['body_length', 'body_width']):
            try:
                length = to_decimal(self.footprint_data['body_length'])
                width = to_decimal(self.footprint_data['body_width'])
                
                body_bounds = [
                    self.origin_offset_x,                    # min_x (left)
                    self.origin_offset_y - width,            # min_y (bottom)
                    self.origin_offset_x + length,           # max_x (right)
                    self.origin_offset_y                     # max_y (top)
                ]
            except (ValueError, TypeError):
                return
        
        if not body_bounds:
            return
        
        # Get individual pad bounds
        pad_bounds_list = self.get_individual_pad_bounds_absolute()
        
        # Create a path for the DFA bond layer
        bond_path = QPainterPath()
        
        # Add body rectangle with expansion
        body_rect = QRectF(
            float(body_bounds[0] - expansion),
            float(body_bounds[1] - expansion), 
            float(body_bounds[2] - body_bounds[0] + 2*expansion),
            float(body_bounds[3] - body_bounds[1] + 2*expansion)
        )
        bond_path.addRect(body_rect)
        
        # Add only the extending parts of pads
        for pad_bounds in pad_bounds_list:
            if not pad_bounds:
                continue
                
            pad_min_x, pad_min_y, pad_max_x, pad_max_y = pad_bounds
            
            # Check if pad extends outside body in any direction
            extends_left = pad_min_x < body_bounds[0]
            extends_right = pad_max_x > body_bounds[2]
            extends_bottom = pad_min_y < body_bounds[1]
            extends_top = pad_max_y > body_bounds[3]
            
            # Only add extending portions
            if extends_left:
                # Left extending portion
                extend_rect = QRectF(
                    float(pad_min_x - expansion),
                    float(max(pad_min_y, body_bounds[1]) - expansion),
                    float(body_bounds[0] - pad_min_x + expansion),
                    float(min(pad_max_y, body_bounds[3]) - max(pad_min_y, body_bounds[1]) + 2*expansion)
                )
                bond_path.addRect(extend_rect)
            
            if extends_right:
                # Right extending portion
                extend_rect = QRectF(
                    float(body_bounds[2]),
                    float(max(pad_min_y, body_bounds[1]) - expansion),
                    float(pad_max_x - body_bounds[2] + expansion),
                    float(min(pad_max_y, body_bounds[3]) - max(pad_min_y, body_bounds[1]) + 2*expansion)
                )
                bond_path.addRect(extend_rect)
            
            if extends_bottom:
                # Bottom extending portion
                extend_rect = QRectF(
                    float(max(pad_min_x, body_bounds[0]) - expansion),
                    float(pad_min_y - expansion),
                    float(min(pad_max_x, body_bounds[2]) - max(pad_min_x, body_bounds[0]) + 2*expansion),
                    float(body_bounds[1] - pad_min_y + expansion)
                )
                bond_path.addRect(extend_rect)
            
            if extends_top:
                # Top extending portion
                extend_rect = QRectF(
                    float(max(pad_min_x, body_bounds[0]) - expansion),
                    float(body_bounds[3]),
                    float(min(pad_max_x, body_bounds[2]) - max(pad_min_x, body_bounds[0]) + 2*expansion),
                    float(pad_max_y - body_bounds[3] + expansion)
                )
                bond_path.addRect(extend_rect)
            
            # Handle corner extensions (pads that extend diagonally)
            if extends_left and extends_bottom:
                # Bottom-left corner
                corner_rect = QRectF(
                    float(pad_min_x - expansion),
                    float(pad_min_y - expansion),
                    float(body_bounds[0] - pad_min_x + expansion),
                    float(body_bounds[1] - pad_min_y + expansion)
                )
                bond_path.addRect(corner_rect)
            
            if extends_right and extends_bottom:
                # Bottom-right corner
                corner_rect = QRectF(
                    float(body_bounds[2]),
                    float(pad_min_y - expansion),
                    float(pad_max_x - body_bounds[2] + expansion),
                    float(body_bounds[1] - pad_min_y + expansion)
                )
                bond_path.addRect(corner_rect)
            
            if extends_left and extends_top:
                # Top-left corner
                corner_rect = QRectF(
                    float(pad_min_x - expansion),
                    float(body_bounds[3]),
                    float(body_bounds[0] - pad_min_x + expansion),
                    float(pad_max_y - body_bounds[3] + expansion)
                )
                bond_path.addRect(corner_rect)
            
            if extends_right and extends_top:
                # Top-right corner
                corner_rect = QRectF(
                    float(body_bounds[2]),
                    float(body_bounds[3]),
                    float(pad_max_x - body_bounds[2] + expansion),
                    float(pad_max_y - body_bounds[3] + expansion)
                )
                bond_path.addRect(corner_rect)
        
        # Draw the combined DFA bond layer with DOTTED FILL
        painter.setPen(QPen(QColor("#00D0D0"), float(line_width/self.zoom_factor)))  # Dark Orange
        bond_color = QColor("#00D0D0")
  # Slightly more opaque for better visibility with dots
        # CHANGED: Use dotted pattern instead of solid fill
        painter.setBrush(QBrush(bond_color, Qt.BrushStyle.Dense7Pattern))
        painter.drawPath(bond_path)

    def draw_ref_des(self, painter):
        """Draw reference designator above the footprint (after courtyard)"""
        ref_des = self.footprint_data.get('ref_des', '').strip()
        if not ref_des:
            return

        # Get text settings
        settings = self.footprint_data.get('text_settings', {})
        text_height = to_decimal(settings.get('text_height', '0.5'))

        # Calculate courtyard expansion
        expansion = to_decimal(self.footprint_data.get('noprob_expansion', '0.51'))

        # SIMPLIFIED APPROACH: Find the highest point of all elements
        highest_y = Decimal('-inf')
        text_center_x = Decimal('0')  # Default to origin

        # Check body bounds
        if all(k in self.footprint_data for k in ['body_length', 'body_width']):
            width = to_decimal(self.footprint_data['body_width'])
            length = to_decimal(self.footprint_data['body_length'])

            body_top = self.origin_offset_y
            highest_y = max(highest_y, body_top)

            # ✅ Calculate body center X
            text_center_x = self.origin_offset_x + (length / 2)

        # Check pad bounds
        pad_bounds = self.calculate_all_pads_bounds_absolute()
        if pad_bounds:
            pad_top = to_decimal(str(pad_bounds[3]))  # pad_bounds[3] is max_y
            highest_y = max(highest_y, pad_top)

        # If no bounds found, use default
        if highest_y == Decimal('-inf'):
            highest_y = Decimal('1.0')  # Default 1mm above origin

        # ✅ Final text Y position (above highest element + courtyard + offset)
        text_y = highest_y + expansion + Decimal('0.5')

        # Draw in world coordinates
        painter.save()

        # Set text pen color and base zoom width
        painter.setPen(QPen(QColor("#00FF00"), self.zoom_factor))  # Green

        # Convert to screen coordinates for sizing
        transform = painter.worldTransform()
        screen_pos = transform.map(QPointF(float(text_center_x), float(text_y)))

        # Switch to screen coordinates for text rendering
        painter.save()
        painter.resetTransform()

        # Calculate zoom-adjusted font size
        font_size = float(text_height * to_decimal(str(self.zoom_factor)))
        font = QFont("Arial", int(font_size))
        font.setBold(True)
        painter.setFont(font)

        # Center text using font metrics
        fm = painter.fontMetrics()
        text_rect = fm.boundingRect(ref_des)
        text_rect.moveCenter(screen_pos.toPoint())

        # Draw text with zoom-aware pen width
        painter.setPen(QPen(QColor("#00FF00"), max(1, int(Decimal('2') / to_decimal(str(self.zoom_factor))))))
        painter.setBrush(QBrush())
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, ref_des)

        painter.restore()
        painter.restore()




    def draw_courtyard(self, painter, body_bounds, pad_bounds):
        """Draw courtyard based on outermost bounds of body or pads with line width adjustments"""
        try:
            base_expansion = to_decimal(self.footprint_data.get('courtyard_expansion', '0.25'))
            courtyard_line_width = to_decimal(self.footprint_data.get('courtyard_line_width', '0.1'))
            body_line_width = to_decimal(self.footprint_data.get('body_line_width', '0.05'))
            body_shape = self.footprint_data.get('body_shape', 'rectangle')  # Get body shape
        except (ValueError, TypeError):
            base_expansion = Decimal('0.25')
            courtyard_line_width = Decimal('0.1')
            body_line_width = Decimal('0.05')
            body_shape = 'rectangle'

        # Helper function to convert bounds to Decimal tuples
        def safe_decimal_bounds(bounds):
            """Convert bounds tuple to Decimal tuple"""
            if bounds is None:
                return None
            return tuple(to_decimal(str(coord)) for coord in bounds)

        # Convert all bounds to Decimal
        body_bounds_decimal = safe_decimal_bounds(body_bounds)
        pad_bounds_decimal = safe_decimal_bounds(pad_bounds)

        # Adjust body_bounds for origin offset if present
        if body_bounds_decimal:
            body_bounds_adjusted = (
                body_bounds_decimal[0] + self.origin_offset_x,
                body_bounds_decimal[1] + self.origin_offset_y,
                body_bounds_decimal[2] + self.origin_offset_x,
                body_bounds_decimal[3] + self.origin_offset_y
            )
        else:
            body_bounds_adjusted = None

        # Handle round body shape with circular courtyard
        if body_shape == 'round' and body_bounds_adjusted:
            # Calculate circle parameters for round body
            center_x = (body_bounds_adjusted[0] + body_bounds_adjusted[2]) / Decimal('2')
            center_y = (body_bounds_adjusted[1] + body_bounds_adjusted[3]) / Decimal('2')
            body_radius = (body_bounds_adjusted[2] - body_bounds_adjusted[0]) / Decimal('2')
            
            # Check if pads extend beyond body circle
            max_pad_distance = Decimal('0')
            if pad_bounds_decimal:
                # Check all corners of pad bounds rectangle to find max distance from center
                pad_corners = [
                    (pad_bounds_decimal[0], pad_bounds_decimal[1]),  # bottom-left
                    (pad_bounds_decimal[2], pad_bounds_decimal[1]),  # bottom-right
                    (pad_bounds_decimal[2], pad_bounds_decimal[3]),  # top-right
                    (pad_bounds_decimal[0], pad_bounds_decimal[3])   # top-left
                ]
                
                for corner_x, corner_y in pad_corners:
                    distance = ((corner_x - center_x)**2 + (corner_y - center_y)**2).sqrt()
                    max_pad_distance = max(max_pad_distance, distance)
            
            # Determine courtyard radius
            if max_pad_distance > body_radius:
                # Pads extend beyond body - use pad-based expansion
                courtyard_radius = max_pad_distance + base_expansion + (courtyard_line_width / 2)
            else:
                # Body is outermost - use body-based expansion
                courtyard_radius = body_radius + base_expansion + (courtyard_line_width / 2) + (body_line_width / 2)
            
            # Draw circular courtyard
            painter.setPen(QPen(QColor("#00FF00"), 1/self.zoom_factor))  # Green
            painter.setBrush(QBrush())  # No fill
            
            courtyard_diameter = courtyard_radius * 2
            painter.drawEllipse(QRectF(
                float(center_x - courtyard_radius),
                float(center_y - courtyard_radius),
                float(courtyard_diameter),
                float(courtyard_diameter)
            ))
            return

        # Original rectangular courtyard logic for rectangular bodies
        # Determine outermost bounds using Decimal arithmetic
        outermost_bounds = None
        outermost_bounds_type = None

        if body_bounds_adjusted and pad_bounds_decimal:
            # Use whichever is outermost - all Decimal operations
            outermost_bounds = [
                min(body_bounds_adjusted[0], pad_bounds_decimal[0]), # min_x
                min(body_bounds_adjusted[1], pad_bounds_decimal[1]), # min_y
                max(body_bounds_adjusted[2], pad_bounds_decimal[2]), # max_x
                max(body_bounds_adjusted[3], pad_bounds_decimal[3])  # max_y
            ]

            # Determine which bounds are actually outermost
            if (body_bounds_adjusted[0] <= pad_bounds_decimal[0] and
                body_bounds_adjusted[1] <= pad_bounds_decimal[1] and
                body_bounds_adjusted[2] >= pad_bounds_decimal[2] and
                body_bounds_adjusted[3] >= pad_bounds_decimal[3]):
                outermost_bounds_type = 'body'
            else:
                outermost_bounds_type = 'pad'

        elif body_bounds_adjusted:
            outermost_bounds = list(body_bounds_adjusted)
            outermost_bounds_type = 'body'
        elif pad_bounds_decimal:
            outermost_bounds = list(pad_bounds_decimal)
            outermost_bounds_type = 'pad'

        if outermost_bounds:
            # Calculate adjusted expansion based on outermost bounds type
            expansion = base_expansion
            if outermost_bounds_type == 'pad':
                expansion += courtyard_line_width / 2
            elif outermost_bounds_type == 'body':
                expansion += (courtyard_line_width / 2) + (body_line_width / 2)

            # Apply courtyard expansion - all Decimal arithmetic
            courtyard_bounds = [
                outermost_bounds[0] - expansion, # min_x
                outermost_bounds[1] - expansion, # min_y
                outermost_bounds[2] + expansion, # max_x
                outermost_bounds[3] + expansion  # max_y
            ]

            # Draw rectangular courtyard - convert to float only for PyQt
            painter.setPen(QPen(QColor("#00FF00"), 1/self.zoom_factor)) # Green
            painter.setBrush(QBrush()) # No fill
            courtyard_width = courtyard_bounds[2] - courtyard_bounds[0]
            courtyard_height = courtyard_bounds[3] - courtyard_bounds[1]

            painter.drawRect(QRectF(
                float(courtyard_bounds[0]),
                float(courtyard_bounds[1]),
                float(courtyard_width),
                float(courtyard_height)
            ))

    def draw_noprob(self, painter, body_bounds, pad_bounds):
        """Draw courtyard with per-side expansion based on outermost bounds (body or pads)"""
        if not self.show_noprob_top and not self.show_noprob_bottom:
            return  # Skip drawing if both are disabled
        try:
            base_expansion = to_decimal(self.footprint_data.get('noprob_expansion', '0.51'))
            noprob_line_width = to_decimal(self.footprint_data.get('noprob_line_width', '0.1'))
            body_line_width = to_decimal(self.footprint_data.get('body_line_width', '0.05'))
        except (ValueError, TypeError):
            base_expansion = Decimal('0.51')
            noprob_line_width = Decimal('0.1')
            body_line_width = Decimal('0.05')

        courtyard_line_W = noprob_line_width / 2
        body_line_W = body_line_width / 2
        body_linecourtyard = courtyard_line_W

        # Convert bounds to Decimal
        def safe_decimal_bounds(bounds):
            if bounds is None:
                return None
            return tuple(to_decimal(str(coord)) for coord in bounds)

        body_bounds_decimal = safe_decimal_bounds(body_bounds)
        pad_bounds_decimal = safe_decimal_bounds(pad_bounds)

        # Apply origin offset to body bounds
        body_bounds_adjusted = None
        if body_bounds_decimal:
            body_bounds_adjusted = (
                body_bounds_decimal[0] + self.origin_offset_x,
                body_bounds_decimal[1] + self.origin_offset_y,
                body_bounds_decimal[2] + self.origin_offset_x,
                body_bounds_decimal[3] + self.origin_offset_y
            )

        # Per-side comparisons
        outermost_left = outermost_right = outermost_top = outermost_bottom = None
        outermost_bounds_type_left = outermost_bounds_type_right = outermost_bounds_type_top = outermost_bounds_type_bottom = None

        if body_bounds_adjusted and pad_bounds_decimal:
            # Left
            if body_bounds_adjusted[0] <= pad_bounds_decimal[0]:
                outermost_left = body_bounds_adjusted[0]
                outermost_bounds_type_left = 'body'
            else:
                outermost_left = pad_bounds_decimal[0]
                outermost_bounds_type_left = 'pad'
            # Right
            if body_bounds_adjusted[2] >= pad_bounds_decimal[2]:
                outermost_right = body_bounds_adjusted[2]
                outermost_bounds_type_right = 'body'
            else:
                outermost_right = pad_bounds_decimal[2]
                outermost_bounds_type_right = 'pad'
            # Bottom
            if body_bounds_adjusted[1] <= pad_bounds_decimal[1]:
                outermost_bottom = body_bounds_adjusted[1]
                outermost_bounds_type_bottom = 'body'
            else:
                outermost_bottom = pad_bounds_decimal[1]
                outermost_bounds_type_bottom = 'pad'
            # Top
            if body_bounds_adjusted[3] >= pad_bounds_decimal[3]:
                outermost_top = body_bounds_adjusted[3]
                outermost_bounds_type_top = 'body'
            else:
                outermost_top = pad_bounds_decimal[3]
                outermost_bounds_type_top = 'pad'

        elif body_bounds_adjusted:
            outermost_left = body_bounds_adjusted[0]
            outermost_right = body_bounds_adjusted[2]
            outermost_bottom = body_bounds_adjusted[1]
            outermost_top = body_bounds_adjusted[3]
            outermost_bounds_type_left = outermost_bounds_type_right = outermost_bounds_type_top = outermost_bounds_type_bottom = 'body'

        elif pad_bounds_decimal:
            outermost_left = pad_bounds_decimal[0]
            outermost_right = pad_bounds_decimal[2]
            outermost_bottom = pad_bounds_decimal[1]
            outermost_top = pad_bounds_decimal[3]
            outermost_bounds_type_left = outermost_bounds_type_right = outermost_bounds_type_top = outermost_bounds_type_bottom = 'pad'

        if outermost_left is not None:
            # Expansion logic per side
            def get_expansion(bound_type):
                return base_expansion + (courtyard_line_W if bound_type == 'pad' else body_linecourtyard)

            expansion_left = get_expansion(outermost_bounds_type_left)
            expansion_right = get_expansion(outermost_bounds_type_right)
            expansion_bottom = get_expansion(outermost_bounds_type_bottom)
            expansion_top = get_expansion(outermost_bounds_type_top)

            # Final courtyard bounds
            courtyard_bounds = [
                outermost_left - expansion_left,
                outermost_bottom - expansion_bottom,
                outermost_right + expansion_right,
                outermost_top + expansion_top
            ]

            # Drawing
            painter.setPen(QPen(QColor("#00FFC8"), 1 / self.zoom_factor))  # Green, width scaled by zoom
            painter.setBrush(QBrush())  # No fill

            width = courtyard_bounds[2] - courtyard_bounds[0]
            height = courtyard_bounds[3] - courtyard_bounds[1]

            painter.drawRect(QRectF(
                float(courtyard_bounds[0]),
                float(courtyard_bounds[1]),
                float(width),
                float(height)
            ))


    def draw_silkscreen(self, painter, body_bounds, individual_pad_bounds, airgap=0.15):
        """Draw silkscreen exactly along body outline with gaps only where pads overlap with airgap"""
        if not body_bounds:
            return

        min_x, min_y, max_x, max_y = body_bounds
        body_shape = self.footprint_data.get('body_shape', 'rectangle')

        # Set silkscreen line properties
        line_width = 4/self.zoom_factor
        painter.setPen(QPen(QColor("#FFF305"), line_width))

        # MOVE THESE HELPER FUNCTIONS TO THE TOP
        # Helper function to merge overlapping intervals
        def merge_intervals(intervals):
            """Merge overlapping intervals in the form [(start, end), ...]"""
            if not intervals:
                return []
            intervals = sorted(intervals, key=lambda x: x[0])
            merged = [intervals[0]]
            for current in intervals[1:]:
                last = merged[-1]
                if current[0] <= last[1]:
                    merged[-1] = (last[0], max(last[1], current[1]))
                else:
                    merged.append(current)
            return merged

        # Helper function to convert pad bounds to Decimal
        def safe_decimal_bounds(bounds):
            """Convert pad bounds tuple to Decimal tuple"""
            if bounds is None:
                return None
            return tuple(to_decimal(str(coord)) for coord in bounds)

        # Helper function to draw line segments with gaps where pads interfere
        def draw_line_with_pad_gaps(x1, y1, x2, y2, pad_bounds_list, gap, orientation):
            """Draw line segment with gaps where pads (+ airgap) would overlap"""
            # Convert gap to Decimal if not already
            gap_decimal = to_decimal(str(gap))

            if orientation == 'horizontal':
                start_pos = min(x1, x2)
                end_pos = max(x1, x2)
                line_y = y1

                intersections = []
                for pad_bounds in pad_bounds_list:
                    if not pad_bounds:
                        continue
                    # Convert pad bounds to Decimal for arithmetic
                    bounds_decimal = safe_decimal_bounds(pad_bounds)
                    if not bounds_decimal:
                        continue

                    px_min, py_min, px_max, py_max = bounds_decimal

                    # Expand pad bounds by airgap - now all Decimal arithmetic
                    pad_min_x = px_min - gap_decimal
                    pad_max_x = px_max + gap_decimal
                    pad_min_y = py_min - gap_decimal
                    pad_max_y = py_max + gap_decimal

                    # Check if this horizontal line intersects with expanded pad
                    if (line_y >= pad_min_y and line_y <= pad_max_y and
                        pad_max_x >= start_pos and pad_min_x <= end_pos):
                        # Calculate intersection range
                        inter_start = max(start_pos, pad_min_x)
                        inter_end = min(end_pos, pad_max_x)
                        intersections.append((float(inter_start), float(inter_end)))

                # Sort and merge overlapping intersections
                merged = merge_intervals(intersections)

                # Draw line segments between gaps
                current_pos = start_pos
                for gap_start, gap_end in merged:
                    if current_pos < gap_start:
                        painter.drawLine(QPointF(float(current_pos), float(line_y)), QPointF(float(gap_start), float(line_y)))
                    current_pos = gap_end

                # Draw final segment if needed
                if current_pos < end_pos:
                    painter.drawLine(QPointF(float(current_pos), float(line_y)), QPointF(float(end_pos), float(line_y)))

            else:  # vertical
                start_pos = min(y1, y2)
                end_pos = max(y1, y2)
                line_x = x1

                intersections = []
                for pad_bounds in pad_bounds_list:
                    if not pad_bounds:
                        continue
                    # Convert pad bounds to Decimal for arithmetic
                    bounds_decimal = safe_decimal_bounds(pad_bounds)
                    if not bounds_decimal:
                        continue

                    px_min, py_min, px_max, py_max = bounds_decimal

                    # Expand pad bounds by airgap - now all Decimal arithmetic
                    pad_min_x = px_min - gap_decimal
                    pad_max_x = px_max + gap_decimal
                    pad_min_y = py_min - gap_decimal
                    pad_max_y = py_max + gap_decimal

                    # Check if this vertical line intersects with expanded pad
                    if (line_x >= pad_min_x and line_x <= pad_max_x and
                        pad_max_y >= start_pos and pad_min_y <= end_pos):
                        # Calculate intersection range
                        inter_start = max(start_pos, pad_min_y)
                        inter_end = min(end_pos, pad_max_y)
                        intersections.append((float(inter_start), float(inter_end)))

                # Sort and merge overlapping intersections
                merged = merge_intervals(intersections)

                # Draw line segments between gaps
                current_pos = start_pos
                for gap_start, gap_end in merged:
                    if current_pos < gap_start:
                        painter.drawLine(QPointF(float(line_x), float(current_pos)), QPointF(float(line_x), float(gap_start)))
                    current_pos = gap_end

                # Draw final segment if needed
                if current_pos < end_pos:
                    painter.drawLine(QPointF(float(line_x), float(current_pos)), QPointF(float(line_x), float(end_pos)))

        if body_shape == 'rectangle':
            # Check if chamfered silkscreen is enabled
            follow_chamfer = self.footprint_data.get('silkscreen_follow_chamfer', False)
            chamfer_size = to_decimal(self.footprint_data.get('body_chamfer', '0'))
            chamfer_corners = self.footprint_data.get('chamfer_corners', {})

            # APPLY ORIGIN OFFSET TO BODY BOUNDS FOR SILKSCREEN
            min_x = body_bounds[0] + self.origin_offset_x
            min_y = body_bounds[1] + self.origin_offset_y
            max_x = body_bounds[2] + self.origin_offset_x
            max_y = body_bounds[3] + self.origin_offset_y

            if follow_chamfer and chamfer_size > 0 and any(chamfer_corners.values()):
                # ===== CHAMFERED SILKSCREEN LOGIC WITH PAD GAPS =====
                # Convert chamfer_size to Decimal
                chamfer_size = to_decimal(str(chamfer_size))
                
                # Generate chamfered body segments
                points = []
                
                # Start from top-left, moving clockwise with chamfers
                if chamfer_corners.get('tl', False):
                    # Start below the chamfer
                    points.append((min_x, max_y - chamfer_size))
                    # Draw chamfer line to the right
                    points.append((min_x + chamfer_size, max_y))
                else:
                    # Start at top-left corner
                    points.append((min_x, max_y))

                # Top edge to top-right
                if chamfer_corners.get('tr', False):
                    # Draw to start of top-right chamfer
                    points.append((max_x - chamfer_size, max_y))
                    # Draw chamfer line down
                    points.append((max_x, max_y - chamfer_size))
                else:
                    # Draw to top-right corner
                    points.append((max_x, max_y))

                # Right edge to bottom-right
                if chamfer_corners.get('br', False):
                    # Draw to start of bottom-right chamfer
                    points.append((max_x, min_y + chamfer_size))
                    # Draw chamfer line to the left
                    points.append((max_x - chamfer_size, min_y))
                else:
                    # Draw to bottom-right corner
                    points.append((max_x, min_y))

                # Bottom edge to bottom-left
                if chamfer_corners.get('bl', False):
                    # Draw to start of bottom-left chamfer
                    points.append((min_x + chamfer_size, min_y))
                    # Draw chamfer line up
                    points.append((min_x, min_y + chamfer_size))
                else:
                    # Draw to bottom-left corner
                    points.append((min_x, min_y))

                # Left edge back to start
                if chamfer_corners.get('tl', False):
                    # Draw to start of top-left chamfer (close the path)
                    points.append((min_x, max_y - chamfer_size))
                else:
                    # Draw to top-left corner (close the path)
                    points.append((min_x, max_y))

                # Generate line segments from points and apply gap logic
                for i in range(len(points) - 1):
                    p1x, p1y = points[i]
                    p2x, p2y = points[i + 1]
                    dx = float(p2x - p1x)
                    dy = float(p2y - p1y)
                    eps = 1e-9  # numerical tolerance

                    # Horizontal
                    if abs(dy) < eps:
                        draw_line_with_pad_gaps(p1x, p1y, p2x, p2y, individual_pad_bounds, airgap, 'horizontal')
                    # Vertical
                    elif abs(dx) < eps:
                        draw_line_with_pad_gaps(p1x, p1y, p2x, p2y, individual_pad_bounds, airgap, 'vertical')
                    # Diagonal chamfer: draw directly (gap logic is H/V-only)
                    else:
                        painter.drawLine(QPointF(float(p1x), float(p1y)), QPointF(float(p2x), float(p2y)))

            else:
                # ===== STANDARD RECTANGULAR SILKSCREEN LOGIC =====
                # Draw all four sides of rectangular body outline with gaps where pads interfere
                
                # Top line
                draw_line_with_pad_gaps(min_x, max_y, max_x, max_y, individual_pad_bounds, airgap, 'horizontal')
                # Bottom line
                draw_line_with_pad_gaps(min_x, min_y, max_x, min_y, individual_pad_bounds, airgap, 'horizontal')
                # Left line
                draw_line_with_pad_gaps(min_x, min_y, min_x, max_y, individual_pad_bounds, airgap, 'vertical')
                # Right line
                draw_line_with_pad_gaps(max_x, min_y, max_x, max_y, individual_pad_bounds, airgap, 'vertical')

        # ... rest of the method for round shapes, etc.

        elif body_shape == 'round':
            # ===== ROUND SILKSCREEN LOGIC =====
            # APPLY ORIGIN OFFSET TO BODY BOUNDS FOR SILKSCREEN
            min_x = body_bounds[0] + self.origin_offset_x
            min_y = body_bounds[1] + self.origin_offset_y
            max_x = body_bounds[2] + self.origin_offset_x
            max_y = body_bounds[3] + self.origin_offset_y

            # Calculate circle parameters
            center_x = (min_x + max_x) / Decimal('2')
            center_y = (min_y + max_y) / Decimal('2')
            radius = (max_x - min_x) / Decimal('2')

            # Convert airgap to Decimal
            airgap_decimal = to_decimal(str(airgap))

            # Check if any pads overlap with the circle outline
            has_pad_overlaps = False
            for pad_bounds in individual_pad_bounds:
                if not pad_bounds:
                    continue

                # Convert pad bounds to Decimal
                px_min, py_min, px_max, py_max = [to_decimal(str(coord)) for coord in pad_bounds]

                # Expand pad bounds by airgap
                pad_min_x = px_min - airgap_decimal
                pad_max_x = px_max + airgap_decimal
                pad_min_y = py_min - airgap_decimal
                pad_max_y = py_max + airgap_decimal

                # Simple check: if pad rectangle intersects with circle bounds
                circle_left = center_x - radius
                circle_right = center_x + radius
                circle_top = center_y + radius
                circle_bottom = center_y - radius

                if (pad_max_x >= circle_left and pad_min_x <= circle_right and
                    pad_max_y >= circle_bottom and pad_min_y <= circle_top):
                    has_pad_overlaps = True
                    break

            if not has_pad_overlaps:
                # No pad overlaps, draw complete circle
                painter.drawEllipse(QRectF(float(min_x), float(min_y), float(max_x - min_x), float(max_y - min_y)))
            else:
                # Draw circle with gaps - simplified approach using small arc segments
                num_segments = 72  # 5-degree segments
                angle_step = 360.0 / num_segments

                for i in range(num_segments):
                    start_angle = i * angle_step
                    end_angle = (i + 1) * angle_step

                    # Calculate midpoint of this arc segment
                    mid_angle = math.radians((start_angle + end_angle) / 2)
                    mid_x = center_x + radius * Decimal(str(math.cos(mid_angle)))
                    mid_y = center_y + radius * Decimal(str(math.sin(mid_angle)))

                    # Check if this segment overlaps with any expanded pad
                    segment_overlaps = False
                    for pad_bounds in individual_pad_bounds:
                        if not pad_bounds:
                            continue

                        # Convert pad bounds to Decimal
                        px_min, py_min, px_max, py_max = [to_decimal(str(coord)) for coord in pad_bounds]

                        # Expand pad bounds by airgap
                        pad_min_x = px_min - airgap_decimal
                        pad_max_x = px_max + airgap_decimal
                        pad_min_y = py_min - airgap_decimal
                        pad_max_y = py_max + airgap_decimal

                        # Check if segment midpoint is inside expanded pad rectangle
                        if (mid_x >= pad_min_x and mid_x <= pad_max_x and
                            mid_y >= pad_min_y and mid_y <= pad_max_y):
                            segment_overlaps = True
                            break

                    # Draw this segment if it doesn't overlap with pads
                    if not segment_overlaps:
                        # Use drawArc for precise arc drawing
                        arc_rect = QRectF(float(min_x), float(min_y), float(max_x - min_x), float(max_y - min_y))
                        start_angle_16 = int(start_angle * 16)
                        span_angle_16 = int(angle_step * 16)
                        painter.drawArc(arc_rect, start_angle_16, span_angle_16)



    def draw_pad(self, painter, pad, pad_index=None):
        """Draw pad using absolute position with proper layer handling for TH pads"""
        # Get absolute positions
        absolute_positions = getattr(self, '_absolute_positions', None)
        if absolute_positions is None:
            absolute_positions = self.calculate_pad_absolute_positions()
            self._absolute_positions = absolute_positions

        # Use absolute position if available, otherwise fall back to direct offsets
        if pad_index is not None and pad_index in absolute_positions:
            x, y = absolute_positions[pad_index]
        else:
            try:
                x = to_decimal(pad.get('x_offset', 0))
                y = to_decimal(pad.get('y_offset', 0))
            except (ValueError, TypeError):
                x, y = 0, 0

        pin_num = pad.get('pin_number', '1')

        # Define through hole pad types (no paste layer)
        through_hole_types = ['PTH', 'NPTH', 'PTH_oblong', 'NPTH_oblong', 'PTH_rectangle']
        smd_types = ['square', 'rectangle', 'rounded_rectangle', 'round', 'SMD-oblong', 'D-shape', 'custom']

        # Draw paste layer (silver) - SKIP FOR THROUGH HOLE PADS
        if pad['type'] not in through_hole_types:
            # Check if paste is enabled for SMD pads
            paste_enabled = pad.get('paste_enabled', True)
            if paste_enabled:
                try:
                    paste_exp = to_decimal(pad.get('paste_expansion', 0))
                except (ValueError, TypeError):
                    paste_exp = 0
                    
                if paste_exp != 0:
                    painter.setPen(QPen(QColor("#C0C0C0"), 1/self.zoom_factor))
                    painter.setBrush(QBrush()) # No fill - outline only
                    self.draw_pad_shape(painter, pad, x, y, paste_exp)

        # Draw mask layer (purple #8A2BE2) - outline only
        mask_enabled = pad.get('mask_enabled', True)
        if mask_enabled:
            try:
                mask_exp = to_decimal(pad.get('mask_expansion', 0))
            except (ValueError, TypeError):
                mask_exp = 0
                
            if mask_exp != 0:
                painter.setPen(QPen(QColor("#8A2BE2"), 1/self.zoom_factor))
                painter.setBrush(QBrush()) # No fill - outline only
                self.draw_pad_shape(painter, pad, x, y, mask_exp)

        # Draw copper pad (red) - outline only
        pen_width = Decimal('2') / self.zoom_factor
        painter.setPen(QPen(QColor("#FF0000"), float(pen_width)))
        painter.setBrush(QBrush()) # No fill - outline only
        self.draw_pad_shape(painter, pad, x, y, 0)

        # Draw pin number with correct orientation
        self.draw_pin_number(painter, pad, x, y, pin_num)


    def draw_unique_padstack_names(self, painter):
        """Draw unique padstack names below the footprint (after courtyard)"""
        if not self.footprint_data.get('padstacks') and not self.footprint_data.get('fiducials_enabled', False):
            return

        # Collect unique pad names
        unique_names = []
        seen_names = set()
        
        # Regular pads
        for pad in self.footprint_data.get('padstacks', []):
            pad_name = self.generate_pad_name(pad)
            if pad_name not in seen_names:
                unique_names.append(pad_name)
                seen_names.add(pad_name)
        
        # Add fiducial padstack name if fiducials are enabled
        if self.footprint_data.get('fiducials_enabled', False):
            fiducial_settings = self.footprint_data.get('settings', {})
            fiducial_name = self.generate_fiducial_padstack_name(fiducial_settings)
            if fiducial_name not in seen_names:
                unique_names.append(fiducial_name)
                seen_names.add(fiducial_name)

        if not unique_names:
            return

        # Get text settings
        settings = self.footprint_data.get('text_settings', {})
        text_height = to_decimal(settings.get('text_height', '0.5'))

        # Calculate courtyard expansion
        noprobexp = to_decimal(self.footprint_data.get('noprob_expansion', '0.51'))
        coutyexp = to_decimal(self.footprint_data.get('courtyard_expansion', '0.51'))
        expansion = max(noprobexp, coutyexp)

        # SIMPLIFIED APPROACH: Find the lowest point of all elements
        lowest_y = Decimal('inf')
        text_center_x = Decimal('0')  # Default to origin

        # Check body bounds
        if all(k in self.footprint_data for k in ['body_length', 'body_width']):
            width = to_decimal(self.footprint_data['body_width'])
            length = to_decimal(self.footprint_data['body_length'])

            body_bottom = self.origin_offset_y - width
            lowest_y = min(lowest_y, body_bottom)

            # ✅ Calculate body center X
            text_center_x = self.origin_offset_x + (length/2) # assuming body is centered at origin offset

        # Check pad bounds
        pad_bounds = self.calculate_all_pads_bounds_absolute()
        if pad_bounds:
            pad_bottom = to_decimal(str(pad_bounds[1]))  # pad_bounds[1] is min_y
            lowest_y = min(lowest_y, pad_bottom)

        # If no bounds found, use default
        if lowest_y == Decimal('inf'):
            lowest_y = Decimal('-1.0')  # Default 1mm below origin

        # ✅ Final text start Y
        text_start_y = lowest_y - expansion - Decimal('0.5')


        # Draw each unique name in world coordinates
        painter.save()

        # Set text properties for world space drawing with zoom scaling
        painter.setPen(QPen(QColor("#FFAA00"), self.zoom_factor))  # Orange, scale with zoom

        for i, pad_name in enumerate(unique_names):
            # Simple linear text spacing
            text_y = text_start_y - (Decimal(str(i)) * (text_height + Decimal('0.2')))  # Stack vertically

            # Draw text in world coordinates at origin X (0)
            # Convert to screen coordinates for font sizing
            transform = painter.worldTransform()
            screen_pos = transform.map(QPointF(float(text_center_x), float(text_y)))


            # Switch to screen coordinates for text rendering
            painter.save()
            painter.resetTransform()

            # SIMPLIFIED: Linear zoom factor application
            font_size = float(text_height * to_decimal(str(self.zoom_factor)))
            font = QFont("Arial", int(font_size))
            font.setBold(True)
            painter.setFont(font)

            # Get text metrics
            fm = painter.fontMetrics()
            text_rect = fm.boundingRect(pad_name)
            text_rect.moveCenter(screen_pos.toPoint())

            # Draw text with zoom-aware pen width
            painter.setPen(QPen(QColor("#FFAA00"), max(1, int(Decimal('2')/to_decimal(str(self.zoom_factor))))))
            painter.setBrush(QBrush())
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, pad_name)

            painter.restore()

        painter.restore()

    def generate_fiducial_padstack_name(self, fiducial_settings):
        """Generate fiducial padstack name based on settings"""
        try:
            diameter = to_decimal(fiducial_settings.get('fiducial_diameter', '1.0'))
            mask_opening = to_decimal(fiducial_settings.get('fiducial_mask_opening', '2.0'))
            keepout_diameter = to_decimal(fiducial_settings.get('fiducial_keepout_diameter', '3.0'))
            
            # Create name based on dimensions (in 0.1mm units)
            name = f"FID_C{int(diameter * 100)}"
            
            if mask_opening > diameter:
                mask_size = int(mask_opening * 100)
                name += f"_M{mask_size}"
                
            if keepout_diameter > mask_opening:
                keepout_size = int(keepout_diameter * 100)
                name += f"_K{keepout_size}"
                
            return name
        except (ValueError, TypeError):
            return "FID_C100_M200_K300"  # Default fiducial name


    def draw_pin_number(self, painter, pad, x, y, pin_num):
        """Draw pin number in screen space with correct orientation and ultra-small size"""
        # Save current state
        painter.save()

        # Get current transform matrix
        transform = painter.worldTransform()

        # Map pad center to screen coordinates
        screen_pos = transform.map(QPointF(x, y))

        # Reset transform to draw in screen space (ensures upright text)
        painter.resetTransform()

        # Calculate font size based on pad size and zoom for ultra-small text
        pad_type = pad['type']
        try:
            if pad_type == 'square':
                pad_size = to_decimal(pad.get('size', 1))
                base_font_size = max(6, min(pad_size * self.zoom_factor * 0.12, 12))
            elif pad_type in ['rectangle', 'rounded_rectangle', 'SMD-oblong', 'PTH_rectangle']:
                min_dim = min(to_decimal(pad.get('length', 1)), to_decimal(pad.get('width', 1)))
                base_font_size = max(6, min(min_dim * self.zoom_factor * 0.1, 12))
            elif pad_type in ['round', 'D-shape']:
                diameter = to_decimal(pad.get('diameter', 1))
                base_font_size = max(6, min(diameter * self.zoom_factor * 0.12, 12))
            else:
                base_font_size = max(6, min(8, 12))
        except (ValueError, TypeError):
            base_font_size = 8

        # Set text properties for screen space
        painter.setPen(QPen(QColor("#FFFFFF"), 1))
        font = QFont("Arial", int(base_font_size))
        font.setBold(True) # Make bold for better visibility at small sizes
        painter.setFont(font)

        # Calculate text area based on font size
        text_width = base_font_size * 1.5
        text_height = base_font_size * 1.2

        # Draw text in screen coordinates (always upright)
        text_rect = QRectF(screen_pos.x() - text_width/2, screen_pos.y() - text_height/2,
                          text_width, text_height)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, pin_num)

        # Restore transform
        painter.restore()

    def draw_pad_shape(self, painter, pad, x, y, expansion):
        """Draw pad shape as outline only (no fill) - PRESERVES CALLER'S PEN COLOR"""
        pad_type = pad['type']

        # Ensure no fill - outline only
        painter.setBrush(QBrush())

        if pad_type == 'square':
            try:
                size = to_decimal(pad.get('size', 1)) + 2*expansion
                painter.drawRect(QRectF(x-size/2, y-size/2, size, size))
            except (ValueError, TypeError):
                painter.drawRect(QRectF(x-0.5, y-0.5, 1, 1))

        elif pad_type == 'rectangle':
            try:
                length = to_decimal(pad.get('length', 1)) + 2*expansion
                width = to_decimal(pad.get('width', 1)) + 2*expansion
                rotation = to_decimal(pad.get('rotation', 0)) if pad.get('rotation') else 0
            except (ValueError, TypeError):
                length, width, rotation = 1, 1, 0

            painter.save()
            if rotation != 0:
                painter.translate(x, y)
                painter.rotate(rotation)
                painter.translate(-x, -y)
            
            painter.drawRect(QRectF(x-length/2, y-width/2, length, width))
            painter.restore()

        elif pad_type == 'round':
            try:
                diameter = to_decimal(pad.get('diameter', 1)) + 2*expansion
                painter.drawEllipse(QRectF(x-diameter/2, y-diameter/2, diameter, diameter))
            except (ValueError, TypeError):
                painter.drawEllipse(QRectF(x-0.5, y-0.5, 1, 1))


        elif pad_type == 'SMD-oblong':
            try:
                length = to_decimal(pad.get('length', 1)) + 2*expansion
                width = to_decimal(pad.get('width', 1)) + 2*expansion
                rotation = to_decimal(pad.get('rotation', 0)) if pad.get('rotation') else 0
            except (ValueError, TypeError):
                length, width, rotation = 1, 1, 0
            
            painter.save()
            if rotation != 0:
                painter.translate(x, y)
                painter.rotate(rotation)
                painter.translate(-x, -y)
            
            radius = width / 2
            painter.drawRoundedRect(QRectF(x-length/2, y-width/2, length, width), radius, radius)
            painter.restore()

        elif pad_type == 'rounded_rectangle':
            try:
                length = to_decimal(pad.get('length', 1)) + 2*expansion
                width = to_decimal(pad.get('width', 1)) + 2*expansion
                radius = to_decimal(pad.get('corner_radius', 0.2))
                rotation = to_decimal(pad.get('rotation', 0)) if pad.get('rotation') else 0
            except (ValueError, TypeError):
                length, width, radius, rotation = 1, 1, 0.2, 0
            
            painter.save()
            if rotation != 0:
                painter.translate(x, y)
                painter.rotate(rotation)
                painter.translate(-x, -y)
            
            painter.drawRoundedRect(QRectF(x-length/2, y-width/2, length, width), radius, radius)
            painter.restore()


        elif pad_type == 'D-shape':
            # D-shape is rounded rectangle with one side corner radius
            try:
                length = to_decimal(pad.get('length', 1)) + 2*expansion
                width = to_decimal(pad.get('width', 1)) + 2*expansion
                corner_radius = to_decimal(pad.get('corner_radius', 0.2))
                rotation = to_decimal(pad.get('rotation', 0)) if pad.get('rotation') else 0
            except (ValueError, TypeError):
                length, width, corner_radius, rotation = 1, 1, 0.2, 0

            painter.save()
            if rotation != 0:
                painter.translate(x, y)
                painter.rotate(rotation)
                painter.translate(-x, -y)

            # Create D-shape path (rounded rectangle with rounded corners on one side)
            path = QPainterPath()
            half_length = length / 2
            half_width = width / 2
            r = corner_radius

            # Start from left-top corner
            path.moveTo(x - half_length, y - half_width)
            # Top line to rounded corner
            path.lineTo(x + half_length - r, y - half_width)
            # Top-right rounded corner
            path.quadTo(x + half_length, y - half_width, x + half_length, y - half_width + r)
            # Right side line
            path.lineTo(x + half_length, y + half_width - r)
            # Bottom-right rounded corner
            path.quadTo(x + half_length, y + half_width, x + half_length - r, y + half_width)
            # Bottom line
            path.lineTo(x - half_length, y + half_width)
            # Close path (left side straight)
            path.closeSubpath()

            painter.drawPath(path)
            painter.restore()

        elif pad_type in ['PTH', 'NPTH']:
            if expansion == 0: # Drawing the actual copper pad/hole
                # Save current pen color
                saved_pen = painter.pen()
                
                try:
                    hole_diameter = to_decimal(pad.get('hole_diameter', 0.8))
                except (ValueError, TypeError):
                    hole_diameter = 0.8
                    
                # Draw hole (black circle)
                painter.setPen(QPen(QColor("#FF6600"), 2/self.zoom_factor))
                painter.setBrush(QBrush(QColor("#000000")))
                painter.drawEllipse(QRectF(x-hole_diameter/2, y-hole_diameter/2, hole_diameter, hole_diameter))

                # Draw pad for PTH only
                if pad_type == 'PTH':
                    pen_width = Decimal('2') / self.zoom_factor
                    painter.setPen(QPen(QColor("#FF0000"), float(pen_width))) # Red for copper
                    painter.setBrush(QBrush()) # No fill for pad outline
                    try:
                        pad_diameter = to_decimal(pad.get('pad_diameter', 1.2))
                    except (ValueError, TypeError):
                        pad_diameter = 1.2
                    painter.drawEllipse(QRectF(x-pad_diameter/2, y-pad_diameter/2, pad_diameter, pad_diameter))

                # Restore original pen
                painter.setPen(saved_pen)
            else: # Drawing mask/paste expansion - PRESERVE CALLER'S PEN COLOR
                if pad_type == 'PTH':
                    try:
                        pad_diameter = to_decimal(pad.get('pad_diameter', 1.2)) + 2*expansion
                        painter.drawEllipse(QRectF(x-pad_diameter/2, y-pad_diameter/2, pad_diameter, pad_diameter))
                    except (ValueError, TypeError):
                        painter.drawEllipse(QRectF(x-0.6, y-0.6, 1.2, 1.2))
                else: # NPTH
                    try:
                        hole_diameter = to_decimal(pad.get('hole_diameter', 0.8)) + 2*expansion
                        painter.drawEllipse(QRectF(x-hole_diameter/2, y-hole_diameter/2, hole_diameter, hole_diameter))
                    except (ValueError, TypeError):
                        painter.drawEllipse(QRectF(x-0.4, y-0.4, 0.8, 0.8))

        elif pad_type == 'PTH_rectangle':
            # PTH_rectangle is like PTH_oblong but with sharp rectangular corners
            # Apply rotation if specified
            rotation = pad.get('rotation', 0)
            painter.save()
            
            # Convert rotation to to_decimal if it's a string
            try:
                rotation_value = to_decimal(rotation) if rotation else 0
            except (ValueError, TypeError):
                rotation_value = 0
            
            if rotation_value != 0:
                painter.translate(x, y)
                painter.rotate(rotation_value)
                painter.translate(-x, -y)
            
            if expansion == 0: # Drawing the actual copper pad/hole
                # Save current pen color
                saved_pen = painter.pen()
                
                try:
                    hole_length = to_decimal(pad.get('hole_length', 1.5))
                    hole_width = to_decimal(pad.get('hole_width', 0.8))
                except (ValueError, TypeError):
                    hole_length, hole_width = 1.5, 0.8
                    
                # Draw rectangular hole (black) - NO ROUNDING
                painter.setPen(QPen(QColor("#FF6600"), 2/self.zoom_factor))
                painter.setBrush(QBrush(QColor("#000000")))
                # Draw rectangle (not rounded rectangle)
                painter.drawRect(QRectF(x-hole_length/2, y-hole_width/2, hole_length, hole_width))

                # Draw rectangular pad (sharp corners)
                pen_width = Decimal('2') / self.zoom_factor
                painter.setPen(QPen(QColor("#FF0000"), float(pen_width))) # Red for copper
                painter.setBrush(QBrush()) # No fill for pad outline
                try:
                    pad_length = to_decimal(pad.get('pad_length', 2.0))
                    pad_width = to_decimal(pad.get('pad_width', 1.2))
                except (ValueError, TypeError):
                    pad_length, pad_width = 2.0, 1.2
                # Draw rectangle (not rounded rectangle)
                painter.drawRect(QRectF(x-pad_length/2, y-pad_width/2, pad_length, pad_width))

                # Restore original pen
                painter.setPen(saved_pen)
            else: # Drawing mask/paste expansion - PRESERVE CALLER'S PEN COLOR
                try:
                    pad_length = to_decimal(pad.get('pad_length', 2.0)) + 2*expansion
                    pad_width = to_decimal(pad.get('pad_width', 1.2)) + 2*expansion
                except (ValueError, TypeError):
                    pad_length, pad_width = 2.0, 1.2
                # Draw rectangle (not rounded rectangle)
                painter.drawRect(QRectF(x-pad_length/2, y-pad_width/2, pad_length, pad_width))
            
            painter.restore()

        elif pad_type in ['PTH_oblong', 'NPTH_oblong']:
            # Apply rotation if specified
            rotation = pad.get('rotation', 0)
            painter.save()
            
            # Convert rotation to to_decimal if it's a string
            try:
                rotation_value = to_decimal(rotation) if rotation else 0
            except (ValueError, TypeError):
                rotation_value = 0
            
            if rotation_value != 0:
                painter.translate(x, y)
                painter.rotate(rotation_value)
                painter.translate(-x, -y)
            
            if expansion == 0: # Drawing the actual copper pad/hole
                # Save current pen color
                saved_pen = painter.pen()
                
                try:
                    hole_length = to_decimal(pad.get('hole_length', 1.5))
                    hole_width = to_decimal(pad.get('hole_width', 0.8))
                except (ValueError, TypeError):
                    hole_length, hole_width = 1.5, 0.8
                    
                # Draw oblong hole (black)
                painter.setPen(QPen(QColor("#FF6600"), 2/self.zoom_factor))
                painter.setBrush(QBrush(QColor("#000000")))
                # Draw oblong as rounded rectangle
                radius = hole_width / 2
                painter.drawRoundedRect(QRectF(x-hole_length/2, y-hole_width/2, hole_length, hole_width), radius, radius)

                # Draw pad for PTH oblong only
                if pad_type == 'PTH_oblong':
                    pen_width = Decimal('2') / self.zoom_factor
                    painter.setPen(QPen(QColor("#FF0000"), float(pen_width))) # Red for copper
                    painter.setBrush(QBrush()) # No fill for pad outline
                    try:
                        pad_length = to_decimal(pad.get('pad_length', 2.0))
                        pad_width = to_decimal(pad.get('pad_width', 1.2))
                    except (ValueError, TypeError):
                        pad_length, pad_width = 2.0, 1.2
                    pad_radius = pad_width / 2
                    painter.drawRoundedRect(QRectF(x-pad_length/2, y-pad_width/2, pad_length, pad_width), pad_radius, pad_radius)

                # Restore original pen
                painter.setPen(saved_pen)
            else: # Drawing mask/paste expansion - PRESERVE CALLER'S PEN COLOR
                if pad_type == 'PTH_oblong':
                    try:
                        pad_length = to_decimal(pad.get('pad_length', 2.0)) + 2*expansion
                        pad_width = to_decimal(pad.get('pad_width', 1.2)) + 2*expansion
                    except (ValueError, TypeError):
                        pad_length, pad_width = 2.0, 1.2
                    pad_radius = pad_width / 2
                    painter.drawRoundedRect(QRectF(x-pad_length/2, y-pad_width/2, pad_length, pad_width), pad_radius, pad_radius)
                else: # NPTH_oblong
                    try:
                        hole_length = to_decimal(pad.get('hole_length', 1.5)) + 2*expansion
                        hole_width = to_decimal(pad.get('hole_width', 0.8)) + 2*expansion
                    except (ValueError, TypeError):
                        hole_length, hole_width = 1.5, 0.8
                    radius = hole_width / 2
                    painter.drawRoundedRect(QRectF(x-hole_length/2, y-hole_width/2, hole_length, hole_width), radius, radius)
            
            painter.restore()

        elif pad_type == 'PTH_rectangle':
            # PTH_rectangle is rectangular through-hole with rotation
            try:
                rotation = to_decimal(pad.get('rotation', 0)) if pad.get('rotation') else 0
            except (ValueError, TypeError):
                rotation = 0

            painter.save()
            if rotation != 0:
                painter.translate(x, y)
                painter.rotate(rotation)
                painter.translate(-x, -y)

            if expansion == 0: # Drawing the actual copper pad/hole
                # Save current pen color
                saved_pen = painter.pen()
                
                try:
                    hole_length = to_decimal(pad.get('hole_length', 1.5))
                    hole_width = to_decimal(pad.get('hole_width', 0.8))
                    pad_length = to_decimal(pad.get('pad_length', 2.0))
                    pad_width = to_decimal(pad.get('pad_width', 1.2))
                except (ValueError, TypeError):
                    hole_length, hole_width = 1.5, 0.8
                    pad_length, pad_width = 2.0, 1.2
                    
                # Draw rectangular hole (black)
                painter.setPen(QPen(QColor("#FF6600"), 2/self.zoom_factor))
                painter.setBrush(QBrush(QColor("#000000")))
                painter.drawRect(QRectF(x-hole_length/2, y-hole_width/2, hole_length, hole_width))

                # Draw rectangular pad (red outline)
                pen_width = Decimal('2') / self.zoom_factor
                painter.setPen(QPen(QColor("#FF0000"), float(pen_width)))
                painter.setBrush(QBrush()) # No fill for pad outline
                painter.drawRect(QRectF(x-pad_length/2, y-pad_width/2, pad_length, pad_width))

                # Restore original pen
                painter.setPen(saved_pen)
            else: # Drawing mask/paste expansion
                try:
                    pad_length = to_decimal(pad.get('pad_length', 2.0)) + 2*expansion
                    pad_width = to_decimal(pad.get('pad_width', 1.2)) + 2*expansion
                except (ValueError, TypeError):
                    pad_length, pad_width = 2.0, 1.2
                painter.drawRect(QRectF(x-pad_length/2, y-pad_width/2, pad_length, pad_width))
            
            painter.restore()


        elif pad_type == 'NPTH_rectangle':
            # NPTH_rectangle is rectangular non-plated through-hole with rotation
            try:
                rotation = to_decimal(pad.get('rotation', 0)) if pad.get('rotation') else 0
            except (ValueError, TypeError):
                rotation = 0

            painter.save()
            if rotation != 0:
                painter.translate(x, y)
                painter.rotate(rotation)
                painter.translate(-x, -y)

            if expansion == 0:  # Drawing the actual hole
                # Save current pen color
                saved_pen = painter.pen()

                try:
                    hole_length = to_decimal(pad.get('hole_length', 1.5))
                    hole_width = to_decimal(pad.get('hole_width', 0.8))
                except (ValueError, TypeError):
                    hole_length, hole_width = 1.5, 0.8

                # Draw rectangular hole (black) - NO ROUNDING
                painter.setPen(QPen(QColor("#FF6600"), 2/self.zoom_factor))
                painter.setBrush(QBrush(QColor("#000000")))
                # Draw rectangle (not rounded rectangle)
                painter.drawRect(QRectF(x-hole_length/2, y-hole_width/2, hole_length, hole_width))

                # Restore original pen
                painter.setPen(saved_pen)

            else:  # Drawing mask/paste expansion
                try:
                    hole_length = to_decimal(pad.get('hole_length', 1.5)) + 2*expansion
                    hole_width = to_decimal(pad.get('hole_width', 0.8)) + 2*expansion
                except (ValueError, TypeError):
                    hole_length, hole_width = 1.5, 0.8

                # Draw rectangle (not rounded rectangle)
                painter.drawRect(QRectF(x-hole_length/2, y-hole_width/2, hole_length, hole_width))

            painter.restore()


        elif pad_type == 'PTH_square':
            if expansion == 0:  # Drawing actual pad/hole
                saved_pen = painter.pen()
                try:
                    hole_diameter = to_decimal(pad.get('hole_diameter', 0.8))
                    pad_size = to_decimal(pad.get('pad_size', 1.5))
                except (ValueError, TypeError):
                    hole_diameter, pad_size = 0.8, 1.5
                
                # Draw hole (black circle)
                painter.setPen(QPen(QColor("#FF6600"), 2/self.zoom_factor))
                painter.setBrush(QBrush(QColor("#000000")))
                painter.drawEllipse(QRectF(x-hole_diameter/2, y-hole_diameter/2, hole_diameter, hole_diameter))
                
                # Draw square pad (red outline)
                painter.setPen(QPen(QColor("#FF0000"), 2/self.zoom_factor))
                painter.setBrush(QBrush())
                painter.drawRect(QRectF(x-pad_size/2, y-pad_size/2, pad_size, pad_size))
                
                painter.setPen(saved_pen)
            else:  # Drawing mask/paste expansion
                try:
                    pad_size = to_decimal(pad.get('pad_size', 1.5)) + 2*expansion
                    painter.drawRect(QRectF(x-pad_size/2, y-pad_size/2, pad_size, pad_size))
                except (ValueError, TypeError):
                    painter.drawRect(QRectF(x-0.75, y-0.75, 1.5, 1.5))

        elif pad_type == 'PTH_oblong_rect':
            rotation = pad.get('rotation', 0)
            painter.save()
            
            try:
                rotation_value = to_decimal(rotation) if rotation else 0
            except (ValueError, TypeError):
                rotation_value = 0
            
            if rotation_value != 0:
                painter.translate(x, y)
                painter.rotate(rotation_value)
                painter.translate(-x, -y)
            
            if expansion == 0:  # Drawing actual pad/hole
                saved_pen = painter.pen()
                try:
                    hole_length = to_decimal(pad.get('hole_length', 1.5))
                    hole_width = to_decimal(pad.get('hole_width', 0.8))
                    pad_length = to_decimal(pad.get('pad_length', 2.5))
                    pad_width = to_decimal(pad.get('pad_width', 1.5))
                except (ValueError, TypeError):
                    hole_length, hole_width = 1.5, 0.8
                    pad_length, pad_width = 2.5, 1.5
                
                # Draw oblong hole (black)
                painter.setPen(QPen(QColor("#FF6600"), 2/self.zoom_factor))
                painter.setBrush(QBrush(QColor("#000000")))
                radius = hole_width / 2
                painter.drawRoundedRect(QRectF(x-hole_length/2, y-hole_width/2, hole_length, hole_width), radius, radius)
                
                # Draw rectangular pad (red outline)
                painter.setPen(QPen(QColor("#FF0000"), 2/self.zoom_factor))
                painter.setBrush(QBrush())
                painter.drawRect(QRectF(x-pad_length/2, y-pad_width/2, pad_length, pad_width))
                
                painter.setPen(saved_pen)
            else:  # Drawing mask/paste expansion
                try:
                    pad_length = to_decimal(pad.get('pad_length', 2.5)) + 2*expansion
                    pad_width = to_decimal(pad.get('pad_width', 1.5)) + 2*expansion
                    painter.drawRect(QRectF(x-pad_length/2, y-pad_width/2, pad_length, pad_width))
                except (ValueError, TypeError):
                    painter.drawRect(QRectF(x-1.25, y-0.75, 2.5, 1.5))
            
            painter.restore()


        elif pad_type == 'custom':
            # Draw custom polygon using absolute position
            polygon_points = self.calculate_polygon_points_absolute(pad, x, y)
            if polygon_points:
                # Apply expansion to polygon - FIXED VERSION
                if expansion != 0:
                    # Calculate proper uniform expansion using offset algorithm
                    expanded_points = self.expand_polygon_uniformly(polygon_points, expansion)
                    polygon_points = expanded_points if expanded_points else polygon_points

                polygon = QPolygonF(polygon_points)
                painter.drawPolygon(polygon)
        # Draw custom polygon using absolute position   

    def expand_polygon_uniformly(self, points, expansion):
        """Expand polygon by moving each edge outward by the expansion amount"""
        if not points or len(points) < 3 or expansion == 0:
            return points

        try:
            # Convert expansion to float for all mathematical operations
            expansion_float = float(expansion)
            
            expanded_points = []
            n = len(points)
            
            for i in range(n):
                # Get current vertex and adjacent vertices
                prev_i = (i - 1) % n
                next_i = (i + 1) % n
                
                curr = points[i]
                prev = points[prev_i]
                next = points[next_i]

                # Calculate edge vectors (using float operations)
                edge1 = QPointF(curr.x() - prev.x(), curr.y() - prev.y())  # incoming edge
                edge2 = QPointF(next.x() - curr.x(), next.y() - curr.y())  # outgoing edge

                # Calculate outward normals for each edge (rotate 90Â° clockwise)
                normal1 = QPointF(edge1.y(), -edge1.x())
                normal2 = QPointF(edge2.y(), -edge2.x())

                # Normalize the normals
                len1 = math.sqrt(normal1.x()**2 + normal1.y()**2)
                len2 = math.sqrt(normal2.x()**2 + normal2.y()**2)
                
                if len1 > 0:
                    normal1 = QPointF(normal1.x() / len1, normal1.y() / len1)
                if len2 > 0:
                    normal2 = QPointF(normal2.x() / len2, normal2.y() / len2)

                # Average the normals to get the direction to move this vertex
                avg_normal = QPointF(
                    (normal1.x() + normal2.x()) / 2,
                    (normal1.y() + normal2.y()) / 2
                )

                # Normalize the average normal
                avg_len = math.sqrt(avg_normal.x()**2 + avg_normal.y()**2)
                if avg_len > 0:
                    avg_normal = QPointF(avg_normal.x() / avg_len, avg_normal.y() / avg_len)

                # Calculate the actual expansion distance
                # For sharp corners, we need to expand more to maintain edge offset
                dot_product = normal1.x() * normal2.x() + normal1.y() * normal2.y()
                
                # Clamp dot product to avoid floating point errors
                dot_product = max(min(dot_product, 1.0), -1.0)
                
                # Calculate the angle between normals
                try:
                    angle = math.acos(abs(dot_product))  # Use abs to avoid negative values
                    sin_half_angle = math.sin(angle / 2)
                except (ValueError, ZeroDivisionError):
                    sin_half_angle = 0.5  # Fallback value
                
                # Avoid division by zero for straight lines
                expansion_factor = 1.0 / sin_half_angle if sin_half_angle > 0.01 else 1.0
                
                # Limit extreme expansions for very sharp angles
                expansion_factor = min(expansion_factor, 10.0)

                # Move the vertex outward - ALL FLOAT OPERATIONS NOW
                offset_distance = -expansion_float * expansion_factor  # Negative for outward expansion

                new_point = QPointF(
                    curr.x() + avg_normal.x() * offset_distance,
                    curr.y() + avg_normal.y() * offset_distance
                )

                expanded_points.append(new_point)

            return expanded_points

        except Exception as e:
            print(f"Polygon expansion error: {e}")
            return points  # Return original points on error


    def draw_custom_layers(self, painter):
        """Draw custom layers (mask, paste, keepout)"""
        custom_layers = self.footprint_data.get('custom_layers', [])
        
        for layer in custom_layers:
            layer_type = layer.get('layer', 'mask')
            shape = layer.get('shape', 'rectangle')
            
            # Get position
            try:
                x_offset = to_decimal(layer.get('x_offset', 0))
                y_offset = to_decimal(layer.get('y_offset', 0))
            except (ValueError, TypeError):
                x_offset, y_offset = 0, 0
                
            # Handle offset_from
            offset_from = layer.get('offset_from', 'origin')
            if offset_from != 'origin':
                # Get reference pad position
                absolute_positions = self.calculate_pad_absolute_positions()
                pads = self.footprint_data.get('padstacks', [])
                ref_pad = None
                for i, pad in enumerate(pads):
                    if pad.get('pin_number') == offset_from:
                        if i in absolute_positions:
                            ref_x, ref_y = absolute_positions[i]
                            x_offset += ref_x
                            y_offset += ref_y
                        break
            
            # Set color based on layer type
            if layer_type == 'mask':
                painter.setPen(QPen(QColor("#8A2BE2"), 2/self.zoom_factor))  # Purple
            elif layer_type == 'paste':
                painter.setPen(QPen(QColor("#C0C0C0"), 2/self.zoom_factor))  # Silver
            elif layer_type == 'keepout':
                painter.setPen(QPen(QColor("#FF4500"), 2/self.zoom_factor))  # Orange Red
            
            painter.setBrush(QBrush())  # No fill
            
            # Draw shape
            if shape == 'rectangle':
                try:
                    length = to_decimal(layer.get('length', 1))
                    width = to_decimal(layer.get('width', 1))
                    painter.drawRect(QRectF(x_offset - length/2, y_offset - width/2, length, width))
                except (ValueError, TypeError):
                    painter.drawRect(QRectF(x_offset - 0.5, y_offset - 0.5, 1, 1))
                    
            elif shape == 'rounded_rectangle':
                try:
                    length = to_decimal(layer.get('length', 1))
                    width = to_decimal(layer.get('width', 1))
                    radius = to_decimal(layer.get('corner_radius', 0.2))
                    painter.drawRoundedRect(QRectF(x_offset - length/2, y_offset - width/2, length, width), radius, radius)
                except (ValueError, TypeError):
                    painter.drawRoundedRect(QRectF(x_offset - 0.5, y_offset - 0.5, 1, 1), 0.2, 0.2)
                    
            elif shape == 'oblong':
                try:
                    length = to_decimal(layer.get('length', 2))
                    width = to_decimal(layer.get('width', 1))
                    rotation = to_decimal(layer.get('rotation', 0))
                    
                    # APPLY ROTATION FOR OBLONG
                    painter.save()
                    if rotation != 0:
                        painter.translate(x_offset, y_offset)
                        painter.rotate(rotation)
                        painter.translate(-x_offset, -y_offset)
                    
                    radius = width / 2
                    painter.drawRoundedRect(QRectF(x_offset - length/2, y_offset - width/2, length, width), radius, radius)
                    painter.restore()
                    
                except (ValueError, TypeError):
                    painter.drawRoundedRect(QRectF(x_offset - 1, y_offset - 0.5, 2, 1), 0.5, 0.5)
                    
            elif shape == 'custom_polygon':
                # Handle custom polygon similar to pad custom polygons
                polygon_points = self.calculate_custom_layer_polygon_points(layer, x_offset, y_offset)
                if polygon_points:
                    polygon = QPolygonF(polygon_points)
                    painter.drawPolygon(polygon)

    def draw_thermal_vias(self, painter):
        """Draw thermal vias"""
        thermal_vias = self.footprint_data.get('thermal_vias', [])
        
        for via in thermal_vias:
            via_type = via.get('type', 'single')
            
            # Get position
            try:
                x_offset = to_decimal(via.get('x_offset', 0))
                y_offset = to_decimal(via.get('y_offset', 0))
            except (ValueError, TypeError):
                x_offset, y_offset = 0, 0
                
            # Handle offset_from - UPDATED TO INCLUDE THERMAL VIA PINS
            offset_from = via.get('offset_from', 'origin')
            if offset_from != 'origin':
                # First check pad positions
                absolute_positions = self.calculate_pad_absolute_positions()
                pads = self.footprint_data.get('padstacks', [])
                found_reference = False
                
                # Check pad pins first
                for i, pad in enumerate(pads):
                    if pad.get('pin_number') == offset_from:
                        if i in absolute_positions:
                            ref_x, ref_y = absolute_positions[i]
                            x_offset += ref_x
                            y_offset += ref_y
                            found_reference = True
                            break
                
                # If not found in pads, check thermal via pins
                if not found_reference:
                    thermal_vias_list = self.footprint_data.get('thermal_vias', [])
                    for other_via in thermal_vias_list:
                        if other_via.get('pin_number') == offset_from and other_via != via:
                            # Calculate position of the reference thermal via
                            try:
                                ref_x_offset = to_decimal(other_via.get('x_offset', 0))
                                ref_y_offset = to_decimal(other_via.get('y_offset', 0))
                            except (ValueError, TypeError):
                                ref_x_offset, ref_y_offset = 0, 0
                            
                            # Handle recursive offset_from for the reference via
                            ref_offset_from = other_via.get('offset_from', 'origin')
                            if ref_offset_from != 'origin':
                                # Recursively resolve reference via position
                                # Check pads for the reference via's offset
                                for j, ref_pad in enumerate(pads):
                                    if ref_pad.get('pin_number') == ref_offset_from:
                                        if j in absolute_positions:
                                            ref_pad_x, ref_pad_y = absolute_positions[j]
                                            ref_x_offset += ref_pad_x
                                            ref_y_offset += ref_pad_y
                                            break
                            
                            x_offset += ref_x_offset
                            y_offset += ref_y_offset
                            found_reference = True
                            break
            
            # Set via appearance
            painter.setPen(QPen(QColor("#00CED1"), 2/self.zoom_factor)) # Dark Turquoise for via
            painter.setBrush(QBrush(QColor("#008B8B"))) # Dark Cyan fill
            
            # Rest of the drawing code remains the same...
            if via_type == 'single':
                try:
                    via_diameter = to_decimal(via.get('via_diameter', 0.2))
                    drill_diameter = to_decimal(via.get('drill_diameter', 0.1))
                except (ValueError, TypeError):
                    via_diameter, drill_diameter = 0.2, 0.1
                    
                # Draw via pad
                painter.drawEllipse(QRectF(x_offset - via_diameter/2, y_offset - via_diameter/2,
                                        via_diameter, via_diameter))
                
                # Draw drill hole (black)
                painter.setPen(QPen(QColor("#000000"), 1/self.zoom_factor))
                painter.setBrush(QBrush(QColor("#000000")))
                painter.drawEllipse(QRectF(x_offset - drill_diameter/2, y_offset - drill_diameter/2,
                                        drill_diameter, drill_diameter))
                                        
            elif via_type == 'grid_array':
                try:
                    rows = int(via.get('rows', 2))
                    columns = int(via.get('columns', 2))
                    row_spacing = to_decimal(via.get('row_spacing', 1.0))
                    col_spacing = to_decimal(via.get('col_spacing', 1.0))
                    via_diameter = to_decimal(via.get('via_diameter', 0.2))
                    drill_diameter = to_decimal(via.get('drill_diameter', 0.1))
                except (ValueError, TypeError):
                    rows, columns = 2, 2
                    row_spacing, col_spacing = 1.0, 1.0
                    via_diameter, drill_diameter = 0.2, 0.1
                
                # Calculate grid starting position (centered)
                start_x = x_offset - (columns - 1) * col_spacing / 2
                start_y = y_offset - (rows - 1) * row_spacing / 2
                
                for row in range(rows):
                    for col in range(columns):
                        via_x = start_x + col * col_spacing
                        via_y = start_y + row * row_spacing
                        
                        # Draw via pad
                        painter.setPen(QPen(QColor("#00CED1"), 2/self.zoom_factor))
                        painter.setBrush(QBrush(QColor("#008B8B")))
                        painter.drawEllipse(QRectF(via_x - via_diameter/2, via_y - via_diameter/2,
                                                via_diameter, via_diameter))
                        
                        # Draw drill hole
                        painter.setPen(QPen(QColor("#000000"), 1/self.zoom_factor))
                        painter.setBrush(QBrush(QColor("#000000")))
                        painter.drawEllipse(QRectF(via_x - drill_diameter/2, via_y - drill_diameter/2,
                                                drill_diameter, drill_diameter))

    def calculate_custom_layer_polygon_points(self, layer, abs_x, abs_y):
        """Calculate polygon points for custom layer shapes"""
        polygon_data = layer.get('polygon_data', {})
        lines_data = polygon_data.get('lines', [])
        
        if not lines_data:
            return []

        # Similar to pad polygon calculation
        raw_points = []
        current_x = abs_x
        current_y = abs_y
        raw_points.append((current_x, current_y))

        for line_data in lines_data:
            try:
                line_size = to_decimal(line_data.get('line_size', 1.0))
            except (ValueError, TypeError):
                line_size = 1.0

            direction = line_data.get('direction', 'right')

            if direction == 'right':
                current_x += line_size
            elif direction == 'down':
                current_y -= line_size
            elif direction == 'left':
                current_x -= line_size
            elif direction == 'up':
                current_y += line_size

            raw_points.append((current_x, current_y))

        # Convert to QPointF and handle corners (similar to pad polygons)
        final_points = []
        final_points.append(QPointF(raw_points[0][0], raw_points[0][1]))
        
        for i in range(1, len(raw_points) - 1):
            prev_point = raw_points[i-1]
            curr_point = raw_points[i]
            next_point = raw_points[i+1]
            
            if i-1 < len(lines_data):
                line_data = lines_data[i-1]
                corner_type = line_data.get('corner_type', '90-degree')
                try:
                    corner_size = to_decimal(line_data.get('corner_size', 0))
                except (ValueError, TypeError):
                    corner_size = 0

                if corner_type == '90-degree' or corner_size == 0:
                    final_points.append(QPointF(curr_point[0], curr_point[1]))
                elif corner_type == 'chamfer':
                    chamfer_points = self.calculate_chamfer_points(
                        QPointF(prev_point[0], prev_point[1]),
                        QPointF(curr_point[0], curr_point[1]),
                        QPointF(next_point[0], next_point[1]),
                        corner_size
                    )
                    final_points.extend(chamfer_points)
                elif corner_type == 'fillet':
                    fillet_points = self.calculate_fillet_points(
                        QPointF(prev_point[0], prev_point[1]),
                        QPointF(curr_point[0], curr_point[1]),
                        QPointF(next_point[0], next_point[1]),
                        corner_size
                    )
                    final_points.extend(fillet_points)
            else:
                final_points.append(QPointF(curr_point[0], curr_point[1]))
        
        if len(raw_points) > 1:
            final_points.append(QPointF(raw_points[-1][0], raw_points[-1][1]))

        return final_points


    def draw_origin(self, painter):
        """Draw origin crosshair"""
        # Draw origin crosshair
        painter.setPen(QPen(QColor("#FFFF00"), 2/float(self.zoom_factor))) # Yellow crosshair

        # Crosshair size
        cross_size = Decimal('10') / self.zoom_factor

        # Horizontal line
        painter.drawLine(QPointF(-cross_size, 0), QPointF(cross_size, 0))

        # Vertical line
        painter.drawLine(QPointF(0, -cross_size), QPointF(0, cross_size))

        # Origin circle
        painter.setPen(QPen(QColor("#FFFF00"), 1/self.zoom_factor))
        painter.setBrush(QBrush()) # No fill
        painter.drawEllipse(QPointF(0, 0), 3/self.zoom_factor, 3/self.zoom_factor)

    def wheelEvent(self, event):
        """Handle mouse wheel events with cursor-centered zoom - FIXED VERSION"""
        zoom_in_factor = Decimal('1.2')
        zoom_out_factor = Decimal('1') / zoom_in_factor

        # Get mouse position - convert to Decimal
        mouse_pos = event.position()
        mouse_x = to_decimal(str(mouse_pos.x()))
        mouse_y = to_decimal(str(mouse_pos.y()))

        # Store old zoom factor
        old_zoom = self.zoom_factor

        # Determine zoom direction
        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor

        # Update zoom factor with limits
        new_zoom = self.zoom_factor * zoom_factor
        new_zoom = max(Decimal('0.1'), min(new_zoom, Decimal('1000')))  # Clamp zoom
        self.zoom_factor = new_zoom

        # Calculate widget center - convert to Decimal
        center_x = to_decimal(str(self.width())) / Decimal('2')
        center_y = to_decimal(str(self.height())) / Decimal('2')

        # Mouse position relative to center (in widget coordinates)
        mouse_rel_x = mouse_x - center_x
        mouse_rel_y = mouse_y - center_y

        # Calculate scene coordinates more accurately
        # Convert mouse position to scene coordinates BEFORE zoom change
        scene_x = (mouse_rel_x - self.offset_x) / old_zoom
        scene_y = (mouse_rel_y - self.offset_y) / (-old_zoom)  # Note: negative for Y-flip

        # Calculate new offsets to keep the scene point under the mouse
        self.offset_x = mouse_rel_x - scene_x * self.zoom_factor
        self.offset_y = mouse_rel_y - scene_y * (-self.zoom_factor)  # Note: negative for Y-flip

        # Disable auto fit when manually zooming
        self.auto_fit = False
        self.update()

    def to_decimal_coordinate(self, value):
        """Convert coordinate value to Decimal safely"""
        try:
            return to_decimal(str(value))
        except (ValueError, TypeError):
            return Decimal('0')



    def calculate_all_pad_pitches(self):
        """Calculate center-to-center pitch distances between all pad pairs"""
        pads = self.footprint_data.get('padstacks', [])
        if len(pads) < 2:
            return []
        
        pitches = []
        positions = self.calculate_pad_absolute_positions()
        
        # Calculate pitches between all pad pairs
        for i in range(len(pads)):
            for j in range(i + 1, len(pads)):
                if i not in positions or j not in positions:
                    continue
                    
                x1, y1 = positions[i]
                x2, y2 = positions[j]
                
                dx = abs(x2 - x1)
                dy = abs(y2 - y1)
                
                # Add horizontal pitch if significant
                if dx > 0.01:  # Minimum threshold to avoid noise
                    pitches.append({
                        'pad_pair': (i, j),
                        'direction': 'horizontal',
                        'pitch': dx,
                        'start_pos': QPointF(min(x1, x2), (y1 + y2) / 2),
                        'end_pos': QPointF(max(x1, x2), (y1 + y2) / 2)
                    })
                
                # Add vertical pitch if significant  
                if dy > 0.01:
                    pitches.append({
                        'pad_pair': (i, j),
                        'direction': 'vertical', 
                        'pitch': dy,
                        'start_pos': QPointF((x1 + x2) / 2, min(y1, y2)),
                        'end_pos': QPointF((x1 + x2) / 2, max(y1, y2))
                    })
        
        return pitches


    def calculate_min_pad_to_pad_airgap(self):
        """Calculate minimum edge-to-edge distance between all pads"""
        pad_bounds_list = self.get_individual_pad_bounds_absolute()
        if len(pad_bounds_list) < 2:
            return None, None

        min_gap = to_decimal('inf')
        closest_pads = None

        for i in range(len(pad_bounds_list)):
            for j in range(i + 1, len(pad_bounds_list)):
                # Unpack bounds
                x1_min, y1_min, x1_max, y1_max = pad_bounds_list[i]
                x2_min, y2_min, x2_max, y2_max = pad_bounds_list[j]

                # Horizontal gap
                if x1_max < x2_min:  # b1 right edge < b2 left edge
                    x_gap = x2_min - x1_max
                elif x2_max < x1_min:  # b2 right edge < b1 left edge
                    x_gap = x1_min - x2_max
                else:
                    x_gap = 0  # Overlapping in X

                # Vertical gap
                if y1_max < y2_min:  # b1 top edge < b2 bottom edge
                    y_gap = y2_min - y1_max
                elif y2_max < y1_min:  # b2 top edge < b1 bottom edge
                    y_gap = y1_min - y2_max
                else:
                    y_gap = 0  # Overlapping in Y

                # Actual distance
                if x_gap == 0 and y_gap == 0:
                    dist = 0  # Overlapping pads
                elif x_gap == 0:
                    dist = y_gap  # Vertically separated
                elif y_gap == 0:
                    dist = x_gap  # Horizontally separated
                else:
                    dist = math.sqrt(x_gap**2 + y_gap**2)  # Corner-to-corner

                if dist < min_gap:
                    min_gap = dist
                    closest_pads = (i, j, x_gap, y_gap)

        return (min_gap if min_gap != to_decimal('inf') else None), closest_pads

    def calculate_all_pad_airgaps(self):
        """Calculate only X and Y edge-to-edge pad clearances."""
        pad_bounds_list = self.get_individual_pad_bounds_absolute()
        if len(pad_bounds_list) < 2:
            return []
        
        airgaps = []
        
        for i in range(len(pad_bounds_list)):
            for j in range(i + 1, len(pad_bounds_list)):
                b1 = pad_bounds_list[i]  # [min_x, min_y, max_x, max_y]
                b2 = pad_bounds_list[j]

                h_start = h_end = v_start = v_end = None
                x_gap = y_gap = 0

                # --- Horizontal gap (edge-to-edge) ---
                if b1[2] < b2[0]:  # pad1 right to pad2 left
                    x_gap = b2[0] - b1[2]
                    h_start = QPointF(b1[2], (b1[1] + b1[3]) / 2)
                    h_end   = QPointF(b2[0], (b2[1] + b2[3]) / 2)
                elif b2[2] < b1[0]:  # pad2 right to pad1 left
                    x_gap = b1[0] - b2[2]
                    h_start = QPointF(b2[2], (b2[1] + b2[3]) / 2)
                    h_end   = QPointF(b1[0], (b1[1] + b1[3]) / 2)

                # --- Vertical gap (edge-to-edge) ---
                if b1[3] < b2[1]:  # pad1 top to pad2 bottom
                    y_gap = b2[1] - b1[3]
                    v_start = QPointF((b1[0] + b1[2]) / 2, b1[3])
                    v_end   = QPointF((b2[0] + b2[2]) / 2, b2[1])
                elif b2[3] < b1[1]:  # pad2 top to pad1 bottom
                    y_gap = b1[1] - b2[3]
                    v_start = QPointF((b2[0] + b2[2]) / 2, b2[3])
                    v_end   = QPointF((b1[0] + b1[2]) / 2, b1[1])

                airgaps.append({
                    'pads': (i, j),
                    'x_gap': x_gap,
                    'y_gap': y_gap,
                    'h_line': (h_start, h_end) if h_start and h_end else None,
                    'v_line': (v_start, v_end) if v_start and v_end else None,
                })
        
        return airgaps


    def draw_dimension_line_with_label(self, painter, start_point, end_point, value_mm, label_prefix, color, label_offset=QPointF(0,0)):
        """Draw a dimension line with colored 'pill' label in mm with optional offset."""
        if not start_point or not end_point or value_mm <= 0:
            return

        # 1) Dimension line - FIX: Convert zoom_factor to float for division
        painter.setPen(QPen(color, 1.5/float(self.zoom_factor)))
        painter.drawLine(start_point, end_point)

        # 2) End ticks - FIX: Convert zoom_factor to float for division
        ext = 3/float(self.zoom_factor)
        v = QPointF(end_point.x() - start_point.x(), end_point.y() - start_point.y())
        L = math.hypot(v.x(), v.y())
        if L > 0:
            n = QPointF(v.x()/L, v.y()/L)
            p = QPointF(-n.y(), n.x())
            painter.drawLine(QPointF(start_point.x()+p.x()*ext, start_point.y()+p.y()*ext),
                            QPointF(start_point.x()-p.x()*ext, start_point.y()-p.y()*ext))
            painter.drawLine(QPointF(end_point.x()+p.x()*ext, end_point.y()+p.y()*ext),
                            QPointF(end_point.x()-p.x()*ext, end_point.y()-p.y()*ext))

        # 3) Label (world midpoint -> screen) with offset
        mid = QPointF((start_point.x()+end_point.x())/2, (start_point.y()+end_point.y())/2)
        screen_mid = painter.worldTransform().map(mid)

        # Apply offset to prevent label overlap
        screen_mid += label_offset

        label_text = f"{label_prefix}:{value_mm}mm"

        painter.save()
        painter.resetTransform()

        font = QFont("Arial", 9)
        font.setBold(True)
        painter.setFont(font)

        fm = painter.fontMetrics()
        rect = fm.boundingRect(label_text)
        rect.moveCenter(screen_mid.toPoint())
        rect.adjust(-4, -2, 4, 2)

        bg = QColor(color)
        bg.setAlpha(200)
        painter.setPen(QPen(QColor("#000000"), 1))
        painter.setBrush(QBrush(bg))
        painter.drawRoundedRect(rect, 4, 4)

        painter.setPen(QPen(QColor("#000000"), 1))
        painter.setBrush(QBrush())
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label_text)

        painter.restore()

    def draw_all_airgap_dimensions(self, painter):
        """Draw air gap dimensions only between selected pads (if exactly 2 selected)"""
        if len(self.selected_pads) != 2:
            return

        pad_indices = list(self.selected_pads)
        i, j = pad_indices[0], pad_indices[1]

        pad_bounds_list = self.get_individual_pad_bounds_absolute()
        if i >= len(pad_bounds_list) or j >= len(pad_bounds_list):
            return

        b1 = pad_bounds_list[i]  # (x_min, y_min, x_max, y_max)
        b2 = pad_bounds_list[j]

        # Calculate horizontal gap (X)
        h_start = h_end = None
        x_gap = 0

        if b1[2] < b2[0]:  # pad1 right edge < pad2 left edge
            x_gap = b2[0] - b1[2]
            h_start = QPointF(b1[2], (b1[1] + b1[3]) / 2)
            h_end   = QPointF(b2[0], (b2[1] + b2[3]) / 2)

        elif b2[2] < b1[0]:  # pad2 right edge < pad1 left edge
            x_gap = b1[0] - b2[2]
            h_start = QPointF(b2[2], (b2[1] + b2[3]) / 2)
            h_end   = QPointF(b1[0], (b1[1] + b1[3]) / 2)

        # Calculate vertical gap (Y)
        v_start = v_end = None
        y_gap = 0

        if b1[3] < b2[1]:  # pad1 top < pad2 bottom
            y_gap = b2[1] - b1[3]
            v_start = QPointF((b1[0] + b1[2]) / 2, b1[3])
            v_end   = QPointF((b2[0] + b2[2]) / 2, b2[1])

        elif b2[3] < b1[1]:  # pad2 top < pad1 bottom
            y_gap = b1[1] - b2[3]
            v_start = QPointF((b2[0] + b2[2]) / 2, b2[3])
            v_end   = QPointF((b1[0] + b1[2]) / 2, b1[1])

        # Draw dimension lines
        if h_start and h_end and x_gap > 0:
            label_offset = QPointF(0, -15)
            self.draw_dimension_line_with_label(
                painter, h_start, h_end, x_gap, "X Gap", QColor("#00FFFF"), label_offset
            )

        if v_start and v_end and y_gap > 0:
            label_offset = QPointF(15, 0)
            self.draw_dimension_line_with_label(
                painter, v_start, v_end, y_gap, "Y Gap", QColor("#FFFF00"), label_offset
            )

    def draw_all_pitch_dimensions(self, painter):
        """Draw pitch dimensions only between selected pads (if exactly 2 selected)"""
        if len(self.selected_pads) != 2:
            return
        
        pad_indices = list(self.selected_pads)
        i, j = pad_indices[0], pad_indices[1]
        
        positions = self.calculate_pad_absolute_positions()
        if i not in positions or j not in positions:
            return
        
        x1, y1 = positions[i]
        x2, y2 = positions[j]
        
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        
        # Draw horizontal pitch if significant
        if dx > 0.01:
            start = QPointF(min(x1, x2), (y1 + y2) / 2)
            end = QPointF(max(x1, x2), (y1 + y2) / 2)
            label_offset = QPointF(0, -25)  # Offset to avoid overlap
            self.draw_dimension_line_with_label(
                painter, start, end, dx, "Pitch X", QColor("#FFA500"), label_offset
            )
        
        # Draw vertical pitch if significant
        if dy > 0.01:
            start = QPointF((x1 + x2) / 2, min(y1, y2))
            end = QPointF((x1 + x2) / 2, max(y1, y2))
            label_offset = QPointF(25, 0)  # Offset to avoid overlap
            self.draw_dimension_line_with_label(
                painter, start, end, dy, "Pitch Y", QColor("#FFA500"), label_offset
            )


    def draw_minimum_airgap_summary(self, painter):
        """Draw minimum airgap summary in top-left corner"""
        airgaps = self.calculate_all_pad_airgaps()
        if not airgaps:
            return
        
        # Find minimum values
        min_x = min((a['x_gap'] for a in airgaps if a['x_gap'] > 0), default=None)
        min_y = min((a['y_gap'] for a in airgaps if a['y_gap'] > 0), default=None)
        min_overall = min((min(a['x_gap'], a['y_gap']) for a in airgaps 
                        if a['x_gap'] > 0 or a['y_gap'] > 0), default=None)
        
        if min_overall is None:
            return
        
        painter.save()
        painter.resetTransform()
        
        # Create summary text
        summary_lines = []
        if min_overall is not None:
            summary_lines.append(f"Min Airgap: {min_overall:.3f}mm")
        if min_x is not None:
            summary_lines.append(f"Min X Gap: {min_x:.3f}mm")
        if min_y is not None:
            summary_lines.append(f"Min Y Gap: {min_y:.3f}mm")
        
        # Set font
        font = QFont("Arial", 10)
        font.setBold(True)
        painter.setFont(font)
        
        # Calculate text area
        fm = painter.fontMetrics()
        max_width = max(fm.horizontalAdvance(line) for line in summary_lines)
        line_height = fm.height()
        total_height = len(summary_lines) * line_height + 10
        
        # Draw background
        bg_rect = QRectF(10, 10, max_width + 20, total_height)
        painter.setPen(QPen(QColor("#000000"), 1))
        painter.setBrush(QBrush(QColor("#000000", 180)))
        painter.drawRect(bg_rect)
        
        # Draw text lines
        y_offset = 10
        painter.setPen(QPen(QColor("#00FF00"), 1))
        for line in summary_lines:
            painter.drawText(20, y_offset + line_height, line)
            y_offset += line_height
        
        painter.restore()

    def draw_selection_instructions(self, painter):
        """Draw instruction text for pad selection"""
        painter.save()
        painter.resetTransform()  # Switch to screen coordinates
        
        instructions = []
        
        if self.show_airgap_checkbox.isChecked() or self.show_pitch_checkbox.isChecked():
            if len(self.selected_pads) == 0:
                instructions.append("Click on 2 pads to measure dimensions")
            elif len(self.selected_pads) == 1:
                instructions.append("Click on 1 more pad to measure")
            elif len(self.selected_pads) == 2:
                instructions.append("Dimensions shown between selected pads")
                instructions.append("Click elsewhere to clear selection")
        
        if instructions:
            # Position at bottom-left
            y_start = self.height() - 60
            
            painter.setPen(QPen(QColor("#FFFFFF"), 1))
            font = QFont("Arial", 10)
            painter.setFont(font)
            
            for i, instruction in enumerate(instructions):
                # Draw background for better visibility
                text_rect = painter.fontMetrics().boundingRect(instruction)
                text_rect.moveTo(10, y_start + i * 20)
                text_rect.adjust(-3, -1, 3, 1)
                
                painter.setBrush(QBrush(QColor(0, 0, 0, 150)))
                painter.drawRect(text_rect)
                
                painter.setBrush(QBrush())
                painter.drawText(10, y_start + i * 20 + 15, instruction)
        
        painter.restore()



    def draw_pad_airgap_dimension(self, painter):
        """Draw pad-to-pad airgap dimension in screen space"""
        min_airgap, closest_pads = self.calculate_min_pad_to_pad_airgap()
        if min_airgap is None:
            return
        
        # Draw airgap text in screen space
        painter.save()
        painter.resetTransform()  # Switch to screen coordinates
        
        # Set text properties
        painter.setPen(QPen(QColor("#00FF00"), 2))  # Bright green
        font = QFont("Arial", 12)
        font.setBold(True)
        painter.setFont(font)
        
        # Format the airgap value
        airgap_text = f"Min Pad-to-Pad Airgap: {min_airgap:.3f} mm"
        
        # Draw text with background for better visibility
        text_rect = painter.fontMetrics().boundingRect(airgap_text)
        text_rect.adjust(-5, -2, 5, 2)
        text_rect.moveTo(10, 10)
        
        # Draw background rectangle
        painter.setPen(QPen(QColor("#000000"), 1))
        color = QColor("#000000")
        color.setAlpha(180)
        painter.setBrush(QBrush(color))
 # Semi-transparent black
        painter.drawRect(text_rect)
        
        # Draw the text
        painter.setPen(QPen(QColor("#00FF00"), 2))
        painter.setBrush(QBrush())
        painter.drawText(text_rect.adjusted(5, 2, -5, -2), Qt.AlignmentFlag.AlignLeft, airgap_text)
        
        painter.restore()

    def draw_airgap_dimension_lines(self, painter):
        """Draw dimension lines between closest pads"""
        min_airgap, closest_pads = self.calculate_min_pad_to_pad_airgap()
        if min_airgap is None or closest_pads is None:
            return
        
        if min_airgap == 0:  # Skip if pads are overlapping
            return
            
        pad_bounds_list = self.get_individual_pad_bounds_absolute()
        i, j, x_gap, y_gap = closest_pads
        
        b1 = pad_bounds_list[i]
        b2 = pad_bounds_list[j]
        
        # Set dimension line properties
        painter.setPen(QPen(QColor("#FFFF00"), 1.5/self.zoom_factor))  # Yellow dimension lines
        
        if x_gap > 0 and y_gap == 0:  # Horizontally separated
            # Draw horizontal dimension line
            y_center = (max(b1[1], b2[1]) + min(b1[3], b2[3])) / 2
            line_start = QPointF(b1[2], y_center)
            line_end = QPointF(b2[0], y_center)
            
            painter.drawLine(line_start, line_end)
            
            # Draw extension lines
            # Draw extension lines (horizontal gap case)
            painter.drawLine(QPointF(b1[2], b1[1]), QPointF(b1[2], b1[3]))  # right edge of pad 1
            painter.drawLine(QPointF(b2[0], b2[1]), QPointF(b2[0], b2[3]))  # left edge of pad 2

        elif y_gap > 0 and x_gap == 0:  # Vertically separated
            # Draw vertical dimension line
            x_center = (max(b1[0], b2[0]) + min(b1[2], b2[2])) / 2
            line_start = QPointF(x_center, b1[3])  # top edge of pad 1
            line_end   = QPointF(x_center, b2[1])  # bottom edge of pad 2
            painter.drawLine(line_start, line_end)

            # Draw extension lines (vertical gap case)
            painter.drawLine(QPointF(b1[0], b1[3]), QPointF(b1[2], b1[3]))  # top edge of pad 1
            painter.drawLine(QPointF(b2[0], b2[1]), QPointF(b2[2], b2[1]))  # bottom edge of pad 2

    def generate_pad_name(self, pad):
        """Generate padstack name based on pad type and expansions"""
        pad_type = pad['type']
        
        try:
            mask_exp = to_decimal(pad.get('mask_expansion', 0)) if pad.get('mask_enabled', True) else 0
            paste_exp = to_decimal(pad.get('paste_expansion', 0)) if pad.get('paste_enabled', True) else 0
        except (ValueError, TypeError):
            mask_exp = paste_exp = 0
        
        name = ""
        
        if pad_type == 'square':
            try:
                size = to_decimal(pad.get('size', 1))
                name = f"S{int(size * 100)}"
                if mask_exp > 0:
                    mask_size = int((size + 2 * mask_exp) * 100)
                    name += f"M{mask_size}"
                if paste_exp > 0:
                    paste_size = int((size + 2 * paste_exp) * 100)
                    name += f"P{paste_size}"

                if mask_exp < 0:
                    mask_size = int((size + 2 * mask_exp) * 100)
                    name += f"M{mask_size}"
                if paste_exp < 0:
                    paste_size = int((size + 2 * paste_exp) * 100)
                    name += f"P{paste_size}"

            except (ValueError, TypeError):
                name = "S100"
                
        elif pad_type == 'rectangle':
            try:
                length = to_decimal(pad.get('length', 1))
                width = to_decimal(pad.get('width', 1))
                name = f"R{int(length * 100)}_{int(width * 100)}"
                if mask_exp > 0:
                    mask_l = int((length + 2 * mask_exp) * 100)
                    mask_w = int((width + 2 * mask_exp) * 100)
                    name += f"M{mask_l}_{mask_w}"
                if paste_exp > 0:
                    paste_l = int((length + 2 * paste_exp) * 100)
                    paste_w = int((width + 2 * paste_exp) * 100)
                    name += f"P{paste_l}_{paste_w}"
                if mask_exp < 0:
                    mask_l = int((length + 2 * mask_exp) * 100)
                    mask_w = int((width + 2 * mask_exp) * 100)
                    name += f"M{mask_l}_{mask_w}"
                if paste_exp < 0:
                    paste_l = int((length + 2 * paste_exp) * 100)
                    paste_w = int((width + 2 * paste_exp) * 100)
                    name += f"P{paste_l}_{paste_w}"
            except (ValueError, TypeError):
                name = "R100_100"

        elif pad_type == 'rounded_rectangle':
            try:
                length = to_decimal(pad.get('length', 1))
                width = to_decimal(pad.get('width', 1))
                redius = to_decimal(pad.get('corner_radius', 0.2))
                name = f"R{int(length * 100)}_{int(width * 100)}"
                if mask_exp > 0:
                    mask_l = int((length + 2 * mask_exp) * 100)
                    mask_w = int((width + 2 * mask_exp) * 100)
                    name += f"M{mask_l}_{mask_w}"
                if paste_exp > 0:
                    paste_l = int((length + 2 * paste_exp) * 100)
                    paste_w = int((width + 2 * paste_exp) * 100)
                    name += f"P{paste_l}_{paste_w}"
                if mask_exp < 0:
                    mask_l = int((length + 2 * mask_exp) * 100)
                    mask_w = int((width + 2 * mask_exp) * 100)
                    name += f"M{mask_l}_{mask_w}"
                if paste_exp < 0:
                    paste_l = int((length + 2 * paste_exp) * 100)
                    paste_w = int((width + 2 * paste_exp) * 100)
                    name += f"P{paste_l}_{paste_w}"

                name += f"R{int(redius * 100)}"
            except (ValueError, TypeError):
                name = "R100_100R20"

        elif pad_type == 'SMD-oblong':
            try:
                length = to_decimal(pad.get('length', 1))
                width = to_decimal(pad.get('width', 1))
                name = f"B{int(length * 100)}_{int(width * 100)}"
                if mask_exp > 0:
                    mask_l = int((length + 2 * mask_exp) * 100)
                    mask_w = int((width + 2 * mask_exp) * 100)
                    name += f"M{mask_l}_{mask_w}"
                if paste_exp > 0:
                    paste_l = int((length + 2 * paste_exp) * 100)
                    paste_w = int((width + 2 * paste_exp) * 100)
                    name += f"P{paste_l}_{paste_w}"
                if mask_exp < 0:
                    mask_l = int((length + 2 * mask_exp) * 100)
                    mask_w = int((width + 2 * mask_exp) * 100)
                    name += f"M{mask_l}_{mask_w}"
                if paste_exp < 0:
                    paste_l = int((length + 2 * paste_exp) * 100)
                    paste_w = int((width + 2 * paste_exp) * 100)
                    name += f"P{paste_l}_{paste_w}"
            except (ValueError, TypeError):
                name = "B100_100"

        elif pad_type == 'D-shape':
            try:
                length = to_decimal(pad.get('length', 1))
                width = to_decimal(pad.get('width', 1))
                name = f"D{int(length * 100)}_{int(width * 100)}"
                if mask_exp > 0:
                    mask_l = int((length + 2 * mask_exp) * 100)
                    mask_w = int((width + 2 * mask_exp) * 100)
                    name += f"M{mask_l}_{mask_w}"
                if paste_exp > 0:
                    paste_l = int((length + 2 * paste_exp) * 100)
                    paste_w = int((width + 2 * paste_exp) * 100)
                    name += f"P{paste_l}_{paste_w}"
            except (ValueError, TypeError):
                name = "R100_100R20"

        elif pad_type == 'PTH_rectangle':
            try:
                hole_l = to_decimal(pad.get('hole_length', 1.5))
                hole_w = to_decimal(pad.get('hole_width', 0.8))
                pad_l = to_decimal(pad.get('pad_length', 2.0))
                pad_w = to_decimal(pad.get('pad_width', 1.2))
                name = f"R{int(pad_l * 100)}x{int(pad_w * 100)}H{int(hole_l * 100)}_{int(hole_w * 100)}"
                if mask_exp > 0:
                    mask_l = int((pad_l + 2 * mask_exp) * 100)
                    mask_w = int((pad_w + 2 * mask_exp) * 100)
                    name += f"M{mask_l}_{mask_w}"
                if mask_exp < 0:
                    mask_l = int((pad_l + 2 * mask_exp) * 100)
                    mask_w = int((pad_w + 2 * mask_exp) * 100)
                    name += f"M{mask_l}_{mask_w}"

            except (ValueError, TypeError):
                name = "R200_120H150_80"

        elif pad_type == 'NPTH_rectangle':
            try:
                hole_l = to_decimal(pad.get('hole_length', 1.5))
                hole_w = to_decimal(pad.get('hole_width', 0.8))
                name = f"NPTHR{int(hole_l * 100)}x{int(hole_w * 100)}"
            except (ValueError, TypeError):
                name = "NPTHR150x80"
                
        elif pad_type == 'round':
            try:
                diameter = to_decimal(pad.get('diameter', 1))
                name = f"C{int(diameter * 100)}"  # C for circular
                if mask_exp > 0:
                    mask_dia = int((diameter + 2 * mask_exp) * 100)
                    name += f"M{mask_dia}"
                if paste_exp > 0:
                    paste_dia = int((diameter + 2 * paste_exp) * 100)
                    name += f"P{paste_dia}"

                if mask_exp < 0:
                    mask_dia = int((diameter + 2 * mask_exp) * 100)
                    name += f"M{mask_dia}"
                if paste_exp < 0:
                    paste_dia = int((diameter + 2 * paste_exp) * 100)
                    name += f"P{paste_dia}"
            except (ValueError, TypeError):
                name = "C100"
                
        elif pad_type == 'PTH':
            try:
                hole_dia = to_decimal(pad.get('hole_diameter', 0.8))
                pad_dia = to_decimal(pad.get('pad_diameter', 1.2))
                name = f"PTH{int(hole_dia * 100)}_P{int(pad_dia * 100)}"
                if mask_exp > 0:
                    mask_dia = int((pad_dia + 2 * mask_exp) * 100)
                    name += f"_M{mask_dia}"
            except (ValueError, TypeError):
                name = "PTH080_P120"

        elif pad_type == 'NPTH':
            try:
                hole_dia = to_decimal(pad.get('hole_diameter', 0.8))
                name = f"NPTH{int(hole_dia * 100)}"
            except (ValueError, TypeError):
                name = "NPTH080"

                
        elif pad_type == 'PTH_oblong':
            try:
                hole_l = to_decimal(pad.get('hole_length', 1.5))
                hole_w = to_decimal(pad.get('hole_width', 0.8))
                pad_l = to_decimal(pad.get('pad_length', 2.0))
                pad_w = to_decimal(pad.get('pad_width', 1.2))
                name = f"PTHO{int(hole_l * 100)}x{int(hole_w * 100)}_P{int(pad_l * 100)}x{int(pad_w * 100)}"
                if mask_exp > 0:
                    mask_l = int((pad_l + 2 * mask_exp) * 100)
                    mask_w = int((pad_w + 2 * mask_exp) * 100)
                    name += f"_M{mask_l}x{mask_w}"
            except (ValueError, TypeError):
                name = "PTHO150x80_P200x120"

        elif pad_type == 'NPTH_oblong':
            try:
                hole_l = to_decimal(pad.get('hole_length', 1.5))
                hole_w = to_decimal(pad.get('hole_width', 0.8))
                name = f"NPTHO{int(hole_l * 100)}x{int(hole_w * 100)}"
            except (ValueError, TypeError):
                name = "NPTHO150x80"


        elif pad_type == 'PTH_square':     
            try:
                hole_size = to_decimal(pad.get('hole_size', 1.0))
                pad_size = to_decimal(pad.get('pad_size', 1.5))
                name = f"PTHS{int(hole_size * 100)}_P{int(pad_size * 100)}"
                if mask_exp > 0:
                    mask_size = int((pad_size + 2 * mask_exp) * 100)
                    name += f"_M{mask_size}"
            except (ValueError, TypeError):
                name = "PTHS100_P150" 

        elif pad_type == 'PTH_oblong_rect':
            try:
                hole_l = to_decimal(pad.get('hole_length', 1.5))
                hole_w = to_decimal(pad.get('hole_width', 0.8))
                pad_l = to_decimal(pad.get('pad_length', 2.0))
                pad_w = to_decimal(pad.get('pad_width', 1.2))
                name = f"PTHOR{int(hole_l * 100)}x{int(hole_w * 100)}_P{int(pad_l * 100)}x{int(pad_w * 100)}"
                if mask_exp > 0:
                    mask_l = int((pad_l + 2 * mask_exp) * 100)
                    mask_w = int((pad_w + 2 * mask_exp) * 100)
                    name += f"M{mask_l}_{mask_w}"
            except (ValueError, TypeError):
                name = "PTHOR150x80_P200x120"
            
        return name

class PadPositionResolver:
    def __init__(self, pads):
        self.pads = pads
        self.cache = {}
        self.resolved_positions = {}

    def clear_cache(self):
        self.cache.clear()
        self.resolved_positions.clear()

    def get_pad_by_pin(self, pin_number):
        for pad in self.pads:
            if pad.get('pin_number', None) == pin_number:
                return pad
        return None

    def get_absolute_position(self, pad, visiting=None):
        """Get absolute position with cycle detection"""
        if visiting is None:
            visiting = set()
        
        pad_pin = pad.get('pin_number', '')
        
        # Check cache first
        if pad_pin in self.cache:
            return self.cache[pad_pin]
        
        # Check for circular reference
        if pad_pin in visiting:
            print(f"Warning: Circular reference detected for pad {pad_pin}. Using origin offset.")
            try:
                x_offset = to_decimal(pad.get('x_offset', 0))
                y_offset = to_decimal(pad.get('y_offset', 0))
            except (ValueError, TypeError):
                x_offset, y_offset = 0, 0
            self.cache[pad_pin] = (x_offset, y_offset)
            return x_offset, y_offset
        
        # Add current pad to visiting set
        visiting.add(pad_pin)
        
        offset_from = pad.get('offset_from', 'origin')
        try:
            x_offset = to_decimal(pad.get('x_offset', 0))
            y_offset = to_decimal(pad.get('y_offset', 0))
        except (ValueError, TypeError):
            x_offset, y_offset = 0, 0
        
        if offset_from == 'origin':
            abs_x, abs_y = x_offset, y_offset
            self.resolved_positions[pad_pin] = (abs_x, abs_y)
        else:
            # Direct pin reference with cycle detection
            ref_pad = self.get_pad_by_pin(offset_from)
            if ref_pad and ref_pad != pad:
                try:
                    ref_x, ref_y = self.get_absolute_position(ref_pad, visiting)
                    abs_x = ref_x + x_offset
                    abs_y = ref_y + y_offset
                    self.resolved_positions[pad_pin] = (abs_x, abs_y)
                except RecursionError:
                    print(f"Warning: Recursion limit reached for pad {pad_pin}. Using origin offset.")
                    abs_x, abs_y = x_offset, y_offset
                    self.resolved_positions[pad_pin] = (abs_x, abs_y)
            else:
                # Fallback to origin if reference not found
                abs_x, abs_y = x_offset, y_offset
                self.resolved_positions[pad_pin] = (abs_x, abs_y)
        
        # Remove from visiting set before returning
        visiting.discard(pad_pin)
        
        # Cache the result
        self.cache[pad_pin] = (abs_x, abs_y)
        return abs_x, abs_y


    def resolve_all_positions(self):
        self.clear_cache()
        
        # Resolve origin-based pads first
        for pad in self.pads:
            if pad.get('offset_from', 'origin') == 'origin':
                self.get_absolute_position(pad)

        # Iteratively resolve referenced pads
        max_iterations = len(self.pads) * 2
        for _ in range(max_iterations):
            resolved_any = False
            for pad in self.pads:
                pad_pin = pad.get('pin_number', '')
                if pad_pin not in self.resolved_positions:
                    try:
                        self.get_absolute_position(pad)
                        resolved_any = True
                    except:
                        continue
            
            if not resolved_any:
                break

        return self.resolved_positions

class PadStackRow(QWidget):
    delete_requested = pyqtSignal(object)
    data_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        # Main container with grouped sections
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # Create group box for this padstack
        self.group_box = QGroupBox("Padstack Configuration")
        group_layout = QVBoxLayout(self.group_box)
        group_layout.setSpacing(5)

        # ===== ROW 1: Pad Type and Geometry =====
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(10)

        # Pad Type Group
        type_group = QGroupBox("Pad Type")
        type_layout = QHBoxLayout(type_group)
        type_layout.setContentsMargins(5, 5, 5, 5)

        self.type_combo = QComboBox()
        self.type_combo.addItems([
            'square', 'rectangle', 'rounded_rectangle', 'round', 'custom',
            'SMD-oblong', 'D-shape', 'PTH', 'NPTH', 'PTH_oblong', 'NPTH_oblong', 
            'PTH_rectangle', 'NPTH_rectangle', 'PTH_square', 'PTH_oblong_rect'  # New types
        ])
        type_layout.addWidget(self.type_combo)

        row1_layout.addWidget(type_group)

        # Geometry Group (Dynamic based on pad type)
        self.geometry_group = QGroupBox("Geometry")
        self.geometry_layout = QHBoxLayout(self.geometry_group)
        self.geometry_layout.setContentsMargins(5, 5, 5, 5)
        row1_layout.addWidget(self.geometry_group)

        # Action Buttons Group
        actions_group = QGroupBox("Actions")
        actions_layout = QHBoxLayout(actions_group)
        actions_layout.setContentsMargins(5, 5, 5, 5)

        self.duplicate_btn = QPushButton("Duplicate")
        self.duplicate_btn.setMaximumWidth(80)
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setMaximumWidth(60)

        actions_layout.addWidget(self.duplicate_btn)
        actions_layout.addWidget(self.delete_btn)
        row1_layout.addWidget(actions_group)

        group_layout.addLayout(row1_layout)

        # ===== ROW 2: Position and Layer Properties =====
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(10)

        # Position Group
        position_group = QGroupBox("Position")
        position_layout = QGridLayout(position_group)
        position_layout.setContentsMargins(5, 5, 5, 5)

        position_layout.addWidget(QLabel("X Offset:"), 0, 0)
        self.x_offset = QLineEdit()
        self.x_offset.setText("0")
        self.x_offset.setMaximumWidth(100)
        position_layout.addWidget(self.x_offset, 0, 1)

        position_layout.addWidget(QLabel("Y Offset:"), 0, 2)
        self.y_offset = QLineEdit()
        self.y_offset.setText("0")
        self.y_offset.setMaximumWidth(100)
        position_layout.addWidget(self.y_offset, 0, 3)

        position_layout.addWidget(QLabel("Offset From:"), 1, 0)
        # Dynamic dropdown instead of fixed directional options
        self.offset_from = QComboBox()
        self.offset_from.setMaximumWidth(100)
        position_layout.addWidget(self.offset_from, 1, 1, 1, 2)

        position_layout.addWidget(QLabel("Pin:"), 1, 2)
        self.pin_number = QLineEdit()
        self.pin_number.setMaximumWidth(50)
        position_layout.addWidget(self.pin_number, 1, 3)

        row2_layout.addWidget(position_group)


        # Layer Properties Group
        layers_group = QGroupBox("Layer Properties")
        layers_layout = QGridLayout(layers_group)
        layers_layout.setContentsMargins(5, 5, 5, 5)

        layers_layout.addWidget(QLabel("Mask Expansion:"), 0, 0)
        self.mask_expansion = QLineEdit()
        self.mask_expansion.setText("0")
        self.mask_expansion.setMaximumWidth(100)
        layers_layout.addWidget(self.mask_expansion, 0, 1)

        layers_layout.addWidget(QLabel("Paste Expansion:"), 1, 0)
        self.paste_expansion = QLineEdit()
        self.paste_expansion.setText("0")
        self.paste_expansion.setMaximumWidth(100)
        layers_layout.addWidget(self.paste_expansion, 1, 1)

        # Add checkboxes for enabling/disabling mask and paste layers
        self.mask_enabled = QCheckBox("Enable Mask")
        self.mask_enabled.setChecked(True)
        layers_layout.addWidget(self.mask_enabled, 0, 2)

        self.paste_enabled = QCheckBox("Enable Paste")
        self.paste_enabled.setChecked(True)
        layers_layout.addWidget(self.paste_enabled, 1, 2)

        row2_layout.addWidget(layers_group)

        group_layout.addLayout(row2_layout)

        # Custom polygon widget (initially hidden)
        self.polygon_widget = CustomPolygonWidget()
        self.polygon_widget.data_changed.connect(self.data_changed.emit)
        self.polygon_widget.setVisible(False)
        group_layout.addWidget(self.polygon_widget)

        main_layout.addWidget(self.group_box)
        self.setLayout(main_layout)

        # Initialize geometry inputs
        self.update_geometry_inputs()

    def connect_signals(self):
        self.type_combo.currentTextChanged.connect(self.update_geometry_inputs)
        self.type_combo.currentTextChanged.connect(self.update_layer_visibility)
        self.type_combo.currentTextChanged.connect(self.data_changed.emit)
        self.delete_btn.clicked.connect(lambda: self.delete_requested.emit(self))

        # Connect all input signals
        self.x_offset.textChanged.connect(self.data_changed.emit)
        self.y_offset.textChanged.connect(self.data_changed.emit)
        self.mask_expansion.textChanged.connect(self.data_changed.emit)
        self.paste_expansion.textChanged.connect(self.data_changed.emit)
        self.mask_enabled.stateChanged.connect(self.data_changed.emit)
        self.paste_enabled.stateChanged.connect(self.data_changed.emit)

        self.offset_from.currentTextChanged.connect(self.data_changed.emit)
        
        # Update dropdown when pin numbers change
        self.pin_number.textChanged.connect(self.update_offset_from_options)
        self.pin_number.textChanged.connect(self.data_changed.emit)

    def update_layer_visibility(self):
        """Show/hide layer checkboxes based on pad type"""
        pad_type = self.type_combo.currentText()
        smd_types = ['square', 'rectangle', 'rounded_rectangle', 'round', 'SMD-oblong', 'D-shape', 'custom']
        
        # Show checkboxes only for SMD pad types
        is_smd = pad_type in smd_types
        self.mask_enabled.setVisible(is_smd)
        self.paste_enabled.setVisible(is_smd)

    def update_offset_from_options(self):
        """Update the offset_from dropdown with all available pin numbers"""
        # Get the parent FootprintDesigner to access all padstack rows
        parent_designer = self.get_parent_designer()
        if not parent_designer:
            return

        # Collect all pin numbers except the current one
        available_pins = []
        current_pin = self.pin_number.text().strip()

        for row in parent_designer.padstack_rows:
            if row != self: # Don't include self
                pin_text = row.pin_number.text().strip()
                if pin_text and pin_text != current_pin:
                    available_pins.append(pin_text)

        # Update the dropdown
        current_selection = self.offset_from.currentText()
        self.offset_from.blockSignals(True)
        self.offset_from.clear()
        self.offset_from.addItem('origin') # Always include origin

        # Sort pin numbers numerically if possible, otherwise alphabetically
        try:
            available_pins.sort(key=lambda x: int(x) if x.isdigit() else to_decimal('inf'))
        except:
            available_pins.sort()

        self.offset_from.addItems(available_pins)

        # Restore previous selection if still valid
        index = self.offset_from.findText(current_selection)
        if index >= 0:
            self.offset_from.setCurrentIndex(index)
        else:
            self.offset_from.setCurrentText('origin')

        self.offset_from.blockSignals(False)

    def get_parent_designer(self):
        """Find the parent FootprintDesigner instance"""
        parent = self.parent()
        while parent:
            if hasattr(parent, 'padstack_rows'):
                return parent
            parent = parent.parent()
        return None

    def update_geometry_inputs(self):
        # Clear existing geometry inputs
        for i in reversed(range(self.geometry_layout.count())):
            item = self.geometry_layout.itemAt(i)
            if item:
                widget = item.widget()
                if widget:
                    widget.setParent(None)

        pad_type = self.type_combo.currentText()

        # Show/hide polygon widget
        self.polygon_widget.setVisible(pad_type == 'custom')
        
        # Update layer visibility
        self.update_layer_visibility()

        if pad_type == 'square':
            self.geometry_layout.addWidget(QLabel("Size:"))
            self.size_input = QLineEdit()
            self.size_input.setText("1.0")
            self.size_input.setMaximumWidth(100)
            self.size_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.size_input)

        elif pad_type in ['rectangle', 'SMD-oblong']:
            self.geometry_layout.addWidget(QLabel("Length:"))
            self.length_input = QLineEdit()
            self.length_input.setText("1.0")
            self.length_input.setMaximumWidth(100)
            self.length_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.length_input)

            self.geometry_layout.addWidget(QLabel("Width:"))
            self.width_input = QLineEdit()
            self.width_input.setText("1.0")
            self.width_input.setMaximumWidth(100)
            self.width_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.width_input)

            # NEW: Rotation input added
            self.geometry_layout.addWidget(QLabel("Rotation:"))
            self.rotation_input = QLineEdit("0")
            self.rotation_input.setMaximumWidth(100)
            self.rotation_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.rotation_input)            

        elif pad_type == 'rounded_rectangle':
            self.geometry_layout.addWidget(QLabel("Length:"))
            self.length_input = QLineEdit()
            self.length_input.setText("1.0")
            self.length_input.setMaximumWidth(100)
            self.length_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.length_input)

            self.geometry_layout.addWidget(QLabel("Width:"))
            self.width_input = QLineEdit()
            self.width_input.setText("1.0")
            self.width_input.setMaximumWidth(100)
            self.width_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.width_input)

            self.geometry_layout.addWidget(QLabel("Corner Radius:"))
            self.corner_radius_input = QLineEdit()
            self.corner_radius_input.setText("0.2")
            self.corner_radius_input.setMaximumWidth(100)
            self.corner_radius_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.corner_radius_input)

            self.geometry_layout.addWidget(QLabel("Rotation:"))
            self.rotation_input = QLineEdit("0")
            self.rotation_input.setMaximumWidth(100)
            self.rotation_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.rotation_input)   

        elif pad_type in ['round']:
            self.geometry_layout.addWidget(QLabel("Diameter:"))
            self.diameter_input = QLineEdit()
            self.diameter_input.setText("1.0")
            self.diameter_input.setMaximumWidth(100)
            self.diameter_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.diameter_input)

        elif pad_type in ['PTH', 'NPTH']:
            # Round through hole
            self.geometry_layout.addWidget(QLabel("Hole Diameter:"))
            self.hole_diameter_input = QLineEdit()
            self.hole_diameter_input.setText("0.8")
            self.hole_diameter_input.setMaximumWidth(100)
            self.hole_diameter_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.hole_diameter_input)

            if pad_type == 'PTH':
                # PTH needs pad diameter
                self.geometry_layout.addWidget(QLabel("Pad Diameter:"))
                self.pad_diameter_input = QLineEdit()
                self.pad_diameter_input.setText("1.2")
                self.pad_diameter_input.setMaximumWidth(100)
                self.pad_diameter_input.textChanged.connect(self.data_changed.emit)
                self.geometry_layout.addWidget(self.pad_diameter_input)

        elif pad_type in ['PTH_oblong', 'NPTH_oblong']:
            # Oblong through hole
            self.geometry_layout.addWidget(QLabel("Hole Length:"))
            self.hole_length_input = QLineEdit()
            self.hole_length_input.setText("1.5")
            self.hole_length_input.setMaximumWidth(100)
            self.hole_length_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.hole_length_input)

            self.geometry_layout.addWidget(QLabel("Hole Width:"))
            self.hole_width_input = QLineEdit()
            self.hole_width_input.setText("0.8")
            self.hole_width_input.setMaximumWidth(100)
            self.hole_width_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.hole_width_input)

            if pad_type == 'PTH_oblong':
                # PTH oblong needs pad dimensions
                self.geometry_layout.addWidget(QLabel("Pad Length:"))
                self.pad_length_input = QLineEdit()
                self.pad_length_input.setText("2.0")
                self.pad_length_input.setMaximumWidth(100)
                self.pad_length_input.textChanged.connect(self.data_changed.emit)
                self.geometry_layout.addWidget(self.pad_length_input)

                self.geometry_layout.addWidget(QLabel("Pad Width:"))
                self.pad_width_input = QLineEdit()
                self.pad_width_input.setText("1.2")
                self.pad_width_input.setMaximumWidth(100)
                self.pad_width_input.textChanged.connect(self.data_changed.emit)
                self.geometry_layout.addWidget(self.pad_width_input)

            # Add rotation control for oblong pads
            self.geometry_layout.addWidget(QLabel("Rotation:"))
            self.rotation_input = QLineEdit()
            self.rotation_input.setText("0")
            self.rotation_input.setMaximumWidth(80)
            self.rotation_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.rotation_input)

        elif pad_type == 'D-shape':
            self.geometry_layout.addWidget(QLabel("Pad Length:"))
            self.length_input = QLineEdit()
            self.length_input.setText("1.0")
            self.length_input.setMaximumWidth(100)
            self.length_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.length_input)

            self.geometry_layout.addWidget(QLabel("Pad Width:"))
            self.width_input = QLineEdit()
            self.width_input.setText("1.0")
            self.width_input.setMaximumWidth(100)
            self.width_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.width_input)

            self.geometry_layout.addWidget(QLabel("Corner Radius:"))
            self.corner_radius_input = QLineEdit()
            self.corner_radius_input.setText("0.2")
            self.corner_radius_input.setMaximumWidth(100)
            self.corner_radius_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.corner_radius_input)

            self.geometry_layout.addWidget(QLabel("Rotation:"))
            self.rotation_input = QLineEdit()
            self.rotation_input.setText("0")
            self.rotation_input.setMaximumWidth(80)
            self.rotation_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.rotation_input)

        elif pad_type == 'PTH_rectangle':
            self.geometry_layout.addWidget(QLabel("Hole Length:"))
            self.hole_length_input = QLineEdit()
            self.hole_length_input.setText("1.5")
            self.hole_length_input.setMaximumWidth(100)
            self.hole_length_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.hole_length_input)

            self.geometry_layout.addWidget(QLabel("Hole Width:"))
            self.hole_width_input = QLineEdit()
            self.hole_width_input.setText("0.8")
            self.hole_width_input.setMaximumWidth(100)
            self.hole_width_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.hole_width_input)

            self.geometry_layout.addWidget(QLabel("Pad Length:"))
            self.pad_length_input = QLineEdit()
            self.pad_length_input.setText("2.0")
            self.pad_length_input.setMaximumWidth(100)
            self.pad_length_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.pad_length_input)

            self.geometry_layout.addWidget(QLabel("Pad Width:"))
            self.pad_width_input = QLineEdit()
            self.pad_width_input.setText("1.2")
            self.pad_width_input.setMaximumWidth(100)
            self.pad_width_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.pad_width_input)

            self.geometry_layout.addWidget(QLabel("Rotation:"))
            self.rotation_input = QLineEdit()
            self.rotation_input.setText("0")
            self.rotation_input.setMaximumWidth(80)
            self.rotation_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.rotation_input)

        elif pad_type == 'NPTH_rectangle':
            # NPTH rectangle (rectangular hole, no pad)
            self.geometry_layout.addWidget(QLabel("Hole Length:"))
            self.hole_length_input = QLineEdit()
            self.hole_length_input.setText("1.5")
            self.hole_length_input.setMaximumWidth(100)
            self.hole_length_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.hole_length_input)

            self.geometry_layout.addWidget(QLabel("Hole Width:"))
            self.hole_width_input = QLineEdit()
            self.hole_width_input.setText("0.8")
            self.hole_width_input.setMaximumWidth(100)
            self.hole_width_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.hole_width_input)

            # Add rotation control for NPTH rectangle
            self.geometry_layout.addWidget(QLabel("Rotation:"))
            self.rotation_input = QLineEdit()
            self.rotation_input.setText("0")
            self.rotation_input.setMaximumWidth(80)
            self.rotation_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.rotation_input)

        elif pad_type == 'PTH_square':
            # PTH with square pad
            self.geometry_layout.addWidget(QLabel("Hole Diameter:"))
            self.hole_diameter_input = QLineEdit()
            self.hole_diameter_input.setText("0.8")
            self.hole_diameter_input.setMaximumWidth(100)
            self.hole_diameter_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.hole_diameter_input)
            
            self.geometry_layout.addWidget(QLabel("Pad Size:"))
            self.pad_size_input = QLineEdit()
            self.pad_size_input.setText("1.5")
            self.pad_size_input.setMaximumWidth(100)
            self.pad_size_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.pad_size_input)

        elif pad_type == 'PTH_oblong_rect':
            # PTH oblong with rectangular pad
            self.geometry_layout.addWidget(QLabel("Hole Length:"))
            self.hole_length_input = QLineEdit()
            self.hole_length_input.setText("1.5")
            self.hole_length_input.setMaximumWidth(100)
            self.hole_length_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.hole_length_input)
            
            self.geometry_layout.addWidget(QLabel("Hole Width:"))
            self.hole_width_input = QLineEdit()
            self.hole_width_input.setText("0.8")
            self.hole_width_input.setMaximumWidth(100)
            self.hole_width_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.hole_width_input)
            
            self.geometry_layout.addWidget(QLabel("Pad Length:"))
            self.pad_length_input = QLineEdit()
            self.pad_length_input.setText("2.5")
            self.pad_length_input.setMaximumWidth(100)
            self.pad_length_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.pad_length_input)
            
            self.geometry_layout.addWidget(QLabel("Pad Width:"))
            self.pad_width_input = QLineEdit()
            self.pad_width_input.setText("1.5")
            self.pad_width_input.setMaximumWidth(100)
            self.pad_width_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.pad_width_input)
            
            self.geometry_layout.addWidget(QLabel("Rotation:"))
            self.rotation_input = QLineEdit()
            self.rotation_input.setText("0")
            self.rotation_input.setMaximumWidth(80)
            self.rotation_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.rotation_input)



        elif pad_type == 'custom':
            # Custom polygon inputs handled by polygon_widget
            self.geometry_layout.addWidget(QLabel("Custom Polygon (see below)"))

        # ADD TOLERANCE INPUT FOR THROUGH HOLE PAD TYPES
        through_hole_types = ['PTH', 'NPTH', 'PTH_oblong', 'NPTH_oblong', 'PTH_rectangle', 'NPTH_rectangle']
        
        if pad_type in through_hole_types:
            self.geometry_layout.addWidget(QLabel("Tolerance (mm):"))
            self.tolerance_input = QLineEdit()
            self.tolerance_input.setText("0.05")  # Default tolerance value
            self.tolerance_input.setMaximumWidth(80)
            self.tolerance_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.tolerance_input)

        # Add stretch to push everything to the left
        self.geometry_layout.addStretch()

    def get_data(self):
        data = {
            'type': self.type_combo.currentText(),
            'x_offset': self.x_offset.text(),
            'y_offset': self.y_offset.text(),
            'offset_from': self.offset_from.currentText(),
            'mask_expansion': self.mask_expansion.text(),
            'paste_expansion': self.paste_expansion.text(),
            'mask_enabled': self.mask_enabled.isChecked(),
            'paste_enabled': self.paste_enabled.isChecked(),
            'pin_number': self.pin_number.text()
        }

        pad_type = self.type_combo.currentText()

        # ADD TOLERANCE FOR THROUGH HOLE PADS
        through_hole_types = ['PTH', 'NPTH', 'PTH_oblong', 'NPTH_oblong', 'PTH_rectangle', 'NPTH_rectangle', 'PTH_square', 'PTH_oblong_rect']
        if pad_type in through_hole_types and hasattr(self, 'tolerance_input'):
            data['tolerance'] = self.tolerance_input.text()

        if pad_type == 'square' and hasattr(self, 'size_input'):
            data['size'] = self.size_input.text()

        elif pad_type in ['rectangle', 'rounded_rectangle', 'SMD-oblong']:
            if hasattr(self, 'length_input'):
                data['length'] = self.length_input.text()
            if hasattr(self, 'width_input'):
                data['width'] = self.width_input.text()
            if hasattr(self, 'rotation_input'):
                data['rotation'] = self.rotation_input.text()                
            if pad_type == 'rounded_rectangle' and hasattr(self, 'corner_radius_input'):
                data['corner_radius'] = self.corner_radius_input.text()


        elif pad_type in ['round'] and hasattr(self, 'diameter_input'):
            data['diameter'] = self.diameter_input.text()

        elif pad_type in ['D-shape']:
            if hasattr(self, 'length_input'):
                data['length'] = self.length_input.text()
            if hasattr(self, 'width_input'):
                data['width'] = self.width_input.text()
            if hasattr(self, 'corner_radius_input'):
                data['corner_radius'] = self.corner_radius_input.text()
            if hasattr(self, 'rotation_input'):
                data['rotation'] = self.rotation_input.text()

        elif pad_type in ['PTH', 'NPTH']:
            if hasattr(self, 'hole_diameter_input'):
                data['hole_diameter'] = self.hole_diameter_input.text()
            if pad_type == 'PTH' and hasattr(self, 'pad_diameter_input'):
                data['pad_diameter'] = self.pad_diameter_input.text()

        elif pad_type in ['PTH_oblong', 'NPTH_oblong']:
            if hasattr(self, 'hole_length_input'):
                data['hole_length'] = self.hole_length_input.text()
            if hasattr(self, 'hole_width_input'):
                data['hole_width'] = self.hole_width_input.text()
            if hasattr(self, 'rotation_input'):
                data['rotation'] = self.rotation_input.text()
            if pad_type == 'PTH_oblong':
                if hasattr(self, 'pad_length_input'):
                    data['pad_length'] = self.pad_length_input.text()
                if hasattr(self, 'pad_width_input'):
                    data['pad_width'] = self.pad_width_input.text()

        elif pad_type == 'PTH_rectangle':
            if hasattr(self, 'hole_length_input'):
                data['hole_length'] = self.hole_length_input.text()
            if hasattr(self, 'hole_width_input'):
                data['hole_width'] = self.hole_width_input.text()
            if hasattr(self, 'pad_length_input'):
                data['pad_length'] = self.pad_length_input.text()
            if hasattr(self, 'pad_width_input'):
                data['pad_width'] = self.pad_width_input.text()
            if hasattr(self, 'rotation_input'):
                data['rotation'] = self.rotation_input.text()

        elif pad_type == 'NPTH_rectangle':
            if hasattr(self, 'hole_length_input'):
                data['hole_length'] = self.hole_length_input.text()
            if hasattr(self, 'hole_width_input'):
                data['hole_width'] = self.hole_width_input.text()
            if hasattr(self, 'rotation_input'):
                data['rotation'] = self.rotation_input.text()

        # In get_data method:
        elif pad_type == 'PTH_square':
            if hasattr(self, 'hole_diameter_input'):
                data['hole_diameter'] = self.hole_diameter_input.text()
            if hasattr(self, 'pad_size_input'):
                data['pad_size'] = self.pad_size_input.text()
                
        elif pad_type == 'PTH_oblong_rect':
            if hasattr(self, 'hole_length_input'):
                data['hole_length'] = self.hole_length_input.text()
            if hasattr(self, 'hole_width_input'):
                data['hole_width'] = self.hole_width_input.text()
            if hasattr(self, 'pad_length_input'):
                data['pad_length'] = self.pad_length_input.text()
            if hasattr(self, 'pad_width_input'):
                data['pad_width'] = self.pad_width_input.text()
            if hasattr(self, 'rotation_input'):
                data['rotation'] = self.rotation_input.text()


        elif pad_type == 'custom':
            data['polygon_data'] = self.polygon_widget.get_data()

        return data

    def set_data(self, data):
        self.type_combo.setCurrentText(data.get('type', 'square'))
        self.x_offset.setText(str(data.get('x_offset', 0)))
        self.y_offset.setText(str(data.get('y_offset', 0)))
        self.mask_expansion.setText(str(data.get('mask_expansion', 0)))
        self.paste_expansion.setText(str(data.get('paste_expansion', 0)))
        self.mask_enabled.setChecked(data.get('mask_enabled', True))
        self.paste_enabled.setChecked(data.get('paste_enabled', True))
        self.pin_number.setText(str(data.get('pin_number', '1')))

        # Update options first, then set the selection
        self.update_offset_from_options()
        self.offset_from.setCurrentText(data.get('offset_from', 'origin'))

        # Set type-specific data
        pad_type = data.get('type', 'square')
        # SET TOLERANCE FOR THROUGH HOLE PADS
        through_hole_types = ['PTH', 'NPTH', 'PTH_oblong', 'NPTH_oblong', 'PTH_rectangle', 'NPTH_rectangle', 'PTH_square', 'PTH_oblong_rect']
        if pad_type in through_hole_types and hasattr(self, 'tolerance_input'):
            self.tolerance_input.setText(str(data.get('tolerance', '0.05')))

        if pad_type == 'square' and hasattr(self, 'size_input'):
            self.size_input.setText(str(data.get('size', '1.0')))

        elif pad_type in ['rectangle', 'rounded_rectangle', 'SMD-oblong']:
            if hasattr(self, 'length_input'):
                self.length_input.setText(str(data.get('length', '1.0')))
            if hasattr(self, 'width_input'):
                self.width_input.setText(str(data.get('width', '1.0')))
            if hasattr(self, 'rotation_input'):
                self.rotation_input.setText(str(data.get('rotation', '0')))                
            if pad_type == 'rounded_rectangle' and hasattr(self, 'corner_radius_input'):
                self.corner_radius_input.setText(str(data.get('corner_radius', '0.2')))

        elif pad_type in ['round'] and hasattr(self, 'diameter_input'):
            self.diameter_input.setText(str(data.get('diameter', '1.0')))

        elif pad_type == 'D-shape':
            if hasattr(self, 'length_input'):
                self.length_input.setText(str(data.get('length', '1.0')))
            if hasattr(self, 'width_input'):
                self.width_input.setText(str(data.get('width', '1.0')))
            if hasattr(self, 'corner_radius_input'):
                self.corner_radius_input.setText(str(data.get('corner_radius', '0.2')))
            if hasattr(self, 'rotation_input'):
                self.rotation_input.setText(str(data.get('rotation', '0')))

        elif pad_type in ['PTH', 'NPTH']:
            if hasattr(self, 'hole_diameter_input'):
                self.hole_diameter_input.setText(str(data.get('hole_diameter', '0.8')))
            if pad_type == 'PTH' and hasattr(self, 'pad_diameter_input'):
                self.pad_diameter_input.setText(str(data.get('pad_diameter', '1.2')))

        elif pad_type in ['PTH_oblong', 'NPTH_oblong']:
            if hasattr(self, 'hole_length_input'):
                self.hole_length_input.setText(str(data.get('hole_length', '1.5')))
            if hasattr(self, 'hole_width_input'):
                self.hole_width_input.setText(str(data.get('hole_width', '0.8')))
            if hasattr(self, 'rotation_input'):
                self.rotation_input.setText(str(data.get('rotation', '0')))
            if pad_type == 'PTH_oblong':
                if hasattr(self, 'pad_length_input'):
                    self.pad_length_input.setText(str(data.get('pad_length', '2.0')))
                if hasattr(self, 'pad_width_input'):
                    self.pad_width_input.setText(str(data.get('pad_width', '1.2')))

        elif pad_type == 'PTH_rectangle':
            if hasattr(self, 'hole_length_input'):
                self.hole_length_input.setText(str(data.get('hole_length', '1.5')))
            if hasattr(self, 'hole_width_input'):
                self.hole_width_input.setText(str(data.get('hole_width', '0.8')))
            if hasattr(self, 'pad_length_input'):
                self.pad_length_input.setText(str(data.get('pad_length', '2.0')))
            if hasattr(self, 'pad_width_input'):
                self.pad_width_input.setText(str(data.get('pad_width', '1.2')))
            if hasattr(self, 'rotation_input'):
                self.rotation_input.setText(str(data.get('rotation', '0')))

        elif pad_type == 'NPTH_rectangle':
            if hasattr(self, 'hole_length_input'):
                self.hole_length_input.setText(str(data.get('hole_length', '1.5')))
            if hasattr(self, 'hole_width_input'):
                self.hole_width_input.setText(str(data.get('hole_width', '0.8')))
            if hasattr(self, 'rotation_input'):
                self.rotation_input.setText(str(data.get('rotation', '0')))


        # In set_data method:
        elif pad_type == 'PTH_square':
            if hasattr(self, 'hole_diameter_input'):
                self.hole_diameter_input.setText(str(data.get('hole_diameter', '0.8')))
            if hasattr(self, 'pad_size_input'):
                self.pad_size_input.setText(str(data.get('pad_size', '1.5')))
                
        elif pad_type == 'PTH_oblong_rect':
            if hasattr(self, 'hole_length_input'):
                self.hole_length_input.setText(str(data.get('hole_length', '1.5')))
            if hasattr(self, 'hole_width_input'):
                self.hole_width_input.setText(str(data.get('hole_width', '0.8')))
            if hasattr(self, 'pad_length_input'):
                self.pad_length_input.setText(str(data.get('pad_length', '2.5')))
            if hasattr(self, 'pad_width_input'):
                self.pad_width_input.setText(str(data.get('pad_width', '1.5')))
            if hasattr(self, 'rotation_input'):
                self.rotation_input.setText(str(data.get('rotation', '0')))



        elif pad_type == 'custom':
            self.polygon_widget.set_data(data.get('polygon_data', {}))

class CustomLayerRow(QWidget):
    delete_requested = pyqtSignal(object)
    data_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        main_layout = QVBoxLayout()

    
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # Create group box for this custom layer
        self.group_box = QGroupBox("Custom Layer Configuration")
        group_layout = QVBoxLayout(self.group_box)
        group_layout.setSpacing(5)

        # Row 1: Shape and Geometry
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(10)

        # Shape Group
        shape_group = QGroupBox("Shape")
        shape_layout = QHBoxLayout(shape_group)
        shape_layout.setContentsMargins(5, 5, 5, 5)

        self.shape_combo = QComboBox()
        self.shape_combo.addItems(['rectangle', 'rounded_rectangle', 'oblong', 'custom_polygon'])
        shape_layout.addWidget(self.shape_combo)
        row1_layout.addWidget(shape_group)

        # Geometry Group (Dynamic based on shape)
        self.geometry_group = QGroupBox("Geometry")
        self.geometry_layout = QHBoxLayout(self.geometry_group)
        self.geometry_layout.setContentsMargins(5, 5, 5, 5)
        row1_layout.addWidget(self.geometry_group)

        # Actions Group
        actions_group = QGroupBox("Actions")
        actions_layout = QHBoxLayout(actions_group)
        actions_layout.setContentsMargins(5, 5, 5, 5)

        self.duplicate_btn = QPushButton("Duplicate")
        self.duplicate_btn.setMaximumWidth(80)
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setMaximumWidth(60)

        actions_layout.addWidget(self.duplicate_btn)
        actions_layout.addWidget(self.delete_btn)
        row1_layout.addWidget(actions_group)

        group_layout.addLayout(row1_layout)

        # Row 2: Layer and Position
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(10)

        # Layer Group
        layer_group = QGroupBox("Layer")
        layer_layout = QHBoxLayout(layer_group)
        layer_layout.setContentsMargins(5, 5, 5, 5)

        self.layer_combo = QComboBox()
        self.layer_combo.addItems(['mask', 'paste', 'keepout'])
        layer_layout.addWidget(self.layer_combo)
        row2_layout.addWidget(layer_group)

        # Position Group
        position_group = QGroupBox("Position")
        position_layout = QGridLayout(position_group)
        position_layout.setContentsMargins(5, 5, 5, 5)

        position_layout.addWidget(QLabel("X Offset:"), 0, 0)
        self.x_offset = QLineEdit()
        self.x_offset.setText("0")
        self.x_offset.setMaximumWidth(100)
        position_layout.addWidget(self.x_offset, 0, 1)

        position_layout.addWidget(QLabel("Y Offset:"), 0, 2)
        self.y_offset = QLineEdit()
        self.y_offset.setText("0")
        self.y_offset.setMaximumWidth(100)
        position_layout.addWidget(self.y_offset, 0, 3)

        position_layout.addWidget(QLabel("Offset From:"), 1, 0)
        self.offset_from = QComboBox()
        self.offset_from.setMaximumWidth(100)
        position_layout.addWidget(self.offset_from, 1, 1, 1, 2)

        row2_layout.addWidget(position_group)
        group_layout.addLayout(row2_layout)

        # Custom polygon widget (initially hidden)
        self.polygon_widget = CustomPolygonWidget()
        self.polygon_widget.data_changed.connect(self.data_changed.emit)
        self.polygon_widget.setVisible(False)
        group_layout.addWidget(self.polygon_widget)

        main_layout.addWidget(self.group_box)
        self.setLayout(main_layout)

        # Initialize geometry inputs
        self.update_geometry_inputs()

    def connect_signals(self):
        self.shape_combo.currentTextChanged.connect(self.update_geometry_inputs)
        self.shape_combo.currentTextChanged.connect(self.data_changed.emit)
        self.delete_btn.clicked.connect(lambda: self.delete_requested.emit(self))

        # Connect all input signals
        self.x_offset.textChanged.connect(self.data_changed.emit)
        self.y_offset.textChanged.connect(self.data_changed.emit)
        self.layer_combo.currentTextChanged.connect(self.data_changed.emit)
        self.offset_from.currentTextChanged.connect(self.data_changed.emit)
        
        # ADD THIS LINE - Connect polygon widget signals
        self.polygon_widget.data_changed.connect(self.data_changed.emit)


    def update_geometry_inputs(self):
        # Clear existing geometry inputs
        for i in reversed(range(self.geometry_layout.count())):
            item = self.geometry_layout.itemAt(i)
            if item:
                widget = item.widget()
                if widget:
                    widget.setParent(None)

        shape = self.shape_combo.currentText()

        # Show/hide polygon widget
        self.polygon_widget.setVisible(shape == 'custom_polygon')
        # ADD THIS: Force layout update when showing polygon widget
        if shape == 'custom_polygon':
            self.polygon_widget.updateGeometry()       

        if shape == 'rectangle':
            self.geometry_layout.addWidget(QLabel("Length:"))
            self.length_input = QLineEdit()
            self.length_input.setText("1.0")
            self.length_input.setMaximumWidth(100)
            self.length_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.length_input)

            self.geometry_layout.addWidget(QLabel("Width:"))
            self.width_input = QLineEdit()
            self.width_input.setText("1.0")
            self.width_input.setMaximumWidth(100)
            self.width_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.width_input)

        elif shape == 'rounded_rectangle':
            self.geometry_layout.addWidget(QLabel("Length:"))
            self.length_input = QLineEdit()
            self.length_input.setText("1.0")
            self.length_input.setMaximumWidth(100)
            self.length_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.length_input)

            self.geometry_layout.addWidget(QLabel("Width:"))
            self.width_input = QLineEdit()
            self.width_input.setText("1.0")
            self.width_input.setMaximumWidth(100)
            self.width_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.width_input)

            self.geometry_layout.addWidget(QLabel("Corner Radius:"))
            self.corner_radius_input = QLineEdit()
            self.corner_radius_input.setText("0.2")
            self.corner_radius_input.setMaximumWidth(100)
            self.corner_radius_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.corner_radius_input)

        elif shape == 'oblong':
            self.geometry_layout.addWidget(QLabel("Length:"))
            self.length_input = QLineEdit()
            self.length_input.setText("2.0")
            self.length_input.setMaximumWidth(100)
            self.length_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.length_input)

            self.geometry_layout.addWidget(QLabel("Width:"))
            self.width_input = QLineEdit()
            self.width_input.setText("1.0")
            self.width_input.setMaximumWidth(100)
            self.width_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.width_input)

            # ADD ROTATION CONTROL FOR OBLONG
            self.geometry_layout.addWidget(QLabel("Rotation:"))
            self.rotation_input = QLineEdit()
            self.rotation_input.setText("0")
            self.rotation_input.setMaximumWidth(80)
            self.rotation_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.rotation_input)
        
        elif shape == 'custom_polygon':
            self.geometry_layout.addWidget(QLabel("Custom Polygon (see below)"))

        # Add stretch to push everything to the left
        self.geometry_layout.addStretch()

    def get_data(self):
        data = {
            'shape': self.shape_combo.currentText(),
            'layer': self.layer_combo.currentText(),
            'x_offset': self.x_offset.text(),
            'y_offset': self.y_offset.text(),
            'offset_from': self.offset_from.currentText()
        }

        shape = self.shape_combo.currentText()

        if shape in ['rectangle', 'rounded_rectangle', 'oblong']:
            if hasattr(self, 'length_input'):
                data['length'] = self.length_input.text()
            if hasattr(self, 'width_input'):
                data['width'] = self.width_input.text()
            if shape == 'rounded_rectangle' and hasattr(self, 'corner_radius_input'):
                data['corner_radius'] = self.corner_radius_input.text()
            # ADD ROTATION FOR OBLONG
            if shape == 'oblong' and hasattr(self, 'rotation_input'):
                data['rotation'] = self.rotation_input.text()

        elif shape == 'custom_polygon':
            data['polygon_data'] = self.polygon_widget.get_data()

        return data

    def set_data(self, data):
        self.shape_combo.setCurrentText(data.get('shape', 'rectangle'))
        self.layer_combo.setCurrentText(data.get('layer', 'mask'))
        self.x_offset.setText(str(data.get('x_offset', '0')))
        self.y_offset.setText(str(data.get('y_offset', '0')))
        self.offset_from.setCurrentText(data.get('offset_from', 'origin'))

        # Set shape-specific data
        shape = data.get('shape', 'rectangle')

        if shape in ['rectangle', 'rounded_rectangle', 'oblong']:
            if hasattr(self, 'length_input'):
                self.length_input.setText(str(data.get('length', '1.0')))
            if hasattr(self, 'width_input'):
                self.width_input.setText(str(data.get('width', '1.0')))
            if shape == 'rounded_rectangle' and hasattr(self, 'corner_radius_input'):
                self.corner_radius_input.setText(str(data.get('corner_radius', '0.2')))

            # ADD ROTATION FOR OBLONG
            if shape == 'oblong' and hasattr(self, 'rotation_input'):
                self.rotation_input.setText(str(data.get('rotation', '0')))

        elif shape == 'custom_polygon':
            self.polygon_widget.set_data(data.get('polygon_data', {}))

class ThermalViaRow(QWidget):
    delete_requested = pyqtSignal(object)
    data_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # Create group box for this thermal via
        self.group_box = QGroupBox("Thermal Via Configuration")
        group_layout = QVBoxLayout(self.group_box)
        group_layout.setSpacing(5)

        # Row 1: Type and Geometry
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(10)

        # Type Group
        type_group = QGroupBox("Type")
        type_layout = QHBoxLayout(type_group)
        type_layout.setContentsMargins(5, 5, 5, 5)

        self.type_combo = QComboBox()
        self.type_combo.addItems(['grid_array', 'single'])
        type_layout.addWidget(self.type_combo)
        row1_layout.addWidget(type_group)

        # Geometry Group (Dynamic based on type)
        self.geometry_group = QGroupBox("Geometry")
        self.geometry_layout = QHBoxLayout(self.geometry_group)
        self.geometry_layout.setContentsMargins(5, 5, 5, 5)
        row1_layout.addWidget(self.geometry_group)

        # Actions Group
        actions_group = QGroupBox("Actions")
        actions_layout = QHBoxLayout(actions_group)
        actions_layout.setContentsMargins(5, 5, 5, 5)

        self.duplicate_btn = QPushButton("Duplicate")
        self.duplicate_btn.setMaximumWidth(80)
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setMaximumWidth(60)

        actions_layout.addWidget(self.duplicate_btn)
        actions_layout.addWidget(self.delete_btn)
        row1_layout.addWidget(actions_group)

        group_layout.addLayout(row1_layout)

        # Row 2: Position
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(10)

        # Position Group
        # Position Group
        position_group = QGroupBox("Position")
        position_layout = QGridLayout(position_group)
        position_layout.setContentsMargins(5, 5, 5, 5)
        
        position_layout.addWidget(QLabel("X Offset:"), 0, 0)
        self.x_offset = QLineEdit()
        self.x_offset.setText("0")
        self.x_offset.setMaximumWidth(100)
        position_layout.addWidget(self.x_offset, 0, 1)
        
        position_layout.addWidget(QLabel("Y Offset:"), 0, 2)
        self.y_offset = QLineEdit()
        self.y_offset.setText("0")
        self.y_offset.setMaximumWidth(100)
        position_layout.addWidget(self.y_offset, 0, 3)
        
        position_layout.addWidget(QLabel("Offset From:"), 1, 0)
        self.offset_from = QComboBox()
        self.offset_from.setMaximumWidth(100)
        position_layout.addWidget(self.offset_from, 1, 1, 1, 2)
        
        # ADD THIS NEW PIN NUMBER FIELD:
        position_layout.addWidget(QLabel("Via Pin:"), 1, 3)
        self.pin_number = QLineEdit()
        self.pin_number.setMaximumWidth(50)
        position_layout.addWidget(self.pin_number, 1, 4)
        
        row2_layout.addWidget(position_group)
        group_layout.addLayout(row2_layout)

        main_layout.addWidget(self.group_box)
        self.setLayout(main_layout)

        # Initialize geometry inputs
        self.update_geometry_inputs()

    def connect_signals(self):
        self.type_combo.currentTextChanged.connect(self.update_geometry_inputs)
        self.type_combo.currentTextChanged.connect(self.data_changed.emit)
        self.delete_btn.clicked.connect(lambda: self.delete_requested.emit(self))

        # Connect all input signals
        self.x_offset.textChanged.connect(self.data_changed.emit)
        self.y_offset.textChanged.connect(self.data_changed.emit)
        self.offset_from.currentTextChanged.connect(self.data_changed.emit)
        
        # ADD THESE NEW SIGNAL CONNECTIONS:
        self.pin_number.textChanged.connect(self.update_offset_from_options)
        self.pin_number.textChanged.connect(self.data_changed.emit)

    def update_offset_from_options(self):
        """Update offset_from options when pin number changes"""
        parent_designer = self.get_parent_designer()
        if parent_designer:
            parent_designer.update_all_offset_dropdowns()

    def get_parent_designer(self):
        """Find the parent FootprintDesigner instance"""
        parent = self.parent()
        while parent:
            if hasattr(parent, 'thermal_via_rows'):
                return parent
            parent = parent.parent()
        return None


    def update_geometry_inputs(self):
        # Clear existing geometry inputs
        for i in reversed(range(self.geometry_layout.count())):
            item = self.geometry_layout.itemAt(i)
            if item:
                widget = item.widget()
                if widget:
                    widget.setParent(None)

        via_type = self.type_combo.currentText()

        if via_type == 'single':
            self.geometry_layout.addWidget(QLabel("Via Diameter:"))
            self.via_diameter_input = QLineEdit()
            self.via_diameter_input.setText("0.2")
            self.via_diameter_input.setMaximumWidth(100)
            self.via_diameter_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.via_diameter_input)

            self.geometry_layout.addWidget(QLabel("Drill Diameter:"))
            self.drill_diameter_input = QLineEdit()
            self.drill_diameter_input.setText("0.1")
            self.drill_diameter_input.setMaximumWidth(100)
            self.drill_diameter_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.drill_diameter_input)

        elif via_type == 'grid_array':
            self.geometry_layout.addWidget(QLabel("Rows:"))
            self.rows_input = QLineEdit()
            self.rows_input.setText("2")
            self.rows_input.setMaximumWidth(80)
            self.rows_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.rows_input)

            self.geometry_layout.addWidget(QLabel("Columns:"))
            self.columns_input = QLineEdit()
            self.columns_input.setText("2")
            self.columns_input.setMaximumWidth(80)
            self.columns_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.columns_input)

            self.geometry_layout.addWidget(QLabel("Row Spacing:"))
            self.row_spacing_input = QLineEdit()
            self.row_spacing_input.setText("1.0")
            self.row_spacing_input.setMaximumWidth(100)
            self.row_spacing_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.row_spacing_input)

            self.geometry_layout.addWidget(QLabel("Col Spacing:"))
            self.col_spacing_input = QLineEdit()
            self.col_spacing_input.setText("1.0")
            self.col_spacing_input.setMaximumWidth(100)
            self.col_spacing_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.col_spacing_input)

            self.geometry_layout.addWidget(QLabel("Via Diameter:"))
            self.via_diameter_input = QLineEdit()
            self.via_diameter_input.setText("0.2")
            self.via_diameter_input.setMaximumWidth(100)
            self.via_diameter_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.via_diameter_input)

            self.geometry_layout.addWidget(QLabel("Drill Diameter:"))
            self.drill_diameter_input = QLineEdit()
            self.drill_diameter_input.setText("0.1")
            self.drill_diameter_input.setMaximumWidth(100)
            self.drill_diameter_input.textChanged.connect(self.data_changed.emit)
            self.geometry_layout.addWidget(self.drill_diameter_input)

        # Add stretch to push everything to the left
        self.geometry_layout.addStretch()


        

    def get_data(self):
        data = {
            'type': self.type_combo.currentText(),
            'x_offset': self.x_offset.text(),
            'y_offset': self.y_offset.text(),
            'offset_from': self.offset_from.currentText(),
            'pin_number': self.pin_number.text()  # ADD THIS LINE
        }

        via_type = self.type_combo.currentText()

        if via_type == 'single':
            if hasattr(self, 'via_diameter_input'):
                data['via_diameter'] = self.via_diameter_input.text()
            if hasattr(self, 'drill_diameter_input'):
                data['drill_diameter'] = self.drill_diameter_input.text()

        elif via_type == 'grid_array':
            if hasattr(self, 'rows_input'):
                data['rows'] = self.rows_input.text()
            if hasattr(self, 'columns_input'):
                data['columns'] = self.columns_input.text()
            if hasattr(self, 'row_spacing_input'):
                data['row_spacing'] = self.row_spacing_input.text()
            if hasattr(self, 'col_spacing_input'):
                data['col_spacing'] = self.col_spacing_input.text()
            if hasattr(self, 'via_diameter_input'):
                data['via_diameter'] = self.via_diameter_input.text()
            if hasattr(self, 'drill_diameter_input'):
                data['drill_diameter'] = self.drill_diameter_input.text()

        return data

    def set_data(self, data):
        self.type_combo.setCurrentText(data.get('type', 'single'))
        self.x_offset.setText(str(data.get('x_offset', '0')))
        self.y_offset.setText(str(data.get('y_offset', '0')))
        self.offset_from.setCurrentText(data.get('offset_from', 'origin'))
        self.pin_number.setText(str(data.get('pin_number', 'V1')))  # ADD THIS LINE

        # Set type-specific data
        via_type = data.get('type', 'single')

        if via_type == 'single':
            if hasattr(self, 'via_diameter_input'):
                self.via_diameter_input.setText(str(data.get('via_diameter', '0.2')))
            if hasattr(self, 'drill_diameter_input'):
                self.drill_diameter_input.setText(str(data.get('drill_diameter', '0.1')))

        elif via_type == 'grid_array':
            if hasattr(self, 'rows_input'):
                self.rows_input.setText(str(data.get('rows', '2')))
            if hasattr(self, 'columns_input'):
                self.columns_input.setText(str(data.get('columns', '2')))
            if hasattr(self, 'row_spacing_input'):
                self.row_spacing_input.setText(str(data.get('row_spacing', '1.0')))
            if hasattr(self, 'col_spacing_input'):
                self.col_spacing_input.setText(str(data.get('col_spacing', '1.0')))
            if hasattr(self, 'via_diameter_input'):
                self.via_diameter_input.setText(str(data.get('via_diameter', '0.2')))
            if hasattr(self, 'drill_diameter_input'):
                self.drill_diameter_input.setText(str(data.get('drill_diameter', '0.1')))

# Add this class first (if not already present)
class LocalStandardsManager:
    """Manages local storage of standards"""
    
    STANDARDS_FILE = "standards_local.json"
    
    @staticmethod
    def get_standards_path():
        """Get the path for local standards file"""
        home_dir = os.path.expanduser("~")
        settings_dir = os.path.join(home_dir, ".libsienna")
        os.makedirs(settings_dir, exist_ok=True)
        return os.path.join(settings_dir, LocalStandardsManager.STANDARDS_FILE)
    
    @staticmethod
    def load_local_standards():
        """Load standards from local JSON file"""
        standards_path = LocalStandardsManager.get_standards_path()
        try:
            if os.path.exists(standards_path):
                with open(standards_path, 'r') as f:
                    data = json.load(f)
                    return data.get('standards', [])
            else:
                return []
        except Exception as e:
            print(f"Error loading local standards: {e}")
            return []
    
    @staticmethod
    def save_local_standards(standards):
        """Save standards to local JSON file"""
        standards_path = LocalStandardsManager.get_standards_path()
        try:
            data = {'standards': standards}
            with open(standards_path, 'w') as f:
                json.dump(data, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving local standards: {e}")
            return False
    
    @staticmethod
    def add_or_update_standard(standard):
        """Add or update a single standard in local storage"""
        standards = LocalStandardsManager.load_local_standards()
        
        # Check if standard already exists
        existing_index = None
        for i, s in enumerate(standards):
            if s.get('name') == standard.get('name'):
                existing_index = i
                break
        
        if existing_index is not None:
            standards[existing_index] = standard
        else:
            standards.append(standard)
        
        return LocalStandardsManager.save_local_standards(standards)


class SettingsPanel(QDialog):
    settings_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(1200, 700)
        
        # Authentication - MUST be initialized
        self.token = None
        self.user_role = None
        self.username = None
        self.is_admin_manager = False
        self.current_preset = None
        self.server_url = 'http://localhost:5000/api'
        self.parent_server = None
        self.parent_window = parent
        
        # Store all field widgets for dynamic show/hide
        self.field_widgets = {}
        
        # Library database attributes
        self.all_footprints = []
        self.filtered_footprints = []
        
        print("SettingsPanel initialized - waiting for authentication")
        
        self.setup_ui()
        self.setup_styling()
        
        # Load from local on startup
        self.load_from_local()
    
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #555;
                background-color: #2b2b2b;
            }
            QTabBar::tab {
                background-color: #3c3c3c;
                color: #ffffff;
                padding: 8px 20px;
                border: 1px solid #555;
            }
            QTabBar::tab:selected {
                background-color: #0d47a1;
                color: #ffffff;
            }
            QTabBar::tab:hover {
                background-color: #4a4a4a;
            }
        """)
        
        # Tab 1: Standard Settings
        standard_tab = self.create_standard_tab()
        self.tab_widget.addTab(standard_tab, "Standard")
        
        # Tab 2: Library Database
        library_tab = self.create_library_database_tab()
        self.tab_widget.addTab(library_tab, "Library Database")
        
        layout.addWidget(self.tab_widget)
        
        # Don't call update_permissions here - will be called after authentication
    

    def set_authentication(self, token, role, username):
        """Set authentication credentials"""
        self.token = token
        self.user_role = role
        self.username = username
        self.is_admin_manager = role in ['admin', 'manager']
        print(f"SettingsPanel.set_authentication: token={bool(token)}, role={role}, is_admin_manager={self.is_admin_manager}")
        
        # Update UI permissions
        self.update_permissions()
    
    def update_permissions(self):
        """Update UI based on user permissions"""
        if not hasattr(self, 'create_new_btn'):
            return  # UI not yet created
        
        enabled = self.is_admin_manager
        
        # Button permissions
        self.create_new_btn.setEnabled(enabled)
        self.delete_btn.setEnabled(False)
        self.save_btn.setEnabled(enabled)
        self.fetch_btn.setEnabled(True)  # Always enabled
        
        # Disable all input fields for non-admin/manager
        if hasattr(self, 'standard_name_input'):
            self.standard_name_input.setEnabled(enabled)
        if hasattr(self, 'tool_combo'):
            self.tool_combo.setEnabled(enabled)
        
        
        # Disable all field widgets
        for widget in self.field_widgets.values():
            widget.setEnabled(enabled)
        
        status = f"Ready - {self.user_role.capitalize()} access" if self.is_admin_manager else "Ready - Read-only"
        self.status_label.setText(status)
        print(f"Permissions updated: inputs enabled={enabled}")

    def load_from_local(self):
        """Load standards from local storage"""
        standards = LocalStandardsManager.load_local_standards()
        self.standards_list.clear()
        for standard in standards:
            item = QListWidgetItem(standard.get('name', 'Unnamed'))
            item.setData(Qt.ItemDataRole.UserRole, standard)
            self.standards_list.addItem(item)

    def fetch_from_server(self):
        """Fetch standards from server"""
        if not self.parent_server:
            QMessageBox.warning(self, 'Error', 'Server not configured')
            return

        self.status_label.setText("Fetching from server...")
        success, result = self.parent_server.get_standards()

        if success:
            # Save to local
            LocalStandardsManager.save_local_standards(result)
            self.load_from_local()
            self.status_label.setText("Fetched from server")
            QMessageBox.information(self, 'Success', 'Standards fetched from server!')
        else:
            self.status_label.setText("Fetch failed")
            QMessageBox.warning(self, 'Error', f'Failed to fetch: {result}')

    def upload_to_server(self):
        """Upload current standard to server"""
        if not self.is_admin_manager:
            QMessageBox.warning(self, 'Permission Denied', 
                              'Only admin/manager can upload standards')
            return

        standard_name = self.standard_name_input.text().strip()
        if not standard_name:
            QMessageBox.warning(self, 'Error', 'Enter a standard name')
            return

        if not self.parent_server:
            QMessageBox.warning(self, 'Error', 'Server not configured')
            return

        # Build configuration
        config = self.get_settings()
        config['tool'] = self.tool_combo.currentText()
        config['standard_name'] = standard_name

        self.status_label.setText("Uploading...")
        success, result = self.parent_server.save_standard(standard_name, config)

        if success:
            self.status_label.setText("Uploaded to server!")
            QMessageBox.information(self, 'Success', 'Standard uploaded to server!')
        else:
            self.status_label.setText("Upload failed")
            QMessageBox.warning(self, 'Error', f'Upload failed: {result}')

    def create_new_standard(self):
        """Create a new standard"""
        if not self.is_admin_manager:
            QMessageBox.warning(self, 'Permission Denied',
                              'Only admin/manager can create standards')
            return

        self.current_preset = None
        self.standard_name_input.clear()
        self.on_tool_changed()  # Reset to default fields
        self.delete_btn.setEnabled(False)
        self.status_label.setText("Creating new standard")

    def create_standard_tab(self):
        """Create the standard configuration tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Splitter for list + config
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Standards list
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Configuration
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # Set stretch factors
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        
        layout.addWidget(splitter)
        
        return widget  # ← MUST return the widget!

    def create_left_panel(self):
        """Create left panel with standards list"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Buttons
        btn_layout = QVBoxLayout()

        self.create_new_btn = QPushButton("Create New Standard")
        self.create_new_btn.clicked.connect(self.create_new_standard)
        btn_layout.addWidget(self.create_new_btn)

        self.fetch_btn = QPushButton("Fetch from Server")
        self.fetch_btn.clicked.connect(self.fetch_from_server)
        btn_layout.addWidget(self.fetch_btn)

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #aaa; font-size: 10px;")
        btn_layout.addWidget(self.status_label)

        layout.addLayout(btn_layout)

        # Standards list
        list_label = QLabel("Saved Standards:")
        list_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(list_label)

        self.standards_list = QListWidget()
        self.standards_list.itemClicked.connect(self.on_standard_selected)
        layout.addWidget(self.standards_list)

        # Delete button
        self.delete_btn = QPushButton("Delete Standard")
        self.delete_btn.clicked.connect(self.delete_standard)
        self.delete_btn.setEnabled(False)
        layout.addWidget(self.delete_btn)

        return panel

    def create_right_panel(self):
        """Create right panel with dynamic tool-specific settings"""
        panel = QWidget()
        main_layout = QVBoxLayout(panel)

        # Tool selection dropdown
        tool_layout = QHBoxLayout()
        tool_layout.addWidget(QLabel("Tool:"))
        self.tool_combo = QComboBox()
        self.tool_combo.addItems(["Altium", "Allegro", "PADS", "Xpedition"])
        self.tool_combo.currentTextChanged.connect(self.on_tool_changed)
        tool_layout.addWidget(self.tool_combo)
        tool_layout.addStretch()
        main_layout.addLayout(tool_layout)

        # Standard name input
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Standard Name:"))
        self.standard_name_input = QLineEdit()
        self.standard_name_input.setPlaceholderText("Enter standard name...")
        name_layout.addWidget(self.standard_name_input)
        main_layout.addLayout(name_layout)

        # Settings container (dynamic based on tool selection)
        self.settings_container = QWidget()
        self.settings_layout = QVBoxLayout(self.settings_container)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.settings_container)
        main_layout.addWidget(scroll)

        # Buttons
        btn_layout = QHBoxLayout()

        self.save_btn = QPushButton("Save Standard")
        self.save_btn.clicked.connect(self.save_standard)
        btn_layout.addWidget(self.save_btn)

        self.upload_btn = QPushButton("Upload to Server")
        self.upload_btn.clicked.connect(self.upload_to_server)
        btn_layout.addWidget(self.upload_btn)

        main_layout.addLayout(btn_layout)

        # Initialize with first tool's fields
        self.on_tool_changed()

        return panel

    def on_tool_changed(self):
        """Handle tool selection change - load appropriate template"""
        tool = self.tool_combo.currentText()

        # Clear existing fields
        while self.settings_layout.count():
            item = self.settings_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.field_widgets = {}

        # Load tool-specific input template
        if tool == "Altium":
            self.altium_standard_input()
        elif tool == "Allegro":
            self.allegro_standard_input()
        elif tool == "PADS":
            self.pads_standard_input()
        elif tool == "Xpedition":
            self.xpedition_standard_input()

    def altium_standard_input(self):
        """Create Altium-specific input fields"""
        # Body Settings
        self.create_settings_group("Body Settings", [
            ("body_line_width", "Body Line Width (mm)", "0.05"),
            ("bodylayer", "Body Layer", "dropdown_body_altium")
        ])

        # Courtyard Settings
        self.create_courtyard_settings("Altium")

        # Silkscreen Settings
        self.create_settings_group("Silkscreen Settings", [
            ("silkscreen_airgap", "Silkscreen Air Gap (mm)", "0.1"),
            ("silkscreen_line_width", "Silkscreen Line Width (mm)", "0.15"),
            ("silkscreen_follow_chamfer", "Follow Chamfer", "checkbox")
        ])

        # Padstack Name Text Settings
        self.create_settings_group("Padstack Name Text Settings", [
            ("text_height", "Text Height (mm)", "1.0"),
            ("text_width", "Text Width (mm)", "1.0"),
            ("text_line_width", "Text Line Width (mm)", "0.15"),
            ("textfontstyle", "Font Style", "dropdown_font"),
            ("textlayer", "Text Layer", "dropdown_text_altium")
        ])

        # Fiducial Settings
        self.create_settings_group("Fiducial Settings", [
            ("fiducialdiameter", "Fiducial Diameter (mm)", "1.0"),
            ("fiducialmaskopening", "Mask Opening (mm)", "2.0"),
            ("fiducialkeepoutdiameter", "Keepout Diameter (mm)", "3.0"),
            ("fiducialkeepoutlayer", "Keepout Layer", "dropdown_fiducial_altium"),
            ("fiducialxoffset", "X Offset (mm)", "0"),
            ("fiducialyoffset", "Y Offset (mm)", "0")
        ])

        self.settings_layout.addStretch()

    def allegro_standard_input(self):
        """Create Allegro-specific input fields"""
        # Body Settings
        self.create_settings_group("Body Settings", [
            ("body_line_width", "Body Line Width (mm)", "0.05"),
            ("bodylayer", "Body Layer", "dropdown_body_allegro")
        ])

        # Courtyard Settings
        self.create_courtyard_settings("Allegro")

        # NoProb Settings
        self.create_settings_group("NoProb Settings", [
            ("noprobtop", "NoProb Top", "checkbox"),
            ("noprobbottom", "NoProb Bottom", "checkbox"),
            ("noprobexpansion", "NoProb Expansion (mm)", "0.51"),
            ("noproblinewidth", "NoProb Line Width (mm)", "0.1")
        ])

        # DFA Bond Settings
        self.create_settings_group("DFA Bond Settings", [
            ("dfabondtop", "DFA Bond Top", "checkbox"),
            ("dfabondbottom", "DFA Bond Bottom", "checkbox"),
            ("dfabondexpansion", "DFA Bond Expansion (mm)", "0.25")
        ])

        # Silkscreen Settings
        self.create_settings_group("Silkscreen Settings", [
            ("silkscreen_airgap", "Silkscreen Air Gap (mm)", "0.1"),
            ("silkscreen_line_width", "Silkscreen Line Width (mm)", "0.15"),
            ("silkscreen_follow_chamfer", "Follow Chamfer", "checkbox")
        ])

        # Padstack Name Text Settings
        self.create_settings_group("Padstack Name Text Settings", [
            ("text_height", "Text Height (mm)", "0.5"),
            ("text_width", "Text Width (mm)", "0.1"),
            ("text_line_width", "Text Line Width (mm)", "1.8"),
            ("textfontstyle", "Font Style", "dropdown_font"),
            ("textlayer", "Text Layer", "dropdown_text_allegro")
        ])

        # Keepout Settings
        self.create_settings_group("Keepout Settings", [
            ("viakeepoutexpansion", "Via Keepout Expansion (mm)", "0.1"),
            ("packagekeepoutexpansion", "Package Keepout Expansion (mm)", "0.25"),
            ("routekeepoutexpansion", "Route Keepout Expansion (mm)", "0.15")
        ])

        self.settings_layout.addStretch()

    def pads_standard_input(self):
        """Create PADS-specific input fields"""
        # Body Settings
        self.create_settings_group("Body Settings", [
            ("body_line_width", "Body Line Width (mm)", "0.05"),
            ("bodylayer", "Body Layer", "dropdown_body_pads")
        ])

        # Courtyard Settings
        self.create_courtyard_settings("PADS")

        # Silkscreen Settings
        self.create_settings_group("Silkscreen Settings", [
            ("silkscreen_airgap", "Silkscreen Air Gap (mm)", "0.1"),
            ("silkscreen_line_width", "Silkscreen Line Width (mm)", "0.15"),
            ("silkscreen_follow_chamfer", "Follow Chamfer", "checkbox")
        ])

        # Padstack Name Text Settings
        self.create_settings_group("Padstack Name Text Settings", [
            ("text_height", "Text Height (mm)", "1.0"),
            ("text_width", "Text Width (mm)", "1.0"),
            ("text_line_width", "Text Line Width (mm)", "0.15"),
            ("textfontstyle", "Font Style", "dropdown_font"),
            ("textlayer", "Text Layer", "dropdown_text_pads")
        ])

        self.settings_layout.addStretch()

    def xpedition_standard_input(self):
        """Create Xpedition-specific input fields"""
        # Body Settings
        self.create_settings_group("Body Settings", [
            ("body_line_width", "Body Line Width (mm)", "0.05"),
            ("bodylayer", "Body Layer", "dropdown_body_xpedition")
        ])

        # Courtyard Settings
        self.create_courtyard_settings("Xpedition")

        # Silkscreen Settings
        self.create_settings_group("Silkscreen Settings", [
            ("silkscreen_airgap", "Silkscreen Air Gap (mm)", "0.1"),
            ("silkscreen_line_width", "Silkscreen Line Width (mm)", "0.15"),
            ("silkscreen_follow_chamfer", "Follow Chamfer", "checkbox")
        ])

        # Padstack Name Text Settings
        self.create_settings_group("Padstack Name Text Settings", [
            ("text_height", "Text Height (mm)", "1.0"),
            ("text_width", "Text Width (mm)", "1.0"),
            ("text_line_width", "Text Line Width (mm)", "0.15"),
            ("textfontstyle", "Font Style", "dropdown_font"),
            ("textlayer", "Text Layer", "dropdown_text_xpedition")
        ])

        self.settings_layout.addStretch()

    def create_settings_group(self, group_name, fields):
        """Helper method to create a settings group with fields"""
        group = QGroupBox(group_name)
        group_layout = QGridLayout(group)
        group_layout.setSpacing(10)
        
        row = 0
        for field_data in fields:
            field_name = field_data[0]
            label_text = field_data[1]
            widget_type = field_data[2] if len(field_data) > 2 else ""
            
            # Create label
            label = QLabel(label_text + ":")
            group_layout.addWidget(label, row, 0)
            
            # Create appropriate widget based on type
            widget = None
            
            if widget_type == "checkbox":
                widget = QCheckBox()
            
            elif widget_type.startswith("dropdown_body_"):
                # Extract tool name from widget_type
                tool = widget_type.replace("dropdown_body_", "")
                tool = tool.capitalize()  # Ensure proper case (altium -> Altium)
                widget = self.create_layer_dropdown("Body", tool)
            
            elif widget_type.startswith("dropdown_text_"):
                tool = widget_type.replace("dropdown_text_", "")
                tool = tool.capitalize()
                widget = self.create_layer_dropdown("Text", tool)
            
            elif widget_type.startswith("dropdown_fiducial_"):
                tool = widget_type.replace("dropdown_fiducial_", "")
                tool = tool.capitalize()
                widget = self.create_layer_dropdown("Fiducial", tool)
            
            elif widget_type == "dropdown_font":
                widget = self.create_font_style_dropdown()
            
            else:
                # Default to QLineEdit
                widget = QLineEdit()
                if widget_type:  # If default value provided
                    widget.setText(widget_type)
                    widget.setPlaceholderText(widget_type)
                widget.setStyleSheet("QLineEdit { background-color: #3c3c3c; color: white; padding: 5px; }")
            
            if widget:
                group_layout.addWidget(widget, row, 1)
                self.field_widgets[field_name] = widget
            
            row += 1
        
        self.settings_layout.addWidget(group)

    def create_courtyard_settings(self, tool):
        """Create courtyard settings - simplified without dynamic expansion groups"""
        group = QGroupBox("Courtyard Settings")
        group_layout = QGridLayout(group)
        group_layout.setSpacing(10)

        row = 0

        # SMD Courtyard Expansion
        group_layout.addWidget(QLabel("SMD Courtyard Expansion (mm):"), row, 0)
        self.field_widgets["smdcourtyardexpansion"] = QLineEdit("0.25")
        self.field_widgets["smdcourtyardexpansion"].setStyleSheet(
            "QLineEdit { background-color: #3c3c3c; color: white; padding: 5px; }"
        )
        group_layout.addWidget(self.field_widgets["smdcourtyardexpansion"], row, 1)
        row += 1

        # BGA/PTH Courtyard Expansion
        group_layout.addWidget(QLabel("BGA/PTH Courtyard Expansion (mm):"), row, 0)
        self.field_widgets["bgapthcourtyardexpansion"] = QLineEdit("0.5")
        self.field_widgets["bgapthcourtyardexpansion"].setStyleSheet(
            "QLineEdit { background-color: #3c3c3c; color: white; padding: 5px; }"
        )
        group_layout.addWidget(self.field_widgets["bgapthcourtyardexpansion"], row, 1)
        row += 1

        # Courtyard Line Width
        group_layout.addWidget(QLabel("Courtyard Line Width (mm):"), row, 0)
        self.field_widgets["courtyardlinewidth"] = QLineEdit("0.1")
        self.field_widgets["courtyardlinewidth"].setStyleSheet(
            "QLineEdit { background-color: #3c3c3c; color: white; padding: 5px; }"
        )
        group_layout.addWidget(self.field_widgets["courtyardlinewidth"], row, 1)
        row += 1

        # Courtyard Layer
        group_layout.addWidget(QLabel("Courtyard Layer:"), row, 0)
        self.field_widgets["courtyardlayer"] = self.create_layer_dropdown("Courtyard", tool)
        group_layout.addWidget(self.field_widgets["courtyardlayer"], row, 1)
        row += 1

        self.settings_layout.addWidget(group)

    def create_layer_dropdown(self, layer_type, tool):
        """Create a dropdown for layer selection - tool-specific layers"""
        combo = QComboBox()
        
        
        # Normalize tool name to match exactly
        tool = str(tool).strip()
        
        # Tool-specific layer names
        if tool == "Altium":
            if layer_type == "Body":
                combo.addItems(["Top Assembly", "Bottom Assembly", "Mechanical 1", "Mechanical 13"])
            elif layer_type == "Courtyard":
                combo.addItems(["Mechanical 15", "Mechanical 16", "Top Courtyard", "Bottom Courtyard"])
            elif layer_type == "Text":
                combo.addItems(["Top Overlay", "Bottom Overlay", "Top Assembly", "Bottom Assembly"])
            elif layer_type == "Fiducial":
                combo.addItems(["Top Layer", "Bottom Layer", "All Layers", "Mechanical 1"])
        
        elif tool == "Allegro":
            if layer_type == "Body":
                combo.addItems(["Package Geometry/Assembly_Top", "Package Geometry/Assembly_Bottom", 
                            "Package Geometry/Silkscreen_Top", "Board Geometry/Outline"])
            elif layer_type == "Courtyard":
                combo.addItems(["Package Geometry/Courtyard_Top", "Package Geometry/Courtyard_Bottom",
                            "Package Keepout/Assembly_Top", "Package Keepout/Assembly_Bottom"])
            elif layer_type == "Text":
                combo.addItems(["Package Geometry/Silkscreen_Top", "Package Geometry/Silkscreen_Bottom",
                            "Package Geometry/Assembly_Top", "Package Geometry/Assembly_Bottom"])
            elif layer_type == "Fiducial":
                combo.addItems(["Package Keepout/All", "Board Geometry/Outline"])
        
        elif tool == "PADS":
            if layer_type == "Body":
                combo.addItems(["Assembly_Top", "Assembly_Bottom", "Silkscreen_Top", "Board_Outline"])
            elif layer_type == "Courtyard":
                combo.addItems(["Courtyard_Top", "Courtyard_Bottom", "Package_Keepout_Top"])
            elif layer_type == "Text":
                combo.addItems(["Silkscreen_Top", "Silkscreen_Bottom", "Assembly_Top", "Assembly_Bottom"])
            elif layer_type == "Fiducial":
                combo.addItems(["Top", "Bottom", "All_Layers"])
        
        elif tool == "Xpedition":
            if layer_type == "Body":
                combo.addItems(["ASSEMBLY_TOP", "ASSEMBLY_BOTTOM", "SILKSCREEN_TOP", "BOARD_OUTLINE"])
            elif layer_type == "Courtyard":
                combo.addItems(["COURTYARD_TOP", "COURTYARD_BOTTOM", "PKG_KEEPOUT_TOP"])
            elif layer_type == "Text":
                combo.addItems(["SILKSCREEN_TOP", "SILKSCREEN_BOTTOM", "ASSEMBLY_TOP", "ASSEMBLY_BOTTOM"])
            elif layer_type == "Fiducial":
                combo.addItems(["TOP", "BOTTOM", "ALL_LAYERS"])
        
        else:
            # Fallback - add generic items
            print(f"WARNING: Unknown tool '{tool}', using generic layers")
            combo.addItems(["Layer 1", "Layer 2", "Layer 3"])
        
        combo.setStyleSheet("""
            QComboBox {
                background-color: #3c3c3c;
                color: white;
                padding: 5px;
                border: 1px solid #555;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        
        return combo


    def create_font_style_dropdown(self):
        """Create a dropdown for font style selection"""
        combo = QComboBox()
        combo.addItems(["TrueType", "Stroke", "Sans Serif", "Serif"])
        combo.setStyleSheet("""
            QComboBox {
                background-color: #3c3c3c;
                color: white;
                padding: 5px;
                border: 1px solid #555;
            }
        """)
        return combo

    def get_default_value(self, field_name):
        """Get default value for a field"""
        defaults = {
            'body_line_width': '0.05',
            'silkscreen_airgap': '0.1',
            'silkscreen_line_width': '0.15',
            'smdcourtyardexpansion': '0.25',
            'bgapthcourtyardexpansion': '0.5',
            'courtyardlinewidth': '0.1',
            'text_height': '1.0',
            'text_width': '1.0',
            'text_line_width': '0.15',
            'fiducialdiameter': '1.0',
            'fiducialmaskopening': '2.0',
            'fiducialkeepoutdiameter': '3.0',
            'fiducialxoffset': '0',
            'fiducialyoffset': '0',
            'noprobexpansion': '0.51',
            'noproblinewidth': '0.1',
            'dfabondexpansion': '0.25',
            'viakeepoutexpansion': '0.1',
            'packagekeepoutexpansion': '0.25',
            'routekeepoutexpansion': '0.15'
        }
        return defaults.get(field_name, '')

    def save_to_local(self, standard):
        """Save standard to local storage"""
        try:
            standards = LocalStandardsManager.load_local_standards()
            # Remove existing standard with same name
            standards = [s for s in standards if s.get('name') != standard['name']]
            standards.append(standard)
            LocalStandardsManager.save_local_standards(standards)
            self.load_from_local()
            return True
        except Exception as e:
            print(f"Error saving to local: {e}")
            return False

    def save_standard(self):
        """Save standard locally and optionally upload to server"""
        if not self.is_admin_manager:
            QMessageBox.warning(self, 'Permission Denied',
                            'Only admin/manager can save standards')
            return

        standard_name = self.standard_name_input.text().strip()
        if not standard_name:
            QMessageBox.warning(self, 'Error', 'Please enter a standard name')
            return

        # Build complete configuration
        config = {}

        # Add all field values
        for field, widget in self.field_widgets.items():
            if isinstance(widget, QCheckBox):
                config[field] = widget.isChecked()
            elif isinstance(widget, QComboBox):
                config[field] = widget.currentText() or self.get_default_value(field)
            elif isinstance(widget, QLineEdit):
                config[field] = widget.text() or self.get_default_value(field)
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                config[field] = widget.value()
            else:
                config[field] = self.get_default_value(field)

        # Create standard object with proper structure
        standard = {
            'name': standard_name,  # ← Standard name at root level
            'tool': self.tool_combo.currentText(),  # ← Tool at root level
            'data': config  # ← All field data in 'data' key
        }

        try:
            # Save to local JSON first
            if self.save_to_local(standard):
                self.status_label.setText("Saved to local")
                QMessageBox.information(self, 'Success',
                                    f'Standard "{standard_name}" saved locally!')
            else:
                QMessageBox.critical(self, 'Error', 'Failed to save locally')
        except Exception as e:
            self.status_label.setText("Save error")
            QMessageBox.critical(self, 'Error', f'Save error: {str(e)}')

        print(f"Saved standard: name='{standard_name}', tool='{self.tool_combo.currentText()}'")

    def delete_standard(self):
        """Delete selected standard"""
        if not self.is_admin_manager:
            QMessageBox.warning(self, 'Permission Denied',
                              'Only admin/manager can delete standards')
            return

        current_item = self.standards_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, 'Error', 'Select a standard to delete')
            return

        standard_name = current_item.text()
        reply = QMessageBox.question(self, 'Confirm Delete',
                                    f'Delete standard "{standard_name}"?',
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            # Remove from local storage
            standards = LocalStandardsManager.load_local_standards()
            standards = [s for s in standards if s.get('name') != standard_name]
            LocalStandardsManager.save_local_standards(standards)

            # Reload list
            self.load_from_local()
            self.status_label.setText("Deleted from local")
            QMessageBox.information(self, 'Success', 'Standard deleted from local storage')

    def on_standard_selected(self, item):
        """Load standard for editing"""
        standard = item.data(Qt.ItemDataRole.UserRole)

        # Set the current preset name
        self.current_preset = standard.get('name', '')

        # Load the standard name into the input field
        if self.current_preset:
            self.standard_name_input.setText(self.current_preset)

        # Load the tool selection
        tool = standard.get('tool', 'Altium')
        self.tool_combo.setCurrentText(tool)

        # Load the configuration data
        config = standard.get('data', {})
        self.load_settings_from_config(config)

        # Enable delete button for admin/manager
        self.delete_btn.setEnabled(self.is_admin_manager)

        # Update status
        self.status_label.setText(f"Loaded: {self.current_preset}")

        print(f"Loaded standard: name='{self.current_preset}', tool='{tool}'")

    def load_settings_from_config(self, config):
        """Load settings from configuration"""
        if not config:
            return

        try:
            # Load field values
            for field, widget in self.field_widgets.items():
                if field in config:
                    value = config[field]

                    if isinstance(widget, QCheckBox):
                        # Handle checkbox
                        widget.setChecked(bool(value))

                    elif isinstance(widget, QComboBox):
                        # Handle combobox
                        widget.setCurrentText(str(value))

                    elif isinstance(widget, QLineEdit):
                        # Handle line edit
                        widget.setText(str(value))

                    elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                        # Handle spin boxes
                        widget.setValue(value)

            print(f"Loaded {len(config)} settings from config")

        except Exception as e:
            print(f"Error loading settings: {e}")


    def get_settings(self):
        """Get all current settings"""
        settings = {}
        for field, widget in self.field_widgets.items():
            try:
                if isinstance(widget, QCheckBox):
                    settings[field] = widget.isChecked()
                elif isinstance(widget, QComboBox):
                    settings[field] = widget.currentText()
                elif isinstance(widget, QLineEdit):
                    settings[field] = widget.text() or self.get_default_value(field)
                elif isinstance(widget, QSpinBox) or isinstance(widget, QDoubleSpinBox):
                    settings[field] = widget.value()
                else:
                    settings[field] = self.get_default_value(field)
            except RuntimeError:
                settings[field] = self.get_default_value(field)
        return settings

    def set_settings(self, settings):
        """Set all settings from dictionary"""
        if not settings:
            return

        try:
            tool = settings.get('tool', 'Altium')
            self.tool_combo.setCurrentText(tool)
            self.standard_name_input.setText(settings.get('standard_name', ''))
        except Exception as e:
            print(f"Error in set_settings: {e}")

    def setup_styling(self):
        """Apply dark theme styling"""
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QLineEdit {
                background-color: #3c3c3c;
                border: 1px solid #555;
                padding: 5px;
                border-radius: 3px;
                color: #ffffff;
            }
            QLineEdit:focus {
                border: 1px solid #0d47a1;
            }
            QPushButton {
                background-color: #4a4a4a;
                border: 1px solid #666;
                padding: 8px 15px;
                border-radius: 3px;
                color: #ffffff;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #666;
            }
            QComboBox {
                background-color: #3c3c3c;
                border: 1px solid #555;
                padding: 5px;
                border-radius: 3px;
                color: #ffffff;
            }
            QListWidget {
                background-color: #1e1e1e;
                border: 1px solid #555;
                color: #ffffff;
            }
            QListWidget::item:selected {
                background-color: #0d47a1;
            }
            QListWidget::item:hover {
                background-color: #3c3c3c;
            }
            QCheckBox {
                color: #ffffff;
            }
            QCheckBox::indicator:checked {
                background-color: #0d47a1;
            }
            QGroupBox {
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                color: #ffffff;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                background-color: #2b2b2b;
            }
            QScrollArea {
                border: none;
            }
        """)    


    # ===== LIBRARY DATABASE TAB =====
    
    def create_library_database_tab(self):
        """Create the Library Database tab with search and display"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Search Section
        search_group = QGroupBox("Search Footprints")
        search_layout = QGridLayout(search_group)
        
        # Search By dropdown
        search_layout.addWidget(QLabel("Search By:"), 0, 0)
        self.search_by_combo = QComboBox()
        self.search_by_combo.addItems(["Part Number", "Footprint Name"])
        search_layout.addWidget(self.search_by_combo, 0, 1)
        
        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter search term...")
        self.search_input.textChanged.connect(self.on_search_changed)
        search_layout.addWidget(self.search_input, 0, 2, 1, 2)
        
        # View Filter dropdown
        search_layout.addWidget(QLabel("View Filter:"), 1, 0)
        self.view_filter_combo = QComboBox()
        self.view_filter_combo.addItems(["All", "Created By", "Date"])
        self.view_filter_combo.currentTextChanged.connect(self.on_filter_changed)
        search_layout.addWidget(self.view_filter_combo, 1, 1)
        
        # Created By dropdown (hidden by default)
        self.created_by_label = QLabel("Created By:")
        self.created_by_label.setVisible(False)
        search_layout.addWidget(self.created_by_label, 1, 2)
        
        self.created_by_combo = QComboBox()
        self.created_by_combo.setVisible(False)
        self.created_by_combo.currentTextChanged.connect(self.on_search_changed)
        search_layout.addWidget(self.created_by_combo, 1, 3)
        
        # Date pickers (hidden by default)
        self.start_date_label = QLabel("Start Date:")
        self.start_date_label.setVisible(False)
        search_layout.addWidget(self.start_date_label, 2, 0)
        
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate.currentDate().addMonths(-1))
        self.start_date_edit.setVisible(False)
        self.start_date_edit.dateChanged.connect(self.on_search_changed)
        search_layout.addWidget(self.start_date_edit, 2, 1)
        
        self.end_date_label = QLabel("End Date:")
        self.end_date_label.setVisible(False)
        search_layout.addWidget(self.end_date_label, 2, 2)
        
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate())
        self.end_date_edit.setVisible(False)
        self.end_date_edit.dateChanged.connect(self.on_search_changed)
        search_layout.addWidget(self.end_date_edit, 2, 3)
        
        layout.addWidget(search_group)
        
        # Results Section
        results_label = QLabel("Search Results:")
        results_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-top: 10px; color: #00FFFF;")
        layout.addWidget(results_label)
        
        # Scrollable results area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #555; background-color: #1e1e1e; }")
        
        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.results_container)
        
        layout.addWidget(scroll)
        
        # Export button
        export_btn = QPushButton("📊 Export to Excel")
        export_btn.clicked.connect(self.export_to_excel)
        layout.addWidget(export_btn)
        
        # Load library data on tab creation
        QTimer.singleShot(500, self.load_library_data)
        
        return widget
    
    def load_library_data(self):
        """Load footprint library from server"""
        if not self.parent_server:
            print("No server connection for library")
            return
        
        try:
            response = self.parent_server.session.get(
                f'{self.parent_server.api_url}/footprints/library',
                timeout=5
            )
            
            if response.status_code == 200:
                self.all_footprints = response.json()
                self.filtered_footprints = self.all_footprints.copy()
                
                # Populate creators dropdown
                creators = set()
                for fp in self.all_footprints:
                    creator = fp.get('created_by', 'Unknown')
                    if creator:
                        creators.add(creator)
                
                self.created_by_combo.clear()
                self.created_by_combo.addItems(sorted(creators))
                
                # Display results
                self.display_results()
                print(f"Loaded {len(self.all_footprints)} footprints from library")
            else:
                print(f"Failed to load library: {response.status_code}")
        
        except Exception as e:
            print(f"Error loading library: {e}")
    
    def on_search_changed(self):
        """Handle search input changes"""
        search_term = self.search_input.text().strip().lower()
        search_by = self.search_by_combo.currentText()
        
        # Start with all footprints
        results = self.all_footprints.copy()
        
        # Apply search filter
        if search_term:
            if search_by == "Part Number":
                results = [fp for fp in results if search_term in fp.get('part_number', '').lower()]
            else:  # Footprint Name
                results = [fp for fp in results if search_term in fp.get('footprint_name', '').lower()]
        
        # Apply view filter
        view_filter = self.view_filter_combo.currentText()
        
        if view_filter == "Created By":
            creator = self.created_by_combo.currentText()
            results = [fp for fp in results if fp.get('created_by', '') == creator]
        
        elif view_filter == "Date":
            start_date = self.start_date_edit.date().toPyDate()
            end_date = self.end_date_edit.date().toPyDate()
            
            filtered_by_date = []
            for fp in results:
                date_str = fp.get('created_date', '')
                try:
                    fp_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    if start_date <= fp_date <= end_date:
                        filtered_by_date.append(fp)
                except:
                    pass
            
            results = filtered_by_date
        
        self.filtered_footprints = results
        self.display_results()
    
    def on_filter_changed(self, filter_type):
        """Handle view filter changes"""
        # Show/hide filter options
        show_creator = filter_type == "Created By"
        show_date = filter_type == "Date"
        
        self.created_by_label.setVisible(show_creator)
        self.created_by_combo.setVisible(show_creator)
        
        self.start_date_label.setVisible(show_date)
        self.start_date_edit.setVisible(show_date)
        self.end_date_label.setVisible(show_date)
        self.end_date_edit.setVisible(show_date)
        
        # Re-apply search
        self.on_search_changed()
    
    def display_results(self):
        """Display search results as cards"""
        # Clear existing results
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not self.filtered_footprints:
            no_results = QLabel("No footprints found")
            no_results.setStyleSheet("color: #888; font-size: 14px; padding: 20px;")
            no_results.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_layout.addWidget(no_results)
            return
        
        # Create cards for each footprint
        for fp in self.filtered_footprints:
            card = self.create_footprint_card(fp)
            self.results_layout.addWidget(card)
    
    def create_footprint_card(self, footprint):
        """Create a visual card for a footprint"""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #2b2b2b;
                border: 1px solid #555;
                border-radius: 5px;
                padding: 10px;
                margin: 5px;
            }
            QFrame:hover {
                background-color: #3c3c3c;
                border: 1px solid #0d47a1;
            }
        """)
        
        layout = QGridLayout(card)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Serial number
        serial = QLabel(f"🔢 #{footprint.get('serial', 'N/A')}")
        serial.setStyleSheet("font-weight: bold; color: #00FFFF; font-size: 12px;")
        layout.addWidget(serial, 0, 0)
        
        # Created date
        date = QLabel(f"📅 {footprint.get('created_date', 'Unknown')}")
        date.setStyleSheet("color: #aaa; font-size: 11px;")
        layout.addWidget(date, 0, 1, Qt.AlignmentFlag.AlignRight)
        
        # Part Number
        part_num = QLabel(f"Part: {footprint.get('part_number', 'N/A')}")
        part_num.setStyleSheet("font-weight: bold; color: #FFD700; font-size: 13px;")
        layout.addWidget(part_num, 1, 0, 1, 2)
        
        # Footprint Name
        fp_name = QLabel(f"Footprint: {footprint.get('footprint_name', 'N/A')}")
        fp_name.setStyleSheet("color: #FFA500; font-size: 12px;")
        layout.addWidget(fp_name, 2, 0, 1, 2)
        
        # Standard used
        standard = QLabel(f"⚙️ Standard: {footprint.get('standard', 'None')}")
        standard.setStyleSheet("color: #90EE90; font-size: 11px;")
        layout.addWidget(standard, 3, 0)
        
        # Creator
        creator = QLabel(f"👤 By: {footprint.get('created_by', 'Unknown')}")
        creator.setStyleSheet("color: #DDA0DD; font-size: 11px;")
        layout.addWidget(creator, 3, 1, Qt.AlignmentFlag.AlignRight)
        
        return card
    
    def export_to_excel(self):
        """Export filtered results to Excel"""
        if not self.filtered_footprints:
            QMessageBox.warning(self, "No Data", "No footprints to export")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export to Excel",
            os.path.expanduser("~/footprints_library.xlsx"),
            "Excel Files (*.xlsx)"
        )
        
        if not filename:
            return
        
        try:
            import openpyxl
            from openpyxl import Workbook
            
            wb = Workbook()
            ws = wb.active
            ws.title = "Footprints Library"
            
            # Headers
            headers = ["Serial", "Part Number", "Footprint Name", "Standard", "Created By", "Created Date"]
            ws.append(headers)
            
            # Data rows
            for fp in self.filtered_footprints:
                row = [
                    fp.get('serial', ''),
                    fp.get('part_number', ''),
                    fp.get('footprint_name', ''),
                    fp.get('standard', ''),
                    fp.get('created_by', ''),
                    fp.get('created_date', '')
                ]
                ws.append(row)
            
            # Auto-adjust column widths
            for column in ws.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(cell.value)
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                ws.column_dimensions[column_letter].width = adjusted_width
            
            wb.save(filename)
            QMessageBox.information(self, "Success", f"Exported {len(self.filtered_footprints)} footprints to:\n{filename}")
        
        except ImportError:
            QMessageBox.critical(self, "Error", "openpyxl library not installed.\nInstall with: pip install openpyxl")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Export failed: {str(e)}")
    

# ============================================================================
# COURTYARD EXPANSION ROW WIDGET
# ============================================================================

class CourtyardExpansionRow(QGroupBox):
    """Individual courtyard expansion group with layer and settings"""
    delete_signal = pyqtSignal()
    
    def __init__(self, row_num):
        super().__init__(f"Courtyard Expansion {row_num}")
        self.row_num = row_num
        self.setup_ui()
    
    def setup_ui(self):
        layout = QGridLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Layer selection
        layout.addWidget(QLabel("Layer:"), 0, 0)
        self.layer_combo = QComboBox()
        self.layer_combo.addItems([
            'Mechanical 13',
            'Mechanical 15',
            'Mechanical 3',
            'Top Courtyard',
            'Bottom Courtyard',
            'Custom Layer'
        ])
        self.layer_combo.setStyleSheet("background-color: #3c3c3c; color: white; padding: 5px;")
        layout.addWidget(self.layer_combo, 0, 1)
        
        # Expansion value
        layout.addWidget(QLabel("Expansion (mm):"), 1, 0)
        self.expansion_input = QLineEdit("0.25")
        self.expansion_input.setStyleSheet("background-color: #3c3c3c; color: white; padding: 5px;")
        layout.addWidget(self.expansion_input, 1, 1)
        
        # Line width
        layout.addWidget(QLabel("Line Width (mm):"), 2, 0)
        self.line_width_input = QLineEdit("0.1")
        self.line_width_input.setStyleSheet("background-color: #3c3c3c; color: white; padding: 5px;")
        layout.addWidget(self.line_width_input, 2, 1)
        
        # Delete button
        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(self.delete_signal.emit)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #D32F2F;
                color: white;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #C62828;
            }
        """)
        delete_btn.setMaximumWidth(80)
        layout.addWidget(delete_btn, 3, 1, Qt.AlignmentFlag.AlignRight)
    
    def set_row_number(self, num):
        """Update row number"""
        self.row_num = num
        self.setTitle(f"Courtyard Expansion {num}")
    
    def get_data(self):
        """Get courtyard expansion data"""
        return {
            'layer': self.layer_combo.currentText(),
            'expansion': self.expansion_input.text(),
            'line_width': self.line_width_input.text()
        }
    
    def set_data(self, data):
        """Set courtyard expansion data"""
        self.layer_combo.setCurrentText(data.get('layer', 'Mechanical 13'))
        self.expansion_input.setText(str(data.get('expansion', '0.25')))
        self.line_width_input.setText(str(data.get('line_width', '0.1')))

class UpdateThread(QThread):
    update_signal = pyqtSignal(dict)

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.running = True

    def run(self):
        while self.running:
            data = self.main_window.get_footprint_data()
            self.update_signal.emit(data)
            self.msleep(100) # Update every 100ms

    def stop(self):
        self.running = False



class FootprintDesigner(QMainWindow):
    def __init__(self):
        super().__init__()
        self.padstack_rows = []
        self.custom_layer_rows = []
        self.thermal_via_rows = []
        self.current_save_file = None
        self.courtyard_layer_rows = []
        # Courtyard type tracking - NEW
        self.courtyard_type = 'standard'  # 'standard' or 'bga_pth'
        self.active_courtyard_expansion = '0.25'        
        
        # CRITICAL: Initialize all missing attributes
        self.fiducials_enabled = False  # ADD THIS LINE
        self.silkscreen_enabled = True   # ADD THIS LINE
        self.dfab_on_enabled = False     # ADD THIS LINE
        
        # Initialize server connection FIRST (before UI setup)
        self.server_url = 'http://localhost:5000'
        self.server = ServerConnection(self.server_url)
        self.token = None
        self.user_role = None
        self.username = None
        
        self.setup_ui()
        self.setup_dark_theme()
        
        # Pass server reference to settings panel
        if hasattr(self, 'settings_panel'):
            self.settings_panel.parent_server = self.server
        
        self.start_update_thread()
        self.load_app_settings()
        
        # Try auto-login
        QTimer.singleShot(500, self.try_auto_login)

    def setup_ui(self):
        self.setWindowTitle("Footprint Designer")
        self.setGeometry(100, 100, 1400, 800)
        self.showMaximized()

        # Create toolbar
        self.create_toolbar()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main splitter (3 panels: left, center, right)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        central_widget.setLayout(QHBoxLayout())
        central_widget.layout().addWidget(main_splitter)

        # Left panel
        left_panel = self.create_left_panel()
        main_splitter.addWidget(left_panel)

        # Center panel (renderer)
        self.renderer = FootprintRenderer()
        main_splitter.addWidget(self.renderer)
        self.renderer.footprint_designer_ref = self
    

        # Initialize renderer with proper origin values
        self.update_renderer_origin()

        self.origin_offset_x_input.textChanged.connect(self.on_origin_offset_changed)
        self.origin_offset_y_input.textChanged.connect(self.on_origin_offset_changed)        


        # Right panel (settings) - initially hidden
        self.settings_panel = SettingsPanel()
        self.settings_panel.settings_changed.connect(self.on_settings_changed)

        # Set initial splitter proportions
        main_splitter.setSizes([800, 700]) # Left, Center, Right (hidden)

    def create_toolbar(self):
        """Create toolbar with left and right aligned buttons"""
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        # Left side buttons
        file_menu = QMenu(self)
        
        new_action = QAction("New", self)
        new_action.triggered.connect(self.new_footprint)
        file_menu.addAction(new_action)
        
        open_action = QAction("Open", self)
        open_action.triggered.connect(self.load_data)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        save_action = QAction("Save", self)
        save_action.triggered.connect(self.save_data)
        file_menu.addAction(save_action)
        
        save_as_action = QAction("Save As", self)
        save_as_action.triggered.connect(self.save_data_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        file_btn = QPushButton("File")
        file_btn.setMenu(file_menu)
        toolbar.addWidget(file_btn)
        
        toolbar.addSeparator()
        # Add dropdown for script generation
        self.script_combo = QComboBox()
        self.script_combo.addItems(["Altium", "Allegro", "PADS", "Xpedition"])
        self.script_combo.setMaximumWidth(100)
        self.script_combo.setEnabled(False)  # ← DISABLE THE COMBO BOX
        self.script_combo.setToolTip("Tool selection is from Settings panel standard")
        toolbar.addWidget(QLabel("Generate:"))
        toolbar.addWidget(self.script_combo)
        toolbar.addAction("Script", self.generate_footprint_script)

        toolbar.addSeparator()

        # Show Silkscreen toggle action
        self.silkscreen_action = toolbar.addAction("Show Silkscreen", self.toggle_silkscreen)
        self.silkscreen_action.setCheckable(True)
        self.silkscreen_action.setChecked(True)

        # Add Fiducial toggle
        self.fiducial_action = toolbar.addAction("+ Add Fiducial", self.toggle_fiducials)
        self.fiducial_action.setCheckable(True)
        self.fiducial_action.setChecked(False)

        toolbar.addSeparator()
        toolbar.addAction("+ Add Padstack", self.add_padstack_row)
        toolbar.addAction("+ Custom Layer", self.add_custom_layer_row)
        toolbar.addAction("+ Thermal Via", self.add_thermal_via_row)

        toolbar.addSeparator()
        toolbar.addAction("Fit to View", self.fit_to_view)

        # Add stretch to push Account and Settings to the right
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        toolbar.addWidget(spacer)

        self.courtyard_type_combo = QComboBox()
        self.courtyard_type_combo.addItems(['Standard', 'BGA/PTH'])
        self.courtyard_type_combo.currentTextChanged.connect(self.on_courtyard_type_changed)
        toolbar.addWidget(self.courtyard_type_combo)
        # Standard dropdown
        self.standard_combo = QComboBox()
        self.standard_combo.setMinimumWidth(250)
        self.standard_combo.addItem("-- Select Standard --", None)
        self.standard_combo.currentIndexChanged.connect(self.on_standard_selected)
        self.standard_combo.currentIndexChanged.connect(self.change_tool)
        

        toolbar.addWidget(self.standard_combo)
        
        toolbar.addSeparator()
        toolbar.addAction("Account", self.show_account_dialog)  # NEW ACCOUNT BUTTON
        toolbar.addAction("Settings", self.toggle_settings_panel)

    def change_tool(self):
        """Handle tool change and update layer visibility"""
        if hasattr(self, 'settings_panel'):
            tool = self.settings_panel.tool_combo.currentText()
            self.script_combo.setCurrentText(tool)

            # Always hide noprob for Altium, regardless of standard selection
            if tool == "Altium":
                if hasattr(self, 'renderer'):
                    self.renderer.show_noprob_top = False
                    self.renderer.show_noprob_bottom = False
                    self.renderer.update()
                    print("NoProb layers hidden for Altium")
            else:
                # For other tools (Allegro, PADS, Xpedition), show noprob layers
                if hasattr(self, 'renderer'):
                    self.renderer.show_noprob_top = True
                    self.renderer.show_noprob_bottom = True
                    self.renderer.update()
                    print(f"NoProb layers shown for {tool}")

    def show_account_dialog(self):
        """Show account dialog"""
        dialog = AccountDialog(self, self.server_url)
        # CRITICAL: Connect the signal PROPERLY
        dialog.login_success.connect(self.on_login_success)
        dialog.exec()

    def on_login_success(self, token, role, username):
        """Handle successful login - THIS IS CRITICAL"""
        print(f"on_login_success called: token={bool(token)}, role={role}, username={username}")
        
        self.token = token
        self.user_role = role
        self.username = username
        
        # Update user label
        if hasattr(self, 'user_label'):
            self.user_label.setText(f"👤 {username} ({role.capitalize()})")
        
        # CRITICAL: Update settings panel with authentication FIRST
        if hasattr(self, 'settings_panel'):
            print("Setting authentication on settings_panel")
            self.settings_panel.set_authentication(token, role, username)
            self.settings_panel.parent_server = self.server
            print(f"SettingsPanel now has token={bool(self.settings_panel.token)}, is_admin_manager={self.settings_panel.is_admin_manager}")
        
        # Load standards after auth is set
        self.load_standards()

    def try_auto_login(self):
        """Try to auto-login with saved credentials"""
        creds = self.server.load_saved_credentials()
        if creds and 'token' in creds:
            success, role = self.server.verify_token(creds['token'])
            if success:
                print(f"Auto-login successful: {creds['username']} as {role}")
                self.on_login_success(creds['token'], role, creds.get('username'))

    def setup_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox {
                background-color: #3c3c3c;
                border: 1px solid #555;
                padding: 5px;
                border-radius: 3px;
            }
            QPushButton {
                background-color: #4a4a4a;
                border: 1px solid #666;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
            QScrollArea {
                background-color: #2b2b2b;
                border: none;
            }
            QFrame {
                border: 1px solid #555;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                background-color: #2b2b2b;
            }
            QToolBar {
                background-color: #3c3c3c;
                border: 1px solid #555;
                spacing: 3px;
            }
            QToolBar::separator {
                width: 2px;
                background-color: #555;
                margin: 0 5px;
            }
        """)

    def load_standards(self):
        """Load standards from LOCAL storage only"""
        print("Loading standards from local storage")
        
        # Load from local JSON file
        standards = LocalStandardsManager.load_local_standards()
        
        # Clear and populate the combo box
        self.standard_combo.blockSignals(True)  # Prevent triggering signals during load
        self.standard_combo.clear()
        self.standard_combo.addItem("-- Select Standard --", None)
        
        for standard in standards:
            self.standard_combo.addItem(standard['name'], standard)
        
        self.standard_combo.blockSignals(False)
        
        print(f"Loaded {len(standards)} standards from local storage")

    def on_standard_selected_toolbar(self, index):
        """Load selected standard into settings"""
        if index == 0:  # Default option
            return
        
        standard = self.standard_combo.itemData(index)
        if standard and hasattr(self, 'settings_panel'):
            config = standard['data']
            self.settings_panel.load_settings_from_config(config)

    def on_standard_selected(self, index):
        """Load selected standard into settings"""
        if index == 0:
            # "-- Select Standard --" selected
            # Check current tool and hide noprob for Altium
            if hasattr(self, 'settings_panel'):
                tool = self.settings_panel.tool_combo.currentText()
                if tool == "Altium":
                    if hasattr(self, 'renderer'):
                        self.renderer.show_noprob_top = False
                        self.renderer.show_noprob_bottom = False
                        self.renderer.update()
            return
        
        standard = self.standard_combo.itemData(index)
        if standard:
            config = standard['data']
            self.settings_panel.load_settings_from_config(config)
            
            # Enable noprob layers when a standard is loaded
            if hasattr(self, 'renderer'):
                tool = self.settings_panel.tool_combo.currentText()
                if tool != "Altium":  # Only show for non-Altium tools
                    self.renderer.show_noprob_top = True
                    self.renderer.show_noprob_bottom = True
                    self.renderer.update()

    def load_app_settings(self):
        """Load application settings (only footprint-related settings now)"""
        settings = SettingsManager.load_settings()
        self.settings_panel.set_settings(settings)

    def save_app_settings(self):
        """Save application settings (only footprint-related settings now)"""
        settings = self.settings_panel.get_settings()
        SettingsManager.save_settings(settings)

    def on_courtyard_type_changed(self):
        """Switch between Standard and BGA/PTH courtyard expansion"""
        courtyard_type_text = self.courtyard_type_combo.currentText()
        
        # Get current settings
        settings = self.settings_panel.get_settings()
        
        if courtyard_type_text == 'BGA/PTH':
            # Switch to BGA/PTH courtyard - SINGLE VALUE
            self.courtyard_type = 'bga_pth'
            self.active_courtyard_expansion = settings.get('bga_pth_courtyard_expansion', '0.5')
            
            print(f"Switched to BGA/PTH courtyard: {self.active_courtyard_expansion} mm")
        else:
            # Switch to Standard courtyard
            self.courtyard_type = 'standard'
            self.active_courtyard_expansion = settings.get('courtyard_expansion', '0.25')
            
            print(f"Switched to Standard courtyard: {self.active_courtyard_expansion} mm")
        
        # Update display
        self.update_courtyard_display()
        
        # Trigger redraw
        self.on_data_changed()

    def update_courtyard_display(self):
        """Update courtyard value display in toolbar"""
        if hasattr(self, 'courtyard_value_display'):
            self.courtyard_value_display.setText(f"{self.active_courtyard_expansion} mm")

    def get_footprint_data(self):
        """Get all footprint data"""
        settings = self.settings_panel.get_settings()
        
        # Get the active courtyard expansion based on toggle
        if self.courtyard_type == 'bga_pth':
            active_courtyard = settings.get('bga_pth_courtyard_expansion', '0.5')
        else:
            active_courtyard = settings.get('courtyard_expansion', '0.25')
        
        data = {
            'part_number': self.part_number.text(),
            'footprint_name': self.footprint_name.text(),
            'ref_des': self.ref_des.text(),
            'body_length': self.body_length.text(),
            'body_width': self.body_width.text(),
            'body_height': self.body_height.text(),
            'body_shape': self.body_shape_combobox.currentText(),
            'origin_offset_x': self.origin_offset_x_input.text(),
            'origin_offset_y': self.origin_offset_y_input.text(),
            'body_chamfer': self.body_chamfer_input.text(),
            'chamfer_corners': {
                'tl': self.chamfer_tl_checkbox.isChecked(),
                'tr': self.chamfer_tr_checkbox.isChecked(),
                'bl': self.chamfer_bl_checkbox.isChecked(),
                'br': self.chamfer_br_checkbox.isChecked()
            },
            'auto_update_origin': self.auto_update_origin,
            'courtyard_expansion': active_courtyard,
            'courtyard_type': self.courtyard_type,
            'noprob_expansion': settings.get('noprob_expansion'),
            'silkscreen_airgap': settings.get('silkscreen_airgap'),
            'silkscreen_enabled': self.silkscreen_enabled,
            'silkscreen_follow_chamfer': settings.get('silkscreen_follow_chamfer', False),
            'dfab_on_enabled': self.dfab_on_enabled,
            'fiducials_enabled': self.fiducials_enabled,
            'padstacks': [row.get_data() for row in self.padstack_rows],
            'custom_layers': [row.get_data() for row in self.custom_layer_rows],
            'thermal_vias': [row.get_data() for row in self.thermal_via_rows],
            'courtyard_layers': [row.get_data() for row in getattr(self, 'courtyard_layer_rows', [])],
            'body_line_width': settings.get('body_line_width'),
            'courtyard_line_width': settings.get('courtyard_line_width'),
            'silkscreen_line_width': settings.get('silkscreen_line_width'),
            'settings': {
                'fiducial_diameter': settings.get('fiducial_diameter'),
                'fiducial_keepout_diameter': settings.get('fiducial_keepout_diameter'),
                'fiducial_x_offset': settings.get('fiducial_x_offset'),
                'fiducial_y_offset': settings.get('fiducial_y_offset'),
                'silkscreen_follow_chamfer': settings.get('silkscreen_follow_chamfer'),
                'via_keepout_expansion': settings.get('via_keepout_expansion'),
                'package_keepout_expansion': settings.get('package_keepout_expansion'),
                'route_keepout_expansion': settings.get('route_keepout_expansion'),
            },
            'text_settings': {
                'text_height': settings.get('text_height'),
                'text_width': settings.get('text_width'),
                'text_line_width': settings.get('text_line_width')
            }
        }
        return data

    def toggle_silkscreen(self):
        """Toggle silkscreen visibility"""
        self.on_data_changed()

    def toggle_fiducials(self):
        """Toggle fiducial visibility"""
        self.fiducials_enabled = self.fiducial_action.isChecked()
        self.on_data_changed()

    def load_app_settings(self):
        """Load application settings"""
        settings = SettingsManager.load_settings()
        self.settings_panel.set_settings(settings)

    def save_app_settings(self):
        """Save application settings"""
        settings = self.settings_panel.get_settings()
        SettingsManager.save_settings(settings)

    def toggle_settings_panel(self):
        """Toggle the visibility of settings panel"""
        is_visible = self.settings_panel.isVisible()
        self.settings_panel.setVisible(not is_visible)

        # Adjust splitter sizes
        if not is_visible:
            # Show settings panel
            self.centralWidget().layout().itemAt(0).widget().setSizes([700, 600, 300])
        else:
            # Hide settings panel
            self.centralWidget().layout().itemAt(0).widget().setSizes([800, 700, 0])

    def on_settings_changed(self):
        """Handle settings changes"""
        # Update renderer with new settings
        self.renderer.update()

    def create_left_panel(self):
        """Create left panel with tabbed interface"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create tab widget
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #555;
                background-color: #2b2b2b;
            }
            QTabBar::tab {
                background-color: #3c3c3c;
                color: #ffffff;
                padding: 6px 20px;
                border: 1px solid #555;
                font-size: 13px;
            }
            QTabBar::tab:selected {
                background-color: #0d47a1;
                color: #ffffff;
            }
            QTabBar::tab:hover {
                background-color: #4a4a4a;
            }
        """)
        
        # Tab 1: Pad Input (existing left panel - NO navigation)
        pad_input_tab = PadInputTab(self)
        tab_widget.addTab(pad_input_tab, "📍 Pad Input")
        
        # Tab 2: Package Input (WITH navigation: packages → IPC → inputs)
        package_input_tab = PackageInputTab(self)
        tab_widget.addTab(package_input_tab, "📦 Package Input")
        
        # Tab 3: AI Librarian
        ai_tab = AILibrarianTab()
        tab_widget.addTab(ai_tab, "🤖 AI Librarian")
        
        layout.addWidget(tab_widget)
        
        return panel

    def on_origin_manual_change(self):
        """Handle manual changes to origin offset - disable auto-update"""
        self.auto_update_origin = False
        self.update_renderer_origin()
        self.on_data_changed()

    def on_body_dimensions_changed(self):
        """Handle body dimension changes - auto-update origin if enabled"""
        if self.auto_update_origin:
            self.update_origin_offset_values()
        self.update_renderer_origin()
        self.on_data_changed()

    def update_origin_offset_values(self):
        """Update origin offset values based on body dimensions"""
        try:
            length = to_decimal(self.body_length.text())
            width = to_decimal(self.body_width.text())
        except (ValueError, TypeError):
            length = 5.0
            width = 3.0

        # Set offset to center of body (length/2, width/2)+
        x_offset = -length / 2
        y_offset = width / 2

        # Block signals to prevent triggering manual change handler
        self.origin_offset_x_input.blockSignals(True)
        self.origin_offset_y_input.blockSignals(True)
        
        self.origin_offset_x_input.setText(f"{x_offset}")
        self.origin_offset_y_input.setText(f"{y_offset}")
        
        self.origin_offset_x_input.blockSignals(False)
        self.origin_offset_y_input.blockSignals(False)
        
        # Re-enable auto-update since this was programmatic
        self.auto_update_origin = True


    def update_courtyard_display(self):
        """Update courtyard value display in toolbar"""
        if hasattr(self, 'courtyard_value_display'):
            self.courtyard_value_display.setText(f"{self.active_courtyard_expansion} mm")


    # ADD THIS METHOD
    def on_origin_offset_changed(self):
        """Called when origin offset inputs change"""
        try:
            print("="*50)
            print("on_origin_offset_changed CALLED")
            
            # Get current input values first
            new_x = Decimal(str(self.origin_offset_x_input.text()))
            new_y = Decimal(str(self.origin_offset_y_input.text()))
            print(f"New values from input: x={new_x}, y={new_y}")
            
            # Get old stored values
            old_x = getattr(self, '_last_origin_x', None)
            old_y = getattr(self, '_last_origin_y', None)
            print(f"Old stored values: x={old_x}, y={old_y}")
            
            # If either is None, this is first initialization
            if old_x is None or old_y is None:
                # Initialize with CURRENT input values, not zeros
                old_x = new_x if old_x is None else old_x
                old_y = new_y if old_y is None else old_y
                print(f"FIRST INITIALIZATION - Using current values as old: ({old_x}, {old_y})")
                # Store them
                self._last_origin_x = new_x
                self._last_origin_y = new_y
                print("Stored initial values, no adjustment needed")
                print("="*50)
                return  # Don't adjust on first initialization
            
            # Only adjust if values actually changed
            if old_x == new_x and old_y == new_y:
                print("Values unchanged, skipping adjustment")
                print("="*50)
                return
            
            print(f"VALUES CHANGED! Calling adjust_pads_for_origin_change")
            print(f"  Old: ({old_x}, {old_y})")
            print(f"  New: ({new_x}, {new_y})")
            
            # Perform adjustment
            self.adjust_pads_for_origin_change(old_x, old_y, new_x, new_y)
            
            # Update stored values
            self._last_origin_x = new_x
            self._last_origin_y = new_y
            print(f"Updated stored values to: x={new_x}, y={new_y}")
            
            # Trigger update
            self.on_data_changed()
            print("="*50)
            
        except Exception as e:
            print(f"ERROR in on_origin_offset_changed: {e}")
            import traceback
            traceback.print_exc()
            print("="*50)


    def adjust_pads_for_origin_change(self, old_origin_x, old_origin_y, new_origin_x, new_origin_y):
        """Adjust pad offsets when origin changes to maintain their absolute positions."""
        
        delta_x = Decimal(str(new_origin_x)) - Decimal(str(old_origin_x))
        delta_y = Decimal(str(new_origin_y)) - Decimal(str(old_origin_y))
        
        print(f"\nadjust_pads_for_origin_change CALLED")
        print(f"  delta_x={delta_x}, delta_y={delta_y}")
        print(f"  Number of padstack rows: {len(self.padstack_rows)}")
        
        adjusted_count = 0
        for i, row in enumerate(self.padstack_rows):
            # Block signals to prevent recursive updates
            row.x_offset.blockSignals(True)
            row.y_offset.blockSignals(True)
            
            pad_data = row.get_data()
            offset_from = pad_data.get('offset_from', 'origin')
            
            print(f"  Row {i}: offset_from={offset_from}")
            
            if offset_from == 'origin':
                current_x = Decimal(str(pad_data.get('x_offset', 0)))
                current_y = Decimal(str(pad_data.get('y_offset', 0)))
                
                # To maintain absolute position: new_offset = old_offset + delta
                new_x = current_x + delta_x
                new_y = current_y + delta_y
                
                print(f"    Pad {i}: old=({current_x},{current_y}) -> new=({new_x},{new_y})")
                
                # Update directly in UI
                row.x_offset.setText(str(new_x))
                row.y_offset.setText(str(new_y))
                adjusted_count += 1
            
            # Unblock signals
            row.x_offset.blockSignals(False)
            row.y_offset.blockSignals(False)
        
        print(f"  Adjusted {adjusted_count} pad(s)\n")


    def update_renderer_origin(self):
        """Update the renderer with current origin offset values"""
        try:
            x_offset = to_decimal(self.origin_offset_x_input.text())
            y_offset = to_decimal(self.origin_offset_y_input.text())
        except (ValueError, TypeError):
            x_offset = y_offset = 0.0

        if hasattr(self, 'renderer'):
            self.renderer.origin_offset_x = x_offset
            self.renderer.origin_offset_y = y_offset
            self.renderer.update()

    def on_origin_offset_inputs_changed(self):
        """Handle changes to origin offset input fields"""
        # Always update if the inputs are enabled (regardless of checkbox state)
        if self.origin_offset_x_input.isEnabled() or self.origin_offset_y_input.isEnabled():
            self.update_origin_offset_from_inputs()
        
        # Also trigger general data change
        self.on_data_changed()

    def new_footprint(self):
        """Create a new footprint (reset all fields)"""
        reply = QMessageBox.question(
            self,
            'New Footprint',
            'Are you sure you want to create a new footprint? All current data will be lost.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Clear current file path
            self.current_save_file = None

            # Clear all input fields
            self.part_number.setText('')
            self.footprint_name.setText('')
            self.ref_des.setText('')
            self.body_length.setText('5.0')
            self.body_width.setText('3.0')
            self.body_height.setText('1.0')
            self.body_shape_combobox.setCurrentIndex(0)

            # Set default origin offset values
            self.origin_offset_x_input.setText("-2.5")  # Default to length/2
            self.origin_offset_y_input.setText("1.5")  # Default to width/2
            self.auto_update_origin = True
            self.update_origin_offset_values()


            # Reset silkscreen action
            self.silkscreen_action.setChecked(True)
          
            default_settings = {
                'body_line_width': '0.05',
                'courtyard_expansion': '0.25',
                'courtyard_line_width': '0.1',
                'noprob_expansion': '0.51',
                'noprob_line_width': '0.1',
                'silkscreen_airgap': '0.15',
                'silkscreen_line_width': '0.15',
            }
            self.settings_panel.set_settings(default_settings)

            # Clear all padstacks
            for row in self.padstack_rows[:]:
                self.delete_padstack_row(row)

            # Clear all custom layers
            for row in self.custom_layer_rows[:]:
                self.delete_custom_layer_row(row)

            # Clear all thermal vias
            for row in self.thermal_via_rows[:]:
                self.delete_thermal_via_row(row)

            # Add one default padstack
            self.add_padstack_row()

    def save_data_as(self):
        """Save footprint data with new filename"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Footprint As", "",
            "LibSienna Footprint Files (*.LibSienna);;All Files (*)"
        )
        
        if filename:
            # Ensure consistent file extension (case-insensitive check)
            if not filename.lower().endswith('.libsienna'):
                filename += '.LibSienna'
                
            self.current_save_file = filename
            data = self.get_footprint_data()
            success = LibSiennaFileFormat.save_footprint(data, filename)
            if success:
                # Also save app settings
                self.save_app_settings()
                QMessageBox.information(self, "Success", f"Footprint saved successfully as {os.path.basename(filename)}!")
            else:
                QMessageBox.critical(self, "Error", "Failed to save footprint file!")

    def save_data(self):
        """Save footprint data and app settings"""
        # Save footprint data to LibSienna file
        if self.current_save_file is None:
            self.save_data_as()
        else:
            data = self.get_footprint_data()
            success = LibSiennaFileFormat.save_footprint(data, self.current_save_file)
            if success:
                # Also save app settings
                self.save_app_settings()
                QMessageBox.information(self, "Success", f"Footprint updated successfully!\n{os.path.basename(self.current_save_file)}")
            else:
                QMessageBox.critical(self, "Error", "Failed to save footprint file!")

    def load_data(self):
        """Load footprint data from custom LibSienna format"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load Footprint",
            "",
            "LibSienna Footprint Files (*.LibSienna *.libsienna);;All Files (*)"  # Accept both cases
        )
        
        if filename:
            print(f"Selected file: {filename}")  # Debug info
            data = LibSiennaFileFormat.load_footprint(filename)
            if data:
                try:
                    self.set_footprint_data(data)
                    # Set current file path so Save will work
                    self.current_save_file = filename
                    QMessageBox.information(
                        self,
                        "Success",
                        f"Footprint loaded successfully from {os.path.basename(filename)}!"
                    )
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to apply loaded data:\n{str(e)}")
            else:
                QMessageBox.critical(self, "Error", "Failed to load footprint file!\nCheck console for details.")

    def fit_to_view(self):
        self.renderer.auto_fit = True
        self.renderer.fit_to_view()
        self.renderer.update()

    def add_padstack_row(self):
        row = PadStackRow()
        row.delete_requested.connect(self.delete_padstack_row)
        row.data_changed.connect(self.on_data_changed)
        row.duplicate_btn.clicked.connect(lambda: self.duplicate_padstack_row(row))

        self.padstack_rows.append(row)
        self.container_layout.insertWidget(len(self.padstack_rows) + len(self.custom_layer_rows) + len(self.thermal_via_rows) - 1, row)

        # Set pin number automatically
        row.pin_number.setText(str(len(self.padstack_rows)))

        # Update all offset_from dropdowns
        self.update_all_offset_dropdowns()

    def delete_padstack_row(self, row):
        if len(self.padstack_rows) > 0:
            self.padstack_rows.remove(row)
            row.setParent(None)
            # Update all remaining offset_from dropdowns
            self.update_all_offset_dropdowns()

    def duplicate_padstack_row(self, original_row):
        new_row = PadStackRow()
        new_row.delete_requested.connect(self.delete_padstack_row)
        new_row.data_changed.connect(self.on_data_changed)
        new_row.duplicate_btn.clicked.connect(lambda: self.duplicate_padstack_row(new_row))

        # Copy data from original
        data = original_row.get_data()
        data['pin_number'] = str(len(self.padstack_rows) + 1)
        
        # NEW: Handle offset_from pin number increment
        offset_from = data.get('offset_from', 'origin')
        if offset_from != 'origin':
            try:
                # Try to convert to int and increment by 1
                pin_num = int(offset_from)
                data['offset_from'] = str(pin_num + 1)
            except ValueError:
                # If it's not a numeric pin (like 'V1' for thermal vias), keep it as is
                # You could add more logic here if needed for other pin formats
                pass

        # Add to layout FIRST so update_offset_from_options can find all rows
        self.padstack_rows.append(new_row)
        self.container_layout.insertWidget(len(self.padstack_rows) + len(self.custom_layer_rows) + len(self.thermal_via_rows) - 1, new_row)

        # Update all dropdowns to include the new pin numbers
        self.update_all_offset_dropdowns()

        # NOW set the data - the dropdown will have the correct options
        new_row.set_data(data)


    def add_custom_layer_row(self):
        row = CustomLayerRow()
        row.delete_requested.connect(self.delete_custom_layer_row)
        row.data_changed.connect(self.on_data_changed)
        row.duplicate_btn.clicked.connect(lambda: self.duplicate_custom_layer_row(row))

        self.custom_layer_rows.append(row)
        self.container_layout.insertWidget(len(self.padstack_rows) + len(self.custom_layer_rows) + len(self.thermal_via_rows) - 1, row)

        # Update all offset_from dropdowns
        self.update_all_offset_dropdowns()

    def delete_custom_layer_row(self, row):
        if row in self.custom_layer_rows:
            self.custom_layer_rows.remove(row)
            row.setParent(None)
            self.update_all_offset_dropdowns()

    def duplicate_custom_layer_row(self, original_row):
        new_row = CustomLayerRow()
        new_row.delete_requested.connect(self.delete_custom_layer_row)
        new_row.data_changed.connect(self.on_data_changed)
        new_row.duplicate_btn.clicked.connect(lambda: self.duplicate_custom_layer_row(new_row))

        # Copy data from original
        data = original_row.get_data()

        # Add to layout
        self.custom_layer_rows.append(new_row)
        self.container_layout.insertWidget(len(self.padstack_rows) + len(self.custom_layer_rows) + len(self.thermal_via_rows) - 1, new_row)

        # Update dropdowns and set data
        self.update_all_offset_dropdowns()
        new_row.set_data(data)

    def add_thermal_via_row(self):
        row = ThermalViaRow()
        row.delete_requested.connect(self.delete_thermal_via_row)
        row.data_changed.connect(self.on_data_changed)
        row.duplicate_btn.clicked.connect(lambda: self.duplicate_thermal_via_row(row))
        
        self.thermal_via_rows.append(row)
        self.container_layout.insertWidget(len(self.padstack_rows) + len(self.custom_layer_rows) + len(self.thermal_via_rows) - 1, row)

        # Set via pin number automatically
        row.pin_number.setText(f"V{len(self.thermal_via_rows)}")  # ADD THIS LINE

        # Update all offset_from dropdowns
        self.update_all_offset_dropdowns()


    def delete_thermal_via_row(self, row):
        if row in self.thermal_via_rows:
            self.thermal_via_rows.remove(row)
            row.setParent(None)
            self.update_all_offset_dropdowns()

    def duplicate_thermal_via_row(self, original_row):
        new_row = ThermalViaRow()
        new_row.delete_requested.connect(self.delete_thermal_via_row)
        new_row.data_changed.connect(self.on_data_changed)
        new_row.duplicate_btn.clicked.connect(lambda: self.duplicate_thermal_via_row(new_row))

        # Copy data from original
        data = original_row.get_data()
        data['pin_number'] = f"V{len(self.thermal_via_rows) + 1}"  # ADD THIS LINE

        # Add to layout
        self.thermal_via_rows.append(new_row)
        self.container_layout.insertWidget(len(self.padstack_rows) + len(self.custom_layer_rows) + len(self.thermal_via_rows) - 1, new_row)

        # Update dropdowns and set data
        self.update_all_offset_dropdowns()
        new_row.set_data(data)


    def update_all_offset_dropdowns(self):
        """Update all offset_from dropdowns when pads/vias are added/removed"""
        # Collect all available pad pin numbers
        available_pad_pins = []
        for row in self.padstack_rows:
            pin_text = row.pin_number.text().strip()
            if pin_text:
                available_pad_pins.append(pin_text)
        
        # Collect all available thermal via pin numbers
        available_via_pins = []
        for row in self.thermal_via_rows:
            pin_text = row.pin_number.text().strip()
            if pin_text:
                available_via_pins.append(pin_text)

        # Update padstack dropdowns (only pad pins)
        for row in self.padstack_rows:
            row.update_offset_from_options()

        # Update custom layer dropdowns (only pad pins)
        for row in self.custom_layer_rows:
            current_selection = row.offset_from.currentText()
            row.offset_from.blockSignals(True)
            row.offset_from.clear()
            row.offset_from.addItem('origin')
            row.offset_from.addItems(available_pad_pins)

            # Restore previous selection if still valid
            index = row.offset_from.findText(current_selection)
            if index >= 0:
                row.offset_from.setCurrentIndex(index)
            else:
                row.offset_from.setCurrentText('origin')
            row.offset_from.blockSignals(False)

        # Update thermal via dropdowns (pad pins + thermal via pins)
        for row in self.thermal_via_rows:
            current_selection = row.offset_from.currentText()
            current_pin = row.pin_number.text().strip()
            
            row.offset_from.blockSignals(True)
            row.offset_from.clear()
            row.offset_from.addItem('origin')
            
            # Add pad pins
            row.offset_from.addItems(available_pad_pins)
            
            # Add thermal via pins (excluding current row's own pin)
            for via_pin in available_via_pins:
                if via_pin != current_pin:  # Don't include self-reference
                    row.offset_from.addItem(via_pin)

            # Restore previous selection if still valid
            index = row.offset_from.findText(current_selection)
            if index >= 0:
                row.offset_from.setCurrentIndex(index)
            else:
                row.offset_from.setCurrentText('origin')
            row.offset_from.blockSignals(False)


    def on_data_changed(self):
        # This will be handled by the update thread
        pass

    def set_footprint_data(self, data):
        self.part_number.setText(data.get('part_number', ''))
        self.footprint_name.setText(data.get('footprint_name', ''))
        self.ref_des.setText(data.get('ref_des', ''))
        self.body_length.setText(str(data.get('body_length', Decimal('5.0'))))
        self.body_width.setText(str(data.get('body_width', Decimal('3.0'))))
        self.body_height.setText(str(data.get('body_height', Decimal('1.0'))))
        self.body_shape_combobox.setCurrentText(data.get('body_shape', 'rectangle'))

        # In set_footprint_data:
        self.body_chamfer_input.setText(str(data.get('body_chamfer', '0')))
        chamfer_corners = data.get('chamfer_corners', {})
        self.chamfer_tl_checkbox.setChecked(chamfer_corners.get('tl', False))
        self.chamfer_tr_checkbox.setChecked(chamfer_corners.get('tr', False))
        self.chamfer_bl_checkbox.setChecked(chamfer_corners.get('bl', False))
        self.chamfer_br_checkbox.setChecked(chamfer_corners.get('br', False))
        
        # Set origin offset values
        self._last_origin_x = Decimal(str(data.get('origin_offset_x', 0)))
        self._last_origin_y = Decimal(str(data.get('origin_offset_y', 0)))     
        self.origin_offset_x_input.setText(str(data.get('origin_offset_x', Decimal('-2.5'))))
        self.origin_offset_y_input.setText(str(data.get('origin_offset_y', Decimal('1.5'))))
        self.auto_update_origin = data.get('auto_update_origin', True)
        
        # Update renderer
        self.update_renderer_origin()
    
        
        self.silkscreen_action.setChecked(data.get('silkscreen_enabled', True))

        
        # Update settings panel
        settings = {

            'fiducial_diameter': '1.0',           # Copper pad diameter (mm)
            'fiducial_mask_opening': '2.0',       # Mask opening diameter (mm)
            'fiducial_keepout_diameter': '3.0',   # Keepout zone diameter (mm)
            'fiducial_x_offset': '2.0',           # X offset from body corner (mm)
            'fiducial_y_offset': '2.0',    
            'body_line_width': data.get('body_line_width', '0.05'),
            'courtyard_expansion': data.get('courtyard_expansion', '0.25'),
            'courtyard_line_width': data.get('courtyard_line_width', '0.1'),
            'noprob_expansion': data.get('noprob_expansion', '0.51'),
            'noprob_line_width': data.get('noprob_line_width', '0.1'),


            'silkscreen_airgap': data.get('silkscreen_airgap', '0.15'),
            'silkscreen_line_width': data.get('silkscreen_line_width', '0.15'),
            'text_height': data.get('text_settings', {}).get('text_height', '0.5'),
            'text_width': data.get('text_settings', {}).get('text_width', '0.1'),
            'text_line_width': data.get('text_settings', {}).get('text_line_width', '1.8'),
        }
        self.settings_panel.set_settings(settings)
        
        # Clear existing rows
        for row in self.padstack_rows[:]:
            self.delete_padstack_row(row)
        for row in self.custom_layer_rows[:]:
            self.delete_custom_layer_row(row)
        for row in self.thermal_via_rows[:]:
            self.delete_thermal_via_row(row)
        
        # Add padstacks from data
        for pad_data in data.get('padstacks', []):
            self.add_padstack_row()
            self.padstack_rows[-1].set_data(pad_data)
        
        # Add custom layers from data
        for layer_data in data.get('custom_layers', []):
            self.add_custom_layer_row()
            self.custom_layer_rows[-1].set_data(layer_data)
        
        # Add thermal vias from data
        for via_data in data.get('thermal_vias', []):
            self.add_thermal_via_row()
            self.thermal_via_rows[-1].set_data(via_data)

    def generate_fiducial_padstack_name(self, fiducial_settings):
        """Generate fiducial padstack name based on settings"""
        try:
            diameter = to_decimal(fiducial_settings.get('fiducial_diameter', '1.0'))
            mask_opening = to_decimal(fiducial_settings.get('fiducial_mask_opening', '2.0'))
            keepout_diameter = to_decimal(fiducial_settings.get('fiducial_keepout_diameter', '3.0'))
            
            # Create name based on dimensions (in 0.1mm units)
            name = f"FID_C{int(diameter * 100)}"
            
            if mask_opening > diameter:
                mask_size = int(mask_opening * 100)
                name += f"_M{mask_size}"
                
            if keepout_diameter > mask_opening:
                keepout_size = int(keepout_diameter * 100)
                name += f"_K{keepout_size}"
                
            return name
        except (ValueError, TypeError):
            return "FID_C100_M200_K300"  # Default fiducial name

    def get_unique_padstack_names(self, include_fiducials=False):
        """Get list of unique padstack names used in the footprint"""
        data = self.get_footprint_data()
        unique_names = []
        seen_names = set()
        
        # Regular pads
        for pad in data.get('padstacks', []):
            pad_name = self.generate_pad_name_for_script(pad)
            if pad_name not in seen_names:
                unique_names.append(pad_name)
                seen_names.add(pad_name)
        
        # Add fiducials if enabled and requested
        if include_fiducials and data.get('fiducials_enabled', False):
            fiducial_settings = data.get('settings', {})
            fiducial_name = self.generate_fiducial_padstack_name(fiducial_settings)
            if fiducial_name not in seen_names:
                unique_names.append(fiducial_name)
                seen_names.add(fiducial_name)
        
        return unique_names



    def generate_footprint_script(self):
        """Generate script based on selected standard's tool"""
        # Get tool from settings panel standard instead of combo box
        if hasattr(self, 'settings_panel'):
            tool = self.settings_panel.tool_combo.currentText()
            
            # FIX: Use setCurrentText() instead of setItems()
            # setItems() doesn't exist in QComboBox
            self.script_combo.setCurrentText(tool)  # Sync for display
            
            # Rest of your existing generate_footprint_script logic...
            print(f"Generating script for tool: {tool}")
        else:
            QMessageBox.warning(self, "Error", "Please select a standard in Settings first")

    def generate_footprint_script(self):
        """Generate footprint script based on selected CAD tool"""
        cad_tool = self.script_combo.currentText()
        
        if cad_tool == "Altium":
            self.generate_altium_script()
        elif cad_tool == "Allegro":
            self.generate_allegro_script()
        elif cad_tool == "PADS":
            self.generate_pads_script()
        elif cad_tool == "Xpedition":
            self.generate_xpedition_script()



############################################################################### Altium script ###############################################################################################################




    def generate_altium_script(self):
        """Generate footprint script from current data and save to a text file"""
        data = self.get_footprint_data()
        settings = self.settings_panel.get_settings()
        account_settings = AccountManager.load_account_settings()

        body_layer_ui = settings.get('bodylayer', 'Top Assembly')
        courtyard_layer_ui = settings.get('courtyardlayer', 'Mechanical 15')
        text_layer_ui = settings.get('textlayer', 'Top Overlay')
        
        # Map to Altium script format
        body_layer = map_layer_to_altium(body_layer_ui)
        courtyard_layer = map_layer_to_altium(courtyard_layer_ui)
        text_layer = map_layer_to_altium(text_layer_ui)
        
        lines = []
        SCALE = Decimal('39.37')  # mm to mils conversion
        
        # GET ORIGIN OFFSET AND CHAMFER VALUES
        origin_offset_x = to_decimal(data.get('origin_offset_x', '0'))
        origin_offset_y = to_decimal(data.get('origin_offset_y', '0'))
        body_chamfer = to_decimal(data.get('body_chamfer', '0'))
        chamfer_corners = data.get('chamfer_corners', {})
        
        footprint_name = data.get('footprint_name', 'Unnamed')
        lines.append(f"StartFootprints\n\nFootprint (Name \"{footprint_name}\"),")
        
        # Body dimensions
        body_length = to_decimal(data.get('body_length', '0'))
        body_width = to_decimal(data.get('body_width', '0'))
        body_line_width = to_decimal(data.get('body_line_width', '0.05'))
        body_shape = data.get('body_shape', 'rectangle')
        
        # Calculate body corners with origin offset
        tl = (origin_offset_x, origin_offset_y)  # Top-left
        tr = (origin_offset_x + body_length, origin_offset_y)  # Top-right
        bl = (origin_offset_x, origin_offset_y - body_width)  # Bottom-left
        br = (origin_offset_x + body_length, origin_offset_y - body_width)  # Bottom-right
        
        # Generate body outline with chamfer support
        if body_shape == 'rectangle':
            if body_chamfer > 0 and any(chamfer_corners.values()):
                # Generate chamfered body outline
                self.generate_chamfered_body_altium(lines, tl, tr, bl, br, body_chamfer, 
                                                chamfer_corners, body_line_width, SCALE)
            else:
                # Standard rectangular body
                lines.append(f"Line (Width {body_line_width*SCALE}) (Start {(tl[0]*SCALE)}, {(tl[1]*SCALE)}) (End {(tr[0]*SCALE)}, {(tr[1]*SCALE)}) (Layer {body_layer})")
                lines.append(f"Line (Width {body_line_width*SCALE}) (Start {(bl[0]*SCALE)}, {(bl[1]*SCALE)}) (End {(tl[0]*SCALE)}, {(tl[1]*SCALE)}) (Layer {body_layer})")
                lines.append(f"Line (Width {body_line_width*SCALE}) (Start {(tr[0]*SCALE)}, {(tr[1]*SCALE)}) (End {(br[0]*SCALE)}, {(br[1]*SCALE)}) (Layer {body_layer})")
                lines.append(f"Line (Width {body_line_width*SCALE}) (Start {(br[0]*SCALE)}, {(br[1]*SCALE)}) (End {(bl[0]*SCALE)}, {(bl[1]*SCALE)}) (Layer {body_layer})")
        elif body_shape == 'round':
            # Round body shape
            radius = max(body_length, body_width) / Decimal('2')
            center_x = origin_offset_x + (body_length / Decimal('2'))
            center_y = origin_offset_y - (body_width / Decimal('2'))
            lines.append(f"Arc (Width {body_line_width*SCALE}) (Location {(center_x*SCALE)}, {(center_y*SCALE)}) (Radius {(radius*SCALE)}) (StartAngle 0) (EndAngle 360) (Layer {body_layer})")
        
        # Generate pads (existing pad generation code continues here)
        pads = data.get('padstacks', [])
        resolver = PadPositionResolver(pads)
        
        # Calculate pad bounds for silkscreen gap calculation
        pad_bounds_list = []
        for pad in pads:
            abs_x, abs_y = resolver.get_absolute_position(pad)
            pad_bounds = self.calculate_pad_bounds_for_script(pad, abs_x, abs_y)
            if pad_bounds:
                pad_bounds_list.append(pad_bounds)
        
        # Generate enhanced silkscreen with chamfer support
        if data.get('silkscreen_enabled', True):
            silkscreen_gap = to_decimal(data.get('silkscreen_airgap', '0.15'))
            silkscreen_line_width = to_decimal(data.get('silkscreen_line_width', '0.15'))
            follow_chamfer = data.get('silkscreen_follow_chamfer', False)
            
            if body_shape == 'rectangle':
                if follow_chamfer and body_chamfer > 0 and any(chamfer_corners.values()):
                    # Generate chamfered silkscreen
                    self.generate_chamfered_silkscreen_altium(lines, tl, tr, bl, br, body_chamfer, 
                                                            chamfer_corners, pad_bounds_list, 
                                                            silkscreen_gap, silkscreen_line_width, SCALE)
                else:
                    # Standard rectangular silkscreen with gaps
                    self.generate_standard_silkscreen_altium(lines, tl, tr, bl, br, pad_bounds_list, 
                                                        silkscreen_gap, silkscreen_line_width, SCALE)
            elif body_shape == 'round':
                # Round silkscreen (implement as needed)
                pass
        
        # Continue with rest of script generation (courtyard, pads, etc.)
        # ... (rest of existing script generation code)

        # Generate pads and collect pad bounds
        pads = data.get('padstacks', [])
        resolver = PadPositionResolver(pads)
        
        # Collect pad bounds for silkscreen gap calculation
        pad_bounds_list = []
        for pad in pads:
            abs_x, abs_y = resolver.get_absolute_position(pad)
            pad_bounds = self.calculate_pad_bounds_for_script(pad, abs_x, abs_y)
            if pad_bounds:
                pad_bounds_list.append(pad_bounds)

        # Helper function for merging intervals
        def merge_intervals(intervals):
            """Merge overlapping intervals in the form [(start, end), ...]"""
            if not intervals:
                return []
            intervals = sorted(intervals, key=lambda x: x[0])
            merged = [intervals[0]]
            for current in intervals[1:]:
                last = merged[-1]
                if current[0] <= last[1]:
                    merged[-1] = (last[0], max(last[1], current[1]))
                else:
                    merged.append(current)
            return merged

        # Add the silkscreen generation function
        def generate_silkscreen_lines_with_gaps(x1, y1, x2, y2, pad_bounds_list, gap, orientation):
            segments = []
            if orientation == 'horizontal':
                start_pos = min(x1, x2)
                end_pos = max(x1, x2)
                line_y = y1
                intersections = []
                
                for (px_min, py_min, px_max, py_max) in pad_bounds_list:
                    # Expand pad bounds by airgap
                    pad_min_x = px_min - gap
                    pad_max_x = px_max + gap
                    pad_min_y = py_min - gap
                    pad_max_y = py_max + gap
                    
                    # Check if horizontal line intersects with expanded pad
                    if (pad_min_y <= line_y <= pad_max_y and 
                        pad_max_x >= start_pos and pad_min_x <= end_pos):
                        inter_start = max(start_pos, pad_min_x)
                        inter_end = min(end_pos, pad_max_x)
                        intersections.append((inter_start, inter_end))
                
                # Merge overlapping intersections
                merged = merge_intervals(intersections)
                
                # Generate line segments between gaps
                current_pos = start_pos
                for gap_start, gap_end in merged:
                    if current_pos < gap_start:
                        segments.append((current_pos, line_y, gap_start, line_y))
                    current_pos = gap_end
                if current_pos < end_pos:
                    segments.append((current_pos, line_y, end_pos, line_y))
                    
            else:  # vertical
                start_pos = min(y1, y2)
                end_pos = max(y1, y2)
                line_x = x1
                intersections = []
                
                for (px_min, py_min, px_max, py_max) in pad_bounds_list:
                    # Expand pad bounds by airgap
                    pad_min_x = px_min - gap
                    pad_max_x = px_max + gap
                    pad_min_y = py_min - gap
                    pad_max_y = py_max + gap
                    
                    # Check if vertical line intersects with expanded pad
                    if (pad_min_x <= line_x <= pad_max_x and 
                        pad_max_y >= start_pos and pad_min_y <= end_pos):
                        inter_start = max(start_pos, pad_min_y)
                        inter_end = min(end_pos, pad_max_y)
                        intersections.append((inter_start, inter_end))
                
                # Merge overlapping intersections
                merged = merge_intervals(intersections)
                
                # Generate line segments between gaps
                current_pos = start_pos
                for gap_start, gap_end in merged:
                    if current_pos < gap_start:
                        segments.append((line_x, current_pos, line_x, gap_start))
                    current_pos = gap_end
                if current_pos < end_pos:
                    segments.append((line_x, current_pos, line_x, end_pos))
                    
            return segments

        # Generate silkscreen with gaps if enabled
        if data.get('silkscreen_enabled', True):
            silkscreen_gap1 = to_decimal(data.get('silkscreen_airgap', '0.15'))
            silkscreen_line_width = to_decimal(data.get('silkscreen_line_width', '0.15'))
            silkscreen_gap = silkscreen_gap1+(silkscreen_line_width/2)  
            # Generate silkscreen lines with gaps for each side of body rectangle
            silk_lines = []
            # Top line (from top-left to top-right)
            silk_lines += generate_silkscreen_lines_with_gaps(tl[0], tl[1], tr[0], tr[1], pad_bounds_list, silkscreen_gap, 'horizontal')
            # Bottom line (from bottom-left to bottom-right)
            silk_lines += generate_silkscreen_lines_with_gaps(bl[0], bl[1], br[0], br[1], pad_bounds_list, silkscreen_gap, 'horizontal')
            # Left line (from bottom-left to top-left)
            silk_lines += generate_silkscreen_lines_with_gaps(bl[0], bl[1], tl[0], tl[1], pad_bounds_list, silkscreen_gap, 'vertical')
            # Right line (from bottom-right to top-right)
            silk_lines += generate_silkscreen_lines_with_gaps(br[0], br[1], tr[0], tr[1], pad_bounds_list, silkscreen_gap, 'vertical')
            
            # Add silkscreen segment lines to script
            for (x1_, y1_, x2_, y2_) in silk_lines:
                lines.append(f"Line (Width {silkscreen_line_width * SCALE}) (Start {(x1_*SCALE)}, {(y1_*SCALE)}) (End {(x2_*SCALE)}, {(y2_*SCALE)}) (Layer TopOverlay)")



        # Generate DFA Bond Layer - SINGLE UNIFIED POLYGON
        if hasattr(self, 'renderer') and hasattr(self.renderer, 'show_dfa_bond_checkbox') and self.renderer.show_dfa_bond_checkbox.isChecked():
            lines.append("")
            lines.append("; ===== DFA BOND LAYER (SINGLE UNIFIED POLYGON) =====")
            
            dfa_expansion = Decimal('0.1')  # Fixed 0.1mm expansion
            dfa_layer = "Mechanical2"  # Layer for DFA bond
            
            # Calculate body bounds for DFA
            body_bounds_dfa = None
            if body_length > 0 and body_width > 0:
                body_bounds_dfa = [
                    origin_offset_x,                    # min_x
                    origin_offset_y - body_width,       # min_y  
                    origin_offset_x + body_length,      # max_x
                    origin_offset_y                     # max_y
                ]
            
            if body_bounds_dfa and hasattr(self, 'renderer'):
                pad_bounds_list = self.renderer.get_individual_pad_bounds_absolute()
                
                # Create QPainterPath for unified polygon
                from PyQt6.QtGui import QPainterPath
                from PyQt6.QtCore import QRectF
                
                unified_path = QPainterPath()
                has_extending_portions = False
                
                for pad_bounds in pad_bounds_list:
                    if not pad_bounds:
                        continue
                    
                    pad_min_x, pad_min_y, pad_max_x, pad_max_y = pad_bounds
                    
                    # Check if pad extends outside body
                    extends_left = pad_min_x < body_bounds_dfa[0]
                    extends_right = pad_max_x > body_bounds_dfa[2]
                    extends_bottom = pad_min_y < body_bounds_dfa[1]
                    extends_top = pad_max_y > body_bounds_dfa[3]
                    
                    # Skip pads completely inside body
                    if not (extends_left or extends_right or extends_bottom or extends_top):
                        continue
                    
                    has_extending_portions = True
                    
                    # Create path for this pad's extending portions
                    pad_extending_path = QPainterPath()
                    
                    if extends_left:
                        # Left extension
                        ext_rect = QRectF(
                            float(pad_min_x - dfa_expansion),
                            float(max(pad_min_y, body_bounds_dfa[1]) - dfa_expansion),
                            float(body_bounds_dfa[0] - pad_min_x + dfa_expansion),
                            float(min(pad_max_y, body_bounds_dfa[3]) - max(pad_min_y, body_bounds_dfa[1]) + 2*dfa_expansion)
                        )
                        pad_extending_path.addRect(ext_rect)
                    
                    if extends_right:
                        # Right extension
                        ext_rect = QRectF(
                            float(body_bounds_dfa[2]),
                            float(max(pad_min_y, body_bounds_dfa[1]) - dfa_expansion),
                            float(pad_max_x - body_bounds_dfa[2] + dfa_expansion),
                            float(min(pad_max_y, body_bounds_dfa[3]) - max(pad_min_y, body_bounds_dfa[1]) + 2*dfa_expansion)
                        )
                        pad_extending_path.addRect(ext_rect)
                    
                    if extends_bottom:
                        # Bottom extension
                        ext_rect = QRectF(
                            float(max(pad_min_x, body_bounds_dfa[0]) - dfa_expansion),
                            float(pad_min_y - dfa_expansion),
                            float(min(pad_max_x, body_bounds_dfa[2]) - max(pad_min_x, body_bounds_dfa[0]) + 2*dfa_expansion),
                            float(body_bounds_dfa[1] - pad_min_y + dfa_expansion)
                        )
                        pad_extending_path.addRect(ext_rect)
                    
                    if extends_top:
                        # Top extension
                        ext_rect = QRectF(
                            float(max(pad_min_x, body_bounds_dfa[0]) - dfa_expansion),
                            float(body_bounds_dfa[3]),
                            float(min(pad_max_x, body_bounds_dfa[2]) - max(pad_min_x, body_bounds_dfa[0]) + 2*dfa_expansion),
                            float(pad_max_y - body_bounds_dfa[3] + dfa_expansion)
                        )
                        pad_extending_path.addRect(ext_rect)
                    
                    # Handle corner extensions
                    if extends_left and extends_bottom:
                        corner_rect = QRectF(
                            float(pad_min_x - dfa_expansion),
                            float(pad_min_y - dfa_expansion),
                            float(body_bounds_dfa[0] - pad_min_x + dfa_expansion),
                            float(body_bounds_dfa[1] - pad_min_y + dfa_expansion)
                        )
                        pad_extending_path.addRect(corner_rect)
                    
                    if extends_right and extends_bottom:
                        corner_rect = QRectF(
                            float(body_bounds_dfa[2]),
                            float(pad_min_y - dfa_expansion),
                            float(pad_max_x - body_bounds_dfa[2] + dfa_expansion),
                            float(body_bounds_dfa[1] - pad_min_y + dfa_expansion)
                        )
                        pad_extending_path.addRect(corner_rect)
                    
                    if extends_left and extends_top:
                        corner_rect = QRectF(
                            float(pad_min_x - dfa_expansion),
                            float(body_bounds_dfa[3]),
                            float(body_bounds_dfa[0] - pad_min_x + dfa_expansion),
                            float(pad_max_y - body_bounds_dfa[3] + dfa_expansion)
                        )
                        pad_extending_path.addRect(corner_rect)
                    
                    if extends_right and extends_top:
                        corner_rect = QRectF(
                            float(body_bounds_dfa[2]),
                            float(body_bounds_dfa[3]),
                            float(pad_max_x - body_bounds_dfa[2] + dfa_expansion),
                            float(pad_max_y - body_bounds_dfa[3] + dfa_expansion)
                        )
                        pad_extending_path.addRect(corner_rect)
                    
                    # Union this pad's extending portions with the overall path
                    unified_path = unified_path.united(pad_extending_path)
                
                # Generate single polygon from unified path
                if has_extending_portions and not unified_path.isEmpty():
                    # Simplify the path to get clean outline
                    simplified_path = unified_path.simplified()
                    
                    # Convert to polygon points
                    polygon_points = simplified_path.toFillPolygon()
                    
                    if len(polygon_points) > 2:
                        lines.append(f"Polygon (PointCount {len(polygon_points)}) (Layer {dfa_layer})")
                        
                        for point in polygon_points:
                            x_scaled = float(point.x() * SCALE)
                            y_scaled = float(point.y() * SCALE)
                            lines.append(f"Point ({x_scaled:.1f}, {y_scaled:.1f})")
                        
                        lines.append("EndPolygon")
                    else:
                        lines.append(f"; DFA polygon has insufficient points - not generated")
                else:
                    lines.append(f"; No extending pads found - DFA bond layer not generated")




        # Generate Courtyard Layer - Updated to support round courtyards
        base_expansion = to_decimal(data.get('courtyard_expansion', '0.25'))
        courtyard_line_width = to_decimal(data.get('courtyard_line_width', '0.1'))
        body_line_width = to_decimal(data.get('body_line_width', '0.05'))
        
        # Check if body is round
        if body_shape == 'round' and body_length > 0 and body_width > 0:
            # Round courtyard for round body
            radius = max(body_length, body_width) / Decimal('2')
            center_x = origin_offset_x + (body_length / Decimal('2'))
            center_y = origin_offset_y - (body_width / Decimal('2'))
            
            # Check if pads extend beyond body circle
            max_pad_distance = Decimal('0')
            if pad_bounds_list:
                for pad_bounds in pad_bounds_list:
                    if pad_bounds:
                        px_min, py_min, px_max, py_max = [to_decimal(str(coord)) for coord in pad_bounds]
                        # Check all corners of pad bounds
                        pad_corners = [(px_min, py_min), (px_max, py_min), (px_max, py_max), (px_min, py_max)]
                        for corner_x, corner_y in pad_corners:
                            distance = ((corner_x - center_x)**2 + (corner_y - center_y)**2).sqrt()
                            max_pad_distance = max(max_pad_distance, distance)
            
            # Determine courtyard radius
            if max_pad_distance > radius:
                # Pads extend beyond body - use pad-based expansion
                courtyard_radius = max_pad_distance + base_expansion + (courtyard_line_width / Decimal('2'))
            else:
                # Body is outermost - use body-based expansion
                courtyard_radius = radius + base_expansion + (courtyard_line_width / Decimal('2')) + (body_line_width / Decimal('2'))
            
            # Draw circular courtyard
            lines.append(f"Arc (Width {courtyard_line_width*SCALE}) (Location {center_x*SCALE}, {center_y*SCALE}) (Radius {courtyard_radius*SCALE}) (StartAngle 0) (EndAngle 360) (Layer {courtyard_layer})")
        
        else:

            courtyard_line_W = courtyard_line_width / 2
            body_line_w = body_line_width / 2
            body_linecourtyard = courtyard_line_W + body_line_w

            # Calculate pad bounds for courtyard (same as renderer)
            pad_bounds_list = []
            for pad in pads:
                abs_x, abs_y = resolver.get_absolute_position(pad)
                pad_bounds = self.calculate_pad_bounds_for_script(pad, abs_x, abs_y)
                if pad_bounds:
                    pad_bounds_list.append(pad_bounds)

            # Calculate overall pad bounds
            pad_bounds_for_courtyard = None
            if pad_bounds_list:
                min_x = min(pb[0] for pb in pad_bounds_list)
                min_y = min(pb[1] for pb in pad_bounds_list)
                max_x = max(pb[2] for pb in pad_bounds_list)
                max_y = max(pb[3] for pb in pad_bounds_list)
                pad_bounds_for_courtyard = [min_x, min_y, max_x, max_y]

            # Body bounds with origin offset applied
            body_bounds_adjusted = [
                tl[0],  # min_x (left edge)
                bl[1],  # min_y (bottom edge)
                tr[0],  # max_x (right edge)
                tl[1]   # max_y (top edge)
            ]

            # Determine outermost bounds for each side separately
            outermost_left = None
            outermost_right = None
            outermost_top = None
            outermost_bottom = None
            outermost_bounds_type_left = None
            outermost_bounds_type_right = None
            outermost_bounds_type_top = None
            outermost_bounds_type_bottom = None

            if body_bounds_adjusted and pad_bounds_for_courtyard:
                # Left side
                if body_bounds_adjusted[0] <= pad_bounds_for_courtyard[0]:
                    outermost_left = body_bounds_adjusted[0]
                    outermost_bounds_type_left = 'body'
                else:
                    outermost_left = pad_bounds_for_courtyard[0]
                    outermost_bounds_type_left = 'pad'
                
                # Right side
                if body_bounds_adjusted[2] >= pad_bounds_for_courtyard[2]:
                    outermost_right = body_bounds_adjusted[2]
                    outermost_bounds_type_right = 'body'
                else:
                    outermost_right = pad_bounds_for_courtyard[2]
                    outermost_bounds_type_right = 'pad'
                
                # Bottom side
                if body_bounds_adjusted[1] <= pad_bounds_for_courtyard[1]:
                    outermost_bottom = body_bounds_adjusted[1]
                    outermost_bounds_type_bottom = 'body'
                else:
                    outermost_bottom = pad_bounds_for_courtyard[1]
                    outermost_bounds_type_bottom = 'pad'
                
                # Top side
                if body_bounds_adjusted[3] >= pad_bounds_for_courtyard[3]:
                    outermost_top = body_bounds_adjusted[3]
                    outermost_bounds_type_top = 'body'
                else:
                    outermost_top = pad_bounds_for_courtyard[3]
                    outermost_bounds_type_top = 'pad'

            elif body_bounds_adjusted:
                outermost_left = body_bounds_adjusted[0]
                outermost_right = body_bounds_adjusted[2]
                outermost_bottom = body_bounds_adjusted[1]
                outermost_top = body_bounds_adjusted[3]
                outermost_bounds_type_left = outermost_bounds_type_right = outermost_bounds_type_top = outermost_bounds_type_bottom = 'body'

            elif pad_bounds_for_courtyard:
                outermost_left = pad_bounds_for_courtyard[0]
                outermost_right = pad_bounds_for_courtyard[2]
                outermost_bottom = pad_bounds_for_courtyard[1]
                outermost_top = pad_bounds_for_courtyard[3]
                outermost_bounds_type_left = outermost_bounds_type_right = outermost_bounds_type_top = outermost_bounds_type_bottom = 'pad'

            if outermost_left is not None:
                # Calculate expansion for each side based on what's outermost on that side
                expansion_left = base_expansion
                if outermost_bounds_type_left == 'pad':
                    expansion_left += courtyard_line_W
                elif outermost_bounds_type_left == 'body':
                    expansion_left += body_linecourtyard

                expansion_right = base_expansion
                if outermost_bounds_type_right == 'pad':
                    expansion_right += courtyard_line_W
                elif outermost_bounds_type_right == 'body':
                    expansion_right += body_linecourtyard

                expansion_bottom = base_expansion
                if outermost_bounds_type_bottom == 'pad':
                    expansion_bottom += courtyard_line_W
                elif outermost_bounds_type_bottom == 'body':
                    expansion_bottom += body_linecourtyard

                expansion_top = base_expansion
                if outermost_bounds_type_top == 'pad':
                    expansion_top += courtyard_line_W
                elif outermost_bounds_type_top == 'body':
                    expansion_top += body_linecourtyard

                # Calculate courtyard bounds with separate expansions for each side
                courtyard_bounds = [
                    outermost_left - expansion_left,      # min_x (left)
                    outermost_bottom - expansion_bottom,  # min_y (bottom)
                    outermost_right + expansion_right,    # max_x (right) 
                    outermost_top + expansion_top         # max_y (top)
                ]
                
                courtyard_bl = (courtyard_bounds[0], courtyard_bounds[1])

                # Generate courtyard rectangle with each side calculated separately
                lines.append(f"Line (Width {(courtyard_line_width*SCALE)}) (Start {(courtyard_bounds[0]*SCALE)}, {(courtyard_bounds[3]*SCALE)}) (End {(courtyard_bounds[2]*SCALE)}, {(courtyard_bounds[3]*SCALE)}) (Layer {courtyard_layer})")  # Top
                lines.append(f"Line (Width {(courtyard_line_width*SCALE)}) (Start {(courtyard_bounds[0]*SCALE)}, {(courtyard_bounds[1]*SCALE)}) (End {(courtyard_bounds[0]*SCALE)}, {(courtyard_bounds[3]*SCALE)}) (Layer {courtyard_layer})")  # Left
                lines.append(f"Line (Width {(courtyard_line_width*SCALE)}) (Start {(courtyard_bounds[2]*SCALE)}, {(courtyard_bounds[1]*SCALE)}) (End {(courtyard_bounds[2]*SCALE)}, {(courtyard_bounds[3]*SCALE)}) (Layer {courtyard_layer})")  # Right
                lines.append(f"Line (Width {(courtyard_line_width*SCALE)}) (Start {(courtyard_bounds[0]*SCALE)}, {(courtyard_bounds[1]*SCALE)}) (End {(courtyard_bounds[2]*SCALE)}, {(courtyard_bounds[1]*SCALE)}) (Layer {courtyard_layer})")  # Bottom



        # Generate Fiducials
        # Generate Fiducials with proper padstack names
        if data.get('fiducials_enabled', False):
            fiducial_settings = data.get('settings', {})
            fiducial_padstack_name = self.generate_fiducial_padstack_name(fiducial_settings)
            
            fid_diameter = to_decimal(fiducial_settings.get('fiducial_diameter', '1.0'))
            fid_mask = to_decimal(fiducial_settings.get('fiducial_mask_opening', '2.0'))
            fid_keepout = to_decimal(fiducial_settings.get('fiducial_keepout_diameter', '3.0'))
            fid_x_offset = to_decimal(fiducial_settings.get('fiducial_x_offset', '2.0'))
            fid_y_offset = to_decimal(fiducial_settings.get('fiducial_y_offset', '2.0'))

            # Calculate fiducial positions
            body_length = to_decimal(data.get('body_length', '5.0'))
            body_width = to_decimal(data.get('body_width', '3.0'))
            
            # Body corners with origin offset
            tr = (origin_offset_x + body_length, origin_offset_y)  # Top-right
            bl = (origin_offset_x, origin_offset_y - body_width)   # Bottom-left

            # Fiducial positions
            fid_positions = [
                (tr[0] + fid_x_offset, tr[1] + fid_y_offset, "FID1"),  # Top-right
                (bl[0] - fid_x_offset, bl[1] - fid_y_offset, "FID2"),  # Bottom-left
            ]

            for fid_x, fid_y, fid_name in fid_positions:
                # Create fiducial pad with proper padstack reference
                lines.append(f"Pad (Name \"{fid_name}\") (Location {fid_x*SCALE}, {fid_y*SCALE}) (Surface True) (Rotation 0) (ExpandMask {fid_mask*SCALE}) (ExpandPaste 0.0)")
                lines.append(f"PadShape (Size {fid_diameter*SCALE}, {fid_diameter*SCALE}) (Shape Round) (Layer Top)")
                lines.append("EndPad")
                
                # Add keepout area
                lines.append(f"Arc (Width 1.0) (Location {(fid_x*SCALE)}, {(fid_y*SCALE)}) (Radius {fid_keepout*SCALE}) (StartAngle 0) (EndAngle 360) (KeepOut True) (Layer mechanical13)")
            # [Rest of the function remains the same - pads, custom layers, thermal vias, text generation]
        # Collect unique padstack names
        unique_names = []
        seen_names = set()
        for pad in pads:
            pad_name = self.generate_pad_name_for_script(pad)
            if pad_name not in seen_names:
                unique_names.append(pad_name)
                seen_names.add(pad_name)

        # Get text settings
        text_height = to_decimal(settings.get('text_height', '0.5')) * SCALE
        text_width = to_decimal(settings.get('text_width', '0.1')) * SCALE
        text_line_width = to_decimal(settings.get('text_line_width', '1.8'))

        # Calculate position below courtyard for text
        base_y = (courtyard_bl[1] - Decimal('1')) * SCALE  # Below courtyard

        for pad in pads:
            pad_type = pad.get('type', 'square')
            name = pad.get('pin_number', '1')
            abs_x, abs_y = resolver.get_absolute_position(pad)
            rotation = 0

            expand_mask = to_decimal(pad.get('mask_expansion', '0'))
            expand_paste = to_decimal(pad.get('paste_expansion', '0'))

            # Check if mask/paste are enabled
            mask_enabled = pad.get('mask_enabled', True)
            paste_enabled = pad.get('paste_enabled', True)
            
            if not mask_enabled:
                expand_mask = Decimal('0')
            if not paste_enabled:
                expand_paste = Decimal('0')

            surface = 'True' if pad_type not in ['PTH', 'NPTH', 'PTH_oblong', 'NPTH_oblong', 'PTH_rectangle'] else 'False'

            if pad_type == 'square':
                size = to_decimal(pad.get('size', '1'))
                lines.append(f"Pad (Name \"{name}\") (Location {(abs_x*SCALE)}, {(abs_y*SCALE)}) (Surface {surface}) (Rotation {rotation}) (ExpandMask {(expand_mask*SCALE)}) (ExpandPaste {(expand_paste*SCALE)})")
                lines.append(f"PadShape (Size {(size*SCALE)}, {(size*SCALE)}) (Shape Rectangular) (Layer Top)")
                lines.append("EndPad")

            elif pad_type == 'rectangle':
                length = to_decimal(pad.get('length', '1'))
                width = to_decimal(pad.get('width', '1'))
                lines.append(f"Pad (Name \"{name}\") (Location {abs_x*SCALE}, {abs_y*SCALE}) (Surface {surface}) (Rotation {rotation}) (ExpandMask {expand_mask*SCALE}) (ExpandPaste {expand_paste*SCALE})")
                lines.append(f"PadShape (Size {length*SCALE}, {(width*SCALE)}) (Shape Rectangular) (Layer Top)")
                lines.append("EndPad")

            elif pad_type == 'SMD-oblong':
                length = to_decimal(pad.get('length', '1'))
                width = to_decimal(pad.get('width', '1'))
                lines.append(f"Pad (Name \"{name}\") (Location {(abs_x*SCALE)}, {(abs_y*SCALE)}) (Surface {surface}) (Rotation {rotation}) (ExpandMask {(expand_mask*SCALE)}) (ExpandPaste {(expand_paste*SCALE)})")
                lines.append(f"PadShape (Size {(length*SCALE)}, {(width*SCALE)}) (Shape Rounded) (Layer Top)")
                lines.append("EndPad")

            elif pad_type == 'rounded_rectangle':
                length = to_decimal(pad.get('length', '1'))
                width = to_decimal(pad.get('width', '1'))
                lines.append(f"Pad (Name \"{name}\") (Location {(abs_x*SCALE)}, {(abs_y*SCALE)}) (Surface {surface}) (Rotation {rotation}) (ExpandMask {(expand_mask*SCALE)}) (ExpandPaste {(expand_paste*SCALE)})")
                lines.append(f"PadShape (Size {(length*SCALE)}, {(width*SCALE)}) (Shape RoundedRectangular) (Layer Top)")
                lines.append("EndPad")

            elif pad_type in ['round', 'D-shape']:
                diameter = to_decimal(pad.get('diameter', '1'))
                lines.append(f"Pad (Name \"{name}\") (Location {(abs_x*SCALE)}, {(abs_y*SCALE)}) (Surface {surface}) (Rotation {rotation}) (ExpandMask {(expand_mask*SCALE)}) (ExpandPaste {(expand_paste*SCALE)})")
                lines.append(f"PadShape (Size {(diameter*SCALE)}, {(diameter*SCALE)}) (Shape Rounded) (Layer Top)")
                lines.append("EndPad")

            elif pad_type in ['PTH', 'NPTH']:
                hole_diameter = to_decimal(pad.get('hole_diameter', '0.8'))
                lines.append(f"Pad (Name \"{name}\") (Location {(abs_x*SCALE)}, {(abs_y*SCALE)}) (Slotted False) (HoleSize {(hole_diameter*SCALE)}) (Surface {surface}) (Rotation {rotation}) (ExpandMask {(expand_mask*SCALE)}) (ExpandPaste {(expand_paste*SCALE)})")
                
                if pad_type == 'PTH':
                    pad_diameter = to_decimal(pad.get('pad_diameter', '1.2'))
                    lines.append(f"PadShape (Size {(pad_diameter*SCALE)}, {(pad_diameter*SCALE)}) (Shape Rounded) (Layer Top)")
                    lines.append(f"PadShape (Size {(pad_diameter*SCALE)}, {(pad_diameter*SCALE)}) (Shape Rounded) (Layer Bottom)")
                lines.append("EndPad")

            elif pad_type in ['PTH_oblong', 'NPTH_oblong']:
                hole_length = to_decimal(pad.get('hole_length', '1.5'))
                hole_width = to_decimal(pad.get('hole_width', '0.8'))
                pad_rotation = to_decimal(pad.get('rotation', '0'))
                
                lines.append(f"Pad (Name \"{name}\") (Location {(abs_x*SCALE)}, {(abs_y*SCALE)}) (Slotted True) (SlotWidth {(hole_width*SCALE)}) (SlotHeight {(hole_length*SCALE)}) (Surface {surface}) (Rotation {(pad_rotation)}) (ExpandMask {(expand_mask*SCALE)}) (ExpandPaste {(expand_paste*SCALE)})")
                
                if pad_type == 'PTH_oblong':
                    pad_length = to_decimal(pad.get('pad_length', '2.0'))
                    pad_width = to_decimal(pad.get('pad_width', '1.2'))
                    lines.append(f"PadShape (Size {(pad_length*SCALE)}, {(pad_width*SCALE)}) (Shape Rounded) (Layer Top)")
                    lines.append(f"PadShape (Size {(pad_length*SCALE)}, {(pad_width*SCALE)}) (Shape Rounded) (Layer Bottom)")
                lines.append("EndPad")

            elif pad_type == 'PTH_rectangle':
                hole_length = to_decimal(pad.get('hole_length', '1.5'))
                hole_width = to_decimal(pad.get('hole_width', '0.8'))
                pad_length = to_decimal(pad.get('pad_length', '2.0'))
                pad_width = to_decimal(pad.get('pad_width', '1.2'))
                pad_rotation = to_decimal(pad.get('rotation', '0'))
                
                lines.append(f"Pad (Name \"{name}\") (Location {(abs_x*SCALE)}, {(abs_y*SCALE)}) (Slotted True) (SlotWidth {(hole_width*SCALE)}) (SlotHeight {(hole_length*SCALE)}) (Surface {surface}) (Rotation {(pad_rotation)}) (ExpandMask {(expand_mask*SCALE)}) (ExpandPaste {(expand_paste*SCALE)})")
                lines.append(f"PadShape (Size {(pad_length*SCALE)}, {(pad_width*SCALE)}) (Shape Rectangular) (Layer Top)")
                lines.append(f"PadShape (Size {(pad_length*SCALE)}, {(pad_width*SCALE)}) (Shape Rectangular) (Layer Bottom)")
                lines.append("EndPad")

            elif pad_type == 'custom':
                # Generate custom polygon using actual polygon points
                polygon_points = self.renderer.calculate_polygon_points_absolute(pad, abs_x, abs_y)
                
                if polygon_points and len(polygon_points) >= 3:
                    # Convert polygon points to scaled coordinates
                    scaled_points = [((p.x() * SCALE), (p.y() * SCALE)) for p in polygon_points]
                    point_count = len(scaled_points)
                    
                    # Generate copper layer polygon (TopLayer)
                    lines.append(f"Polygon (PointCount {point_count}) (Layer TopLayer)")
                    for px, py in scaled_points:
                        lines.append(f"Point ({px}, {py})")
                    lines.append("EndPolygon")
                    
                    # Generate mask layer polygon (TopSolder) if mask enabled and has expansion
                    if mask_enabled and expand_mask != Decimal('0'):
                        expanded_points = self.renderer.expand_polygon_uniformly(polygon_points, expand_mask)
                        if expanded_points:
                            scaled_mask_points = [((p.x() * SCALE), (p.y() * SCALE)) for p in expanded_points]
                            mask_point_count = len(scaled_mask_points)
                            lines.append(f"Polygon (PointCount {mask_point_count}) (Layer TopSolder)")
                            for px, py in scaled_mask_points:
                                lines.append(f"Point ({px}, {py})")
                            lines.append("EndPolygon")
                    
                    # Generate paste layer polygon (TopPaste) if paste enabled and has expansion
                    if paste_enabled and expand_paste != Decimal('0'):
                        expanded_points = self.renderer.expand_polygon_uniformly(polygon_points, expand_paste)
                        if expanded_points:
                            scaled_paste_points = [((p.x() * SCALE), (p.y() * SCALE)) for p in expanded_points]
                            paste_point_count = len(scaled_paste_points)
                            lines.append(f"Polygon (PointCount {paste_point_count}) (Layer TopPaste)")
                            for px, py in scaled_paste_points:
                                lines.append(f"Point ({px}, {py})")
                            lines.append("EndPolygon")
                else:
                    # Fallback to simple rectangle if polygon calculation fails
                    lines.append(f"Pad (Name \"{name}\") (Location {(abs_x*SCALE)}, {(abs_y*SCALE)}) (Surface {surface}) (Rotation {rotation})")
                    lines.append(f"PadShape (Size {(Decimal('1.0')*SCALE)}, {(Decimal('1.0')*SCALE)}) (Shape Rectangular) (Layer Top)")
                    lines.append("EndPad")

        # Generate Custom Layers
        custom_layers = data.get('custom_layers', [])
        for layer in custom_layers:
            layer_type = layer.get('layer', 'mask')
            shape = layer.get('shape', 'rectangle')
            
            x_offset = to_decimal(layer.get('x_offset', '0'))
            y_offset = to_decimal(layer.get('y_offset', '0'))

            # Handle offset_from (simplified)
            offset_from = layer.get('offset_from', 'origin')
            if offset_from != 'origin':
                # Add logic to resolve reference positions if needed
                pass

            # Determine Altium layer based on type
            altium_layer = "TopSolder" if layer_type == "mask" else "TopPaste" if layer_type == "paste" else "Mechanical1"

            if shape == 'rectangle':
                length = to_decimal(layer.get('length', '1'))
                width = to_decimal(layer.get('width', '1'))
                
                # Draw rectangle
                x1, y1 = (x_offset - length/Decimal('2')) * SCALE, (y_offset - width/Decimal('2')) * SCALE
                x2, y2 = (x_offset + length/Decimal('2')) * SCALE, (y_offset + width/Decimal('2')) * SCALE
                lines.append(f"Line (Width 0.1) (Start {(x1)}, {(y1)}) (End {(x2)}, {(y1)}) (Layer {altium_layer})")
                lines.append(f"Line (Width 0.1) (Start {(x2)}, {(y1)}) (End {(x2)}, {(y2)}) (Layer {altium_layer})")
                lines.append(f"Line (Width 0.1) (Start {(x2)}, {(y2)}) (End {(x1)}, {(y2)}) (Layer {altium_layer})")
                lines.append(f"Line (Width 0.1) (Start {(x1)}, {(y2)}) (End {(x1)}, {(y1)}) (Layer {altium_layer})")

        # Generate Thermal Vias
        thermal_vias = data.get('thermal_vias', [])
        for via in thermal_vias:
            via_type = via.get('type', 'single')
            
            x_offset = to_decimal(via.get('x_offset', '0'))
            y_offset = to_decimal(via.get('y_offset', '0'))

            # Handle offset_from (simplified)
            offset_from = via.get('offset_from', 'origin')
            if offset_from != 'origin':
                # Add logic to resolve reference positions if needed
                pass

            if via_type == 'single':
                via_diameter = to_decimal(via.get('via_diameter', '0.2'))
                drill_diameter = to_decimal(via.get('drill_diameter', '0.1'))

                lines.append(f"Via (Location {(x_offset*SCALE)}, {(y_offset*SCALE)}) (Size {(via_diameter*SCALE)}) (DrillSize {(drill_diameter*SCALE)})")

            elif via_type == 'grid_array':
                rows = int(via.get('rows', 2))
                columns = int(via.get('columns', 2))
                row_spacing = to_decimal(via.get('row_spacing', '1.0'))
                col_spacing = to_decimal(via.get('col_spacing', '1.0'))
                via_diameter = to_decimal(via.get('via_diameter', '0.2'))
                drill_diameter = to_decimal(via.get('drill_diameter', '0.1'))

                # Use Decimal arithmetic for grid calculations
                start_x = x_offset - (Decimal(str(columns - 1)) * col_spacing / Decimal('2'))
                start_y = y_offset - (Decimal(str(rows - 1)) * row_spacing / Decimal('2'))

                # Collect unique padstack names (including fiducials)
                unique_names = self.get_unique_padstack_names(include_fiducials=True)

                # Get text settings
                text_height = to_decimal(settings.get('text_height', '0.5')) * SCALE
                text_width = to_decimal(settings.get('text_width', '0.1')) * SCALE
                text_line_width = to_decimal(settings.get('text_line_width', '1.8'))

                # Calculate position below courtyard for text
                base_expansion = to_decimal(data.get('courtyard_expansion', '0.25'))
                
                # Calculate courtyard bottom (simplified)
                body_bottom = origin_offset_y - to_decimal(data.get('body_width', '3.0'))
                base_y = (body_bottom - base_expansion - Decimal('1')) * SCALE  # Below courtyard

                # Add unique padstack name texts below footprint
                for i, pad_name in enumerate(unique_names):
                    text_x = Decimal('0')  # Center at origin
                    text_y = base_y - (Decimal(str(i)) * (text_height + Decimal('0.2') * SCALE))  # Stack vertically
                    lines.append(f'Text (Location {(text_x):.1f}, {(text_y):.1f}) (Line Width {(text_line_width)}) (Height {(text_height):.1f}) (Width {(text_width):.1f}) (Rotation 0) (Layer Mechanical13) (Value "{pad_name}")')

                lines.append("EndFootprint\nEndFootprints")
        # Join lines and save
        script = '\n'.join(lines)
        output_path = account_settings.get('altium_output_path', os.path.expanduser("~/Documents/Altium"))
        os.makedirs(output_path, exist_ok=True)
        footprint_name = data.get('footprint_name', 'Unnamed')
        file_name = os.path.join(output_path, f"{footprint_name}_footprint.txt")

        try:
            with open(file_name, "w") as f:
                f.write(script)
            self.show_script_dialog("Altium Script Generated", file_name, script)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save script file:\n{str(e)}")

    def generate_chamfered_body_altium(self, lines, tl, tr, bl, br, chamfer_size, chamfer_corners, line_width, scale):
        """Generate chamfered body outline for Altium script"""
        # Convert chamfer size
        chamfer_size = to_decimal(str(chamfer_size))
        
        # Generate body outline with selective chamfers
        points = []
        
        # Start from top-left, moving clockwise
        if chamfer_corners.get('tl', False):
            # Top-left chamfer: start below chamfer, then diagonal to right of chamfer
            points.append((tl[0], tl[1] - chamfer_size))
            points.append((tl[0] + chamfer_size, tl[1]))
        else:
            points.append((tl[0], tl[1]))
        
        # Top edge to top-right
        if chamfer_corners.get('tr', False):
            # Stop before chamfer, then diagonal down
            points.append((tr[0] - chamfer_size, tr[1]))
            points.append((tr[0], tr[1] - chamfer_size))
        else:
            points.append((tr[0], tr[1]))
        
        # Right edge to bottom-right
        if chamfer_corners.get('br', False):
            # Stop before chamfer, then diagonal left
            points.append((br[0], br[1] + chamfer_size))
            points.append((br[0] - chamfer_size, br[1]))
        else:
            points.append((br[0], br[1]))
        
        # Bottom edge to bottom-left
        if chamfer_corners.get('bl', False):
            # Stop before chamfer, then diagonal up
            points.append((bl[0] + chamfer_size, bl[1]))
            points.append((bl[0], bl[1] + chamfer_size))
        else:
            points.append((bl[0], bl[1]))
        
        # Close the path back to start
        if not chamfer_corners.get('tl', False):
            points.append((tl[0], tl[1]))
        
        # Generate line segments
        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i + 1]
            lines.append(f"Line (Width {line_width*scale}) (Start {(p1[0]*scale)}, {(p1[1]*scale)}) (End {(p2[0]*scale)}, {(p2[1]*scale)}) (Layer Mechanical13)")

    def generate_chamfered_silkscreen_altium(self, lines, tl, tr, bl, br, chamfer_size, chamfer_corners, 
                                        pad_bounds_list, gap, line_width, scale):
        """Generate chamfered silkscreen with pad gaps for Altium script"""
        # Similar to chamfered body, but with gap calculations
        chamfer_size = to_decimal(str(chamfer_size))
        
        # Generate silkscreen segments with gaps where pads interfere
        segments = []
        
        # Define all potential segments (including chamfer segments)
        if chamfer_corners.get('tl', False):
            segments.extend([
                ((tl[0], tl[1] - chamfer_size), (tl[0] + chamfer_size, tl[1])),  # TL chamfer
            ])
        
        # Top edge
        start_x = tl[0] + (chamfer_size if chamfer_corners.get('tl', False) else 0)
        end_x = tr[0] - (chamfer_size if chamfer_corners.get('tr', False) else 0)
        if start_x < end_x:
            segments.extend(self.generate_silkscreen_segments_with_gaps(
                start_x, tl[1], end_x, tr[1], pad_bounds_list, gap, 'horizontal'))
        
        # Continue for other edges...
        # (Similar logic for right, bottom, left edges with chamfer considerations)
        
        # Generate the actual line commands
        for (x1, y1), (x2, y2) in segments:
            lines.append(f"Line (Width {line_width * scale}) (Start {(x1*scale)}, {(y1*scale)}) (End {(x2*scale)}, {(y2*scale)}) (Layer TopOverlay)")



    def generate_standard_silkscreen_altium(self, lines, tl, tr, bl, br, pad_bounds_list, gap, line_width, scale):
        """Generate standard rectangular silkscreen with pad gaps for Altium script"""
        # Generate silkscreen lines with gaps for each side of body rectangle
        silk_segments = []
        
        # Top line
        silk_segments.extend(self.generate_silkscreen_segments_with_gaps(
            tl[0], tl[1], tr[0], tr[1], pad_bounds_list, gap, 'horizontal'))
        
        # Right line
        silk_segments.extend(self.generate_silkscreen_segments_with_gaps(
            tr[0], tr[1], br[0], br[1], pad_bounds_list, gap, 'vertical'))
        
        # Bottom line
        silk_segments.extend(self.generate_silkscreen_segments_with_gaps(
            br[0], br[1], bl[0], bl[1], pad_bounds_list, gap, 'horizontal'))
        
        # Left line
        silk_segments.extend(self.generate_silkscreen_segments_with_gaps(
            bl[0], bl[1], tl[0], tl[1], pad_bounds_list, gap, 'vertical'))
        
        # Generate line commands
        for (x1, y1), (x2, y2) in silk_segments:
            lines.append(f"Line (Width {line_width * scale}) (Start {(x1*scale)}, {(y1*scale)}) (End {(x2*scale)}, {(y2*scale)}) (Layer TopOverlay)")

    def generate_silkscreen_segments_with_gaps(self, x1, y1, x2, y2, pad_bounds_list, gap, orientation):
        """Generate line segments with gaps where pads would interfere"""
        segments = []
        gap_decimal = to_decimal(str(gap))
        
        if orientation == 'horizontal':
            start_pos = min(x1, x2)
            end_pos = max(x1, x2)
            line_y = y1
            
            # Find intersections with pads
            intersections = []
            for pad_bounds in pad_bounds_list:
                if not pad_bounds:
                    continue
                
                px_min, py_min, px_max, py_max = [to_decimal(str(coord)) for coord in pad_bounds]
                pad_min_x = px_min - gap_decimal
                pad_max_x = px_max + gap_decimal
                pad_min_y = py_min - gap_decimal
                pad_max_y = py_max + gap_decimal
                
                # Check if horizontal line intersects with expanded pad
                if (line_y >= pad_min_y and line_y <= pad_max_y and
                    pad_max_x >= start_pos and pad_min_x <= end_pos):
                    inter_start = max(start_pos, pad_min_x)
                    inter_end = min(end_pos, pad_max_x)
                    intersections.append((inter_start, inter_end))
            
            # Merge overlapping intersections
            merged = self.merge_intervals(intersections)
            
            # Generate segments between gaps
            current_pos = start_pos
            for gap_start, gap_end in merged:
                if current_pos < gap_start:
                    segments.append(((current_pos, line_y), (gap_start, line_y)))
                current_pos = gap_end
            
            if current_pos < end_pos:
                segments.append(((current_pos, line_y), (end_pos, line_y)))
        
        else:  # vertical
            # Similar logic for vertical lines
            start_pos = min(y1, y2)
            end_pos = max(y1, y2)
            line_x = x1
            
            intersections = []
            for pad_bounds in pad_bounds_list:
                if not pad_bounds:
                    continue
                
                px_min, py_min, px_max, py_max = [to_decimal(str(coord)) for coord in pad_bounds]
                pad_min_x = px_min - gap_decimal
                pad_max_x = px_max + gap_decimal
                pad_min_y = py_min - gap_decimal
                pad_max_y = py_max + gap_decimal
                
                if (line_x >= pad_min_x and line_x <= pad_max_x and
                    pad_max_y >= start_pos and pad_min_y <= end_pos):
                    inter_start = max(start_pos, pad_min_y)
                    inter_end = min(end_pos, pad_max_y)
                    intersections.append((inter_start, inter_end))
            
            merged = self.merge_intervals(intersections)
            
            current_pos = start_pos
            for gap_start, gap_end in merged:
                if current_pos < gap_start:
                    segments.append(((line_x, current_pos), (line_x, gap_start)))
                current_pos = gap_end
            
            if current_pos < end_pos:
                segments.append(((line_x, current_pos), (line_x, end_pos)))
        
        return segments

    def merge_intervals(self, intervals):
        """Merge overlapping intervals"""
        if not intervals:
            return []
        
        intervals = sorted(intervals, key=lambda x: x[0])
        merged = [intervals[0]]
        
        for current in intervals[1:]:
            last = merged[-1]
            if current[0] <= last[1]:
                merged[-1] = (last[0], max(last[1], current[1]))
            else:
                merged.append(current)
        
        return merged


#########################################################################################################################################################################################################


    def generate_pad_name_for_script(self, pad):
        """Generate pad name for script - same logic as renderer"""
        return self.renderer.generate_pad_name(pad)

    def generate_pad_name(self, pad):
        """Generate padstack name based on pad type and expansions"""
        pad_type = pad['type']
        
        try:
            mask_exp = to_decimal(pad.get('mask_expansion', 0)) if pad.get('mask_enabled', True) else 0
            paste_exp = to_decimal(pad.get('paste_expansion', 0)) if pad.get('paste_enabled', True) else 0
        except (ValueError, TypeError):
            mask_exp = paste_exp = 0
        
        name = ""
        
        if pad_type == 'square':
            try:
                size = to_decimal(pad.get('size', 1))
                name = f"S{int(size * 100)}"
                if mask_exp > 0:
                    mask_size = int((size + 2 * mask_exp) * 100)
                    name += f"_M{mask_size}"
                if paste_exp > 0:           
                    paste_size = int((size + 2 * paste_exp) * 100)
                    name += f"_P{paste_size}"
            except (ValueError, TypeError):
                name = "S100"
                
        elif pad_type in ['rectangle', 'rounded_rectangle', 'SMD-oblong', 'PTH_rectangle']:
            try:
                length = to_decimal(pad.get('length', 1))
                width = to_decimal(pad.get('width', 1))
                name = f"R{int(length * 100)}x{int(width * 100)}"
                if mask_exp > 0:
                    mask_l = int((length + 2 * mask_exp) * 100)
                    mask_w = int((width + 2 * mask_exp) * 100)
                    name += f"_M{mask_l}x{mask_w}"
                if paste_exp > 0:
                    paste_l = int((length + 2 * paste_exp) * 100)
                    paste_w = int((width + 2 * paste_exp) * 100)
                    name += f"_P{paste_l}x{paste_w}"
            except (ValueError, TypeError):
                name = "R100x100"
                
        elif pad_type == 'round':
            try:
                diameter = to_decimal(pad.get('diameter', 1))
                name = f"C{int(diameter * 100)}"  # C for circular
                if mask_exp > 0:
                    mask_dia = int((diameter + 2 * mask_exp) * 100)
                    name += f"_M{mask_dia}"
                if paste_exp > 0:
                    paste_dia = int((diameter + 2 * paste_exp) * 100)
                    name += f"_P{paste_dia}"
            except (ValueError, TypeError):
                name = "C100"
                
        elif pad_type in ['PTH', 'NPTH']:
            hole_dia = to_decimal(pad.get('hole_diameter', 0.8))
            if pad_type == 'PTH':
                pad_dia = to_decimal(pad.get('pad_diameter', 1.2))
                name = f"PTH{int(hole_dia * 100)}_P{int(pad_dia * 100)}"
            else:
                name = f"NPTH{int(hole_dia * 100)}"
                
        elif pad_type in ['PTH_oblong', 'NPTH_oblong']:
            hole_l = to_decimal(pad.get('hole_length', 1.5))
            hole_w = to_decimal(pad.get('hole_width', 0.8))
            if pad_type == 'PTH_oblong':
                pad_l = to_decimal(pad.get('pad_length', 2.0))
                pad_w = to_decimal(pad.get('pad_width', 1.2))
                name = f"PTHO{int(hole_l * 100)}x{int(hole_w * 100)}_P{int(pad_l * 100)}x{int(pad_w * 100)}"
            else:
                name = f"NPTHO{int(hole_l * 100)}x{int(hole_w * 100)}"
        else:
            name = f"{pad_type.upper()}"
            
        return name
  

############################################################################### allegro script ###############################################################################################################


    def generate_allegro_script(self):
        """Generate comprehensive Allegro PCB Editor SKILL script with complete padstack definitions"""
        data = self.get_footprint_data()
        settings = self.settings_panel.get_settings()
        account_settings = AccountManager.load_account_settings()
        
        lines = []
        footprint_name = data.get('footprint_name', 'Unnamed')

        # PADS script header
        lines.append("! PADS Layout Script - Enhanced Version")
        lines.append(f"! Footprint: {footprint_name}")
        lines.append(f"! Generated by LibSienna Footprint Designer")
        lines.append("")

        # Get pads and resolver
        pads = data.get('padstacks', [])
        resolver = PadPositionResolver(pads)

        # Step 1: Create unique padstack definitions
        lines.append("! ===== PADSTACK DEFINITIONS =====")
        lines.append("*DEFINE_PADSTACK*")

        unique_padstacks = {}
        padstack_counter = 1

        for pad in pads:
            padstack_name = self.generate_pad_name_for_script(pad)
            if padstack_name not in unique_padstacks:
                unique_padstacks[padstack_name] = f"PAD{padstack_counter:03d}"
                pad_type = pad.get('type', 'square')

                lines.append(f"! Padstack: {padstack_name}")
                lines.append(f"{unique_padstacks[padstack_name]} {padstack_name}")

                # Get mask/paste settings
                mask_enabled = pad.get('mask_enabled', True)
                paste_enabled = pad.get('paste_enabled', True)
                mask_exp = to_decimal(pad.get('mask_expansion', 0)) if mask_enabled else 0
                paste_exp = to_decimal(pad.get('paste_expansion', 0)) if paste_enabled else 0

                if pad_type == 'square':
                    size = to_decimal(pad.get('size', 1)) * 1000  # Convert to mils
                    lines.append(f" TOP S{size:.0f}")
                    lines.append(f" BOTTOM S{size:.0f}")
                    
                    if mask_exp > 0:
                        mask_size = (size/1000 + 2 * mask_exp) * 1000
                        lines.append(f" SOLDERMASK S{mask_size:.0f}")
                    if paste_exp > 0:
                        paste_size = (size/1000 + 2 * paste_exp) * 1000
                        lines.append(f" PASTE S{paste_size:.0f}")

                elif pad_type in ['rectangle', 'SMD-oblong', 'rounded_rectangle']:
                    length = to_decimal(pad.get('length', 1)) * 1000
                    width = to_decimal(pad.get('width', 1)) * 1000
                    shape = "R" if pad_type == 'rectangle' else "O"  # O for oblong/rounded

                    lines.append(f" TOP {shape}{length:.0f}X{width:.0f}")
                    lines.append(f" BOTTOM {shape}{length:.0f}X{width:.0f}")
                    
                    if mask_exp > 0:
                        mask_l = (length/1000 + 2 * mask_exp) * 1000
                        mask_w = (width/1000 + 2 * mask_exp) * 1000
                        lines.append(f" SOLDERMASK {shape}{mask_l:.0f}X{mask_w:.0f}")
                    if paste_exp > 0:
                        paste_l = (length/1000 + 2 * paste_exp) * 1000
                        paste_w = (width/1000 + 2 * paste_exp) * 1000
                        lines.append(f" PASTE {shape}{paste_l:.0f}X{paste_w:.0f}")

                elif pad_type == 'round':
                    diameter = to_decimal(pad.get('diameter', 1)) * 1000
                    lines.append(f" TOP C{diameter:.0f}")
                    lines.append(f" BOTTOM C{diameter:.0f}")
                    
                    if mask_exp > 0:
                        mask_dia = (diameter/1000 + 2 * mask_exp) * 1000
                        lines.append(f" SOLDERMASK C{mask_dia:.0f}")
                    if paste_exp > 0:
                        paste_dia = (diameter/1000 + 2 * paste_exp) * 1000
                        lines.append(f" PASTE C{paste_dia:.0f}")

                elif pad_type in ['PTH', 'NPTH']:
                    hole_dia = to_decimal(pad.get('hole_diameter', 0.8)) * 1000
                    lines.append(f" DRILL {hole_dia:.0f}")
                    
                    if pad_type == 'PTH':
                        pad_dia = to_decimal(pad.get('pad_diameter', 1.2)) * 1000
                        lines.append(f" TOP C{pad_dia:.0f}")
                        lines.append(f" BOTTOM C{pad_dia:.0f}")

                elif pad_type in ['PTH_oblong', 'NPTH_oblong']:
                    hole_length = to_decimal(pad.get('hole_length', 1.5)) * 1000
                    hole_width = to_decimal(pad.get('hole_width', 0.8)) * 1000
                    lines.append(f" DRILL O{hole_length:.0f}X{hole_width:.0f}")
                    
                    if pad_type == 'PTH_oblong':
                        pad_length = to_decimal(pad.get('pad_length', 2.0)) * 1000
                        pad_width = to_decimal(pad.get('pad_width', 1.2)) * 1000
                        lines.append(f" TOP O{pad_length:.0f}X{pad_width:.0f}")
                        lines.append(f" BOTTOM O{pad_length:.0f}X{pad_width:.0f}")

                elif pad_type == 'PTH_rectangle':
                    hole_length = to_decimal(pad.get('hole_length', 1.5)) * 1000
                    hole_width = to_decimal(pad.get('hole_width', 0.8)) * 1000
                    lines.append(f" DRILL R{hole_length:.0f}X{hole_width:.0f}")
                    
                    pad_length = to_decimal(pad.get('pad_length', 2.0)) * 1000
                    pad_width = to_decimal(pad.get('pad_width', 1.2)) * 1000
                    lines.append(f" TOP R{pad_length:.0f}X{pad_width:.0f}")
                    lines.append(f" BOTTOM R{pad_length:.0f}X{pad_width:.0f}")

                lines.append("")
                padstack_counter += 1

        lines.append("*END_DEFINE_PADSTACK*")
        lines.append("")

        # Step 2: Create part definition with pad placements
        lines.append("! ===== PART DEFINITION =====")
        lines.append("*PART*")
        lines.append(f"{footprint_name}")
        lines.append("")

        lines.append("! Pad placements:")
        for pad in pads:
            padstack_name = self.generate_pad_name_for_script(pad)
            pin_number = pad.get('pin_number', '1')
            abs_x, abs_y = resolver.get_absolute_position(pad)
            
            # Convert to mils and reference the padstack
            x_mils = abs_x * 1000
            y_mils = abs_y * 1000
            lines.append(f"{pin_number} {x_mils:.0f} {y_mils:.0f} {unique_padstacks[padstack_name]}")

        lines.append("")

        # Get dimensions and settings for geometry generation
        origin_offset_x = to_decimal(data.get('origin_offset_x', '0'))
        origin_offset_y = to_decimal(data.get('origin_offset_y', '0'))
        body_length = to_decimal(data.get('body_length', '0'))
        body_width = to_decimal(data.get('body_width', '0'))
        body_shape = data.get('body_shape', 'rectangle')
        body_chamfer = to_decimal(data.get('body_chamfer', '0'))
        chamfer_corners = data.get('chamfer_corners', {})

        # Calculate body corners with origin offset (in mm)
        tl = (origin_offset_x, origin_offset_y)  # Top-left
        tr = (origin_offset_x + body_length, origin_offset_y)  # Top-right
        bl = (origin_offset_x, origin_offset_y - body_width)  # Bottom-left
        br = (origin_offset_x + body_length, origin_offset_y - body_width)  # Bottom-right

        # Calculate pad bounds for silkscreen gap calculation
        pad_bounds_list = []
        for pad in pads:
            abs_x, abs_y = resolver.get_absolute_position(pad)
            pad_bounds = self.calculate_pad_bounds_for_script(pad, abs_x, abs_y)
            if pad_bounds:
                pad_bounds_list.append(pad_bounds)

        # Step 3: Generate Assembly Layer with Chamfer Support
        if body_length > 0 and body_width > 0:
            lines.append("! ===== ASSEMBLY LAYER =====")
            assembly_width = to_decimal(data.get('body_line_width', '0.05')) * 1000

            if body_shape == 'round':
                # Round assembly
                radius = max(body_length, body_width) / Decimal('2')
                center_x = (origin_offset_x + body_length / Decimal('2')) * 1000
                center_y = (origin_offset_y - body_width / Decimal('2')) * 1000
                radius_mils = radius * 1000
                lines.append(f"CIRCLE {center_x:.0f} {center_y:.0f} {radius_mils:.0f} {assembly_width:.0f} ASSEMBLY_TOP")
            else:
                # Rectangular assembly with chamfer support
                if body_chamfer > 0 and any(chamfer_corners.values()):
                    # Generate chamfered body outline
                    lines.append("! Body outline assembly (chamfered)")
                    assembly_segments = self.generate_chamfered_body_segments_pads(
                        tl, tr, bl, br, body_chamfer, chamfer_corners
                    )
                    for (x1, y1), (x2, y2) in assembly_segments:
                        lines.append(f"LINE {x1*1000:.0f} {y1*1000:.0f} {x2*1000:.0f} {y2*1000:.0f} {assembly_width:.0f} ASSEMBLY_TOP")
                else:
                    # Standard rectangular body
                    lines.append("! Body outline assembly")
                    lines.append(f"LINE {tl[0]*1000:.0f} {tl[1]*1000:.0f} {tr[0]*1000:.0f} {tr[1]*1000:.0f} {assembly_width:.0f} ASSEMBLY_TOP")
                    lines.append(f"LINE {tr[0]*1000:.0f} {tr[1]*1000:.0f} {br[0]*1000:.0f} {br[1]*1000:.0f} {assembly_width:.0f} ASSEMBLY_TOP")
                    lines.append(f"LINE {br[0]*1000:.0f} {br[1]*1000:.0f} {bl[0]*1000:.0f} {bl[1]*1000:.0f} {assembly_width:.0f} ASSEMBLY_TOP")
                    lines.append(f"LINE {bl[0]*1000:.0f} {bl[1]*1000:.0f} {tl[0]*1000:.0f} {tl[1]*1000:.0f} {assembly_width:.0f} ASSEMBLY_TOP")

            lines.append("")

        # Step 4: Generate Silkscreen with Gap Logic and Chamfer Support
        if data.get('silkscreen_enabled', True) and body_length > 0 and body_width > 0:
            lines.append("! ===== SILKSCREEN WITH PAD GAPS =====")
            silkscreen_width = to_decimal(data.get('silkscreen_line_width', '0.15')) * 1000
            silkscreen_gap = to_decimal(data.get('silkscreen_airgap', '0.15'))
            follow_chamfer = data.get('silkscreen_follow_chamfer', False)

            if body_shape == 'round':
                # Round silkscreen - simplified approach
                radius = max(body_length, body_width) / Decimal('2')
                center_x = (origin_offset_x + body_length / Decimal('2')) * 1000
                center_y = (origin_offset_y - body_width / Decimal('2')) * 1000
                radius_mils = radius * 1000
                lines.append(f"! NOTE: Round silkscreen with pad gaps requires manual editing")
                lines.append(f"CIRCLE {center_x:.0f} {center_y:.0f} {radius_mils:.0f} {silkscreen_width:.0f} SILK_TOP")
            else:
                # Rectangular silkscreen with proper gap logic
                if follow_chamfer and body_chamfer > 0 and any(chamfer_corners.values()):
                    # Generate chamfered silkscreen with gaps
                    lines.append("! Chamfered silkscreen with pad gaps")
                    silk_segments = self.generate_chamfered_silkscreen_segments_pads(
                        tl, tr, bl, br, body_chamfer, chamfer_corners, pad_bounds_list, silkscreen_gap
                    )
                else:
                    # Standard rectangular silkscreen with gaps
                    lines.append("! Rectangular silkscreen with pad gaps")
                    silk_segments = self.generate_standard_silkscreen_segments_pads(
                        tl, tr, bl, br, pad_bounds_list, silkscreen_gap
                    )

                # Generate the silkscreen line commands
                for (x1, y1), (x2, y2) in silk_segments:
                    lines.append(f"LINE {x1*1000:.0f} {y1*1000:.0f} {x2*1000:.0f} {y2*1000:.0f} {silkscreen_width:.0f} SILK_TOP")

            lines.append("")

        # Step 5: Generate Proper Courtyard with Individual Side Calculations
        lines.append("! ===== COURTYARD WITH PROPER CALCULATIONS =====")
        base_expansion = to_decimal(data.get('courtyard_expansion', '0.25'))
        courtyard_line_width = to_decimal(data.get('courtyard_line_width', '0.1'))
        body_line_width = to_decimal(data.get('body_line_width', '0.05'))
        courtyard_width = courtyard_line_width * 1000

        if body_length > 0 and body_width > 0:
            if body_shape == 'round':
                # Round courtyard logic
                radius = max(body_length, body_width) / Decimal('2')
                center_x = (origin_offset_x + body_length / Decimal('2'))
                center_y = (origin_offset_y - body_width / Decimal('2'))
                
                # Check if pads extend beyond body circle
                max_pad_distance = Decimal('0')
                if pad_bounds_list:
                    for pad_bounds in pad_bounds_list:
                        px_min, py_min, px_max, py_max = [to_decimal(str(coord)) for coord in pad_bounds]
                        # Check all corners of pad bounds
                        pad_corners = [(px_min, py_min), (px_max, py_min), (px_max, py_max), (px_min, py_max)]
                        for corner_x, corner_y in pad_corners:
                            distance = ((corner_x - center_x)**2 + (corner_y - center_y)**2).sqrt()
                            max_pad_distance = max(max_pad_distance, distance)

                # Determine courtyard radius
                if max_pad_distance > radius:
                    courtyard_radius = max_pad_distance + base_expansion + (courtyard_line_width / Decimal('2'))
                else:
                    courtyard_radius = radius + base_expansion + (courtyard_line_width / Decimal('2')) + (body_line_width / Decimal('2'))

                lines.append(f"CIRCLE {center_x*1000:.0f} {center_y*1000:.0f} {courtyard_radius*1000:.0f} {courtyard_width:.0f} BOARD_GEOMETRY")
            else:
                # Rectangular courtyard with proper individual side calculations
                lines.append("! Rectangular courtyard with individual side calculations")
                
                # Body bounds adjusted for origin offset
                body_bounds_adjusted = [tl[0], bl[1], tr[0], tl[1]]  # [min_x, min_y, max_x, max_y]
                
                # Calculate overall pad bounds
                pad_bounds_for_courtyard = None
                if pad_bounds_list:
                    min_x = min(pb[0] for pb in pad_bounds_list)
                    min_y = min(pb[1] for pb in pad_bounds_list)
                    max_x = max(pb[2] for pb in pad_bounds_list)
                    max_y = max(pb[3] for pb in pad_bounds_list)
                    pad_bounds_for_courtyard = [min_x, min_y, max_x, max_y]

                # Determine outermost bounds for each side
                courtyard_line_w = courtyard_line_width / 2
                body_line_w = body_line_width / 2
                body_linecourtyard = courtyard_line_w + body_line_w

                if body_bounds_adjusted and pad_bounds_for_courtyard:
                    # Calculate individual side expansions
                    expansions = {}
                    
                    # Left side
                    if body_bounds_adjusted[0] <= pad_bounds_for_courtyard[0]:
                        outermost_left = body_bounds_adjusted[0]
                        expansions['left'] = base_expansion + body_linecourtyard
                    else:
                        outermost_left = pad_bounds_for_courtyard[0]
                        expansions['left'] = base_expansion + courtyard_line_w

                    # Right side  
                    if body_bounds_adjusted[2] >= pad_bounds_for_courtyard[2]:
                        outermost_right = body_bounds_adjusted[2]
                        expansions['right'] = base_expansion + body_linecourtyard
                    else:
                        outermost_right = pad_bounds_for_courtyard[2]
                        expansions['right'] = base_expansion + courtyard_line_w

                    # Bottom side
                    if body_bounds_adjusted[1] <= pad_bounds_for_courtyard[1]:
                        outermost_bottom = body_bounds_adjusted[1]
                        expansions['bottom'] = base_expansion + body_linecourtyard
                    else:
                        outermost_bottom = pad_bounds_for_courtyard[1]
                        expansions['bottom'] = base_expansion + courtyard_line_w

                    # Top side
                    if body_bounds_adjusted[3] >= pad_bounds_for_courtyard[3]:
                        outermost_top = body_bounds_adjusted[3]
                        expansions['top'] = base_expansion + body_linecourtyard
                    else:
                        outermost_top = pad_bounds_for_courtyard[3]
                        expansions['top'] = base_expansion + courtyard_line_w

                elif body_bounds_adjusted:
                    outermost_left = body_bounds_adjusted[0]
                    outermost_right = body_bounds_adjusted[2]
                    outermost_bottom = body_bounds_adjusted[1]
                    outermost_top = body_bounds_adjusted[3]
                    expansion_val = base_expansion + body_linecourtyard
                    expansions = {'left': expansion_val, 'right': expansion_val, 'bottom': expansion_val, 'top': expansion_val}
                elif pad_bounds_for_courtyard:
                    outermost_left = pad_bounds_for_courtyard[0]
                    outermost_right = pad_bounds_for_courtyard[2]
                    outermost_bottom = pad_bounds_for_courtyard[1]
                    outermost_top = pad_bounds_for_courtyard[3]
                    expansion_val = base_expansion + courtyard_line_w
                    expansions = {'left': expansion_val, 'right': expansion_val, 'bottom': expansion_val, 'top': expansion_val}
                else:
                    lines.append("! No geometry found for courtyard")

                if 'expansions' in locals():
                    # Calculate courtyard bounds with individual expansions
                    cy_left = (outermost_left - expansions['left']) * 1000
                    cy_right = (outermost_right + expansions['right']) * 1000
                    cy_bottom = (outermost_bottom - expansions['bottom']) * 1000
                    cy_top = (outermost_top + expansions['top']) * 1000

                    # Generate courtyard rectangle
                    lines.append(f"LINE {cy_left:.0f} {cy_top:.0f} {cy_right:.0f} {cy_top:.0f} {courtyard_width:.0f} BOARD_GEOMETRY")
                    lines.append(f"LINE {cy_right:.0f} {cy_top:.0f} {cy_right:.0f} {cy_bottom:.0f} {courtyard_width:.0f} BOARD_GEOMETRY")
                    lines.append(f"LINE {cy_right:.0f} {cy_bottom:.0f} {cy_left:.0f} {cy_bottom:.0f} {courtyard_width:.0f} BOARD_GEOMETRY")
                    lines.append(f"LINE {cy_left:.0f} {cy_bottom:.0f} {cy_left:.0f} {cy_top:.0f} {courtyard_width:.0f} BOARD_GEOMETRY")

        lines.append("")
        lines.append("*END*")

        # Save script
        script = '\n'.join(lines)
        output_path = account_settings.get('allegro_output_path', os.path.expanduser("~/Documents/Allegro"))
        os.makedirs(output_path, exist_ok=True)
        file_name = os.path.join(output_path, f"{footprint_name}.scr")

        try:
            with open(file_name, "w") as f:
                f.write(script)
            self.show_script_dialog("Enhanced PADS Script Generated", file_name, script)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save PADS script: {str(e)}")

    # Helper methods for PADS script generation
    def generate_chamfered_body_segments_allegro(self, tl, tr, bl, br, chamfer_size, chamfer_corners):
        """Generate chamfered body line segments for PADS"""
        segments = []
        chamfer_size = to_decimal(str(chamfer_size))
        
        # Define corner points with chamfers
        points = []
        
        # Start from top-left, moving clockwise
        if chamfer_corners.get('tl', False):
            points.append((tl[0], tl[1] - chamfer_size))
            points.append((tl[0] + chamfer_size, tl[1]))
        else:
            points.append((tl[0], tl[1]))
        
        # Top edge to top-right
        if chamfer_corners.get('tr', False):
            points.append((tr[0] - chamfer_size, tr[1]))
            points.append((tr[0], tr[1] - chamfer_size))
        else:
            points.append((tr[0], tr[1]))
        
        # Right edge to bottom-right
        if chamfer_corners.get('br', False):
            points.append((br[0], br[1] + chamfer_size))
            points.append((br[0] - chamfer_size, br[1]))
        else:
            points.append((br[0], br[1]))
        
        # Bottom edge to bottom-left
        if chamfer_corners.get('bl', False):
            points.append((bl[0] + chamfer_size, bl[1]))
            points.append((bl[0], bl[1] + chamfer_size))
        else:
            points.append((bl[0], bl[1]))
        
        # Generate line segments
        for i in range(len(points)):
            p1 = points[i]
            p2 = points[(i + 1) % len(points)]
            segments.append((p1, p2))
        
        return segments

    def generate_standard_silkscreen_segments_allegro(self, tl, tr, bl, br, pad_bounds_list, gap):
        """Generate standard rectangular silkscreen segments with pad gaps for Allegro"""
        segments = []
        
        # Top line
        segments.extend(self.generate_silkscreen_segments_with_gaps_allegro(
            tl[0], tl[1], tr[0], tr[1], pad_bounds_list, gap, 'horizontal'))
        
        # Right line
        segments.extend(self.generate_silkscreen_segments_with_gaps_allegro(
            tr[0], tr[1], br[0], br[1], pad_bounds_list, gap, 'vertical'))
        
        # Bottom line
        segments.extend(self.generate_silkscreen_segments_with_gaps_allegro(
            br[0], br[1], bl[0], bl[1], pad_bounds_list, gap, 'horizontal'))
        
        # Left line
        segments.extend(self.generate_silkscreen_segments_with_gaps_allegro(
            bl[0], bl[1], tl[0], tl[1], pad_bounds_list, gap, 'vertical'))
        
        return segments

    def generate_chamfered_silkscreen_segments_allegro(self, tl, tr, bl, br, chamfer_size, chamfer_corners, pad_bounds_list, gap):
        """Generate chamfered silkscreen segments with pad gaps for Allegro"""
        segments = []
        
        # Get chamfered body segments first
        body_segments = self.generate_chamfered_body_segments_allegro(tl, tr, bl, br, chamfer_size, chamfer_corners)
        
        # For each body segment, check for pad gaps
        for (x1, y1), (x2, y2) in body_segments:
            # Determine if this is horizontal or vertical segment
            if abs(x2 - x1) > abs(y2 - y1):
                orientation = 'horizontal'
            else:
                orientation = 'vertical'
            
            # Generate segments with gaps
            gap_segments = self.generate_silkscreen_segments_with_gaps_allegro(
                x1, y1, x2, y2, pad_bounds_list, gap, orientation)
            segments.extend(gap_segments)
        
        return segments

    def generate_silkscreen_segments_with_gaps_allegro(self, x1, y1, x2, y2, pad_bounds_list, gap, orientation):
        """Generate line segments with gaps where pads would interfere - Allegro"""
        segments = []
        gap_decimal = to_decimal(str(gap))

        if orientation == 'horizontal':
            start_pos = min(x1, x2)
            end_pos = max(x1, x2)
            line_y = y1

            # Find intersections with pads
            intersections = []
            for pad_bounds in pad_bounds_list:
                if not pad_bounds:
                    continue
                
                px_min, py_min, px_max, py_max = [to_decimal(str(coord)) for coord in pad_bounds]
                pad_min_x = px_min - gap_decimal
                pad_max_x = px_max + gap_decimal
                pad_min_y = py_min - gap_decimal
                pad_max_y = py_max + gap_decimal

                # Check if horizontal line intersects with expanded pad
                if (line_y >= pad_min_y and line_y <= pad_max_y and
                    pad_max_x >= start_pos and pad_min_x <= end_pos):
                    
                    inter_start = max(start_pos, pad_min_x)
                    inter_end = min(end_pos, pad_max_x)
                    intersections.append((inter_start, inter_end))

            # Merge overlapping intersections
            merged = self.merge_intervals(intersections)

            # Generate segments between gaps
            current_pos = start_pos
            for gap_start, gap_end in merged:
                if current_pos < gap_start:
                    segments.append(((current_pos, line_y), (gap_start, line_y)))
                current_pos = gap_end

            if current_pos < end_pos:
                segments.append(((current_pos, line_y), (end_pos, line_y)))

        else:  # vertical
            start_pos = min(y1, y2)
            end_pos = max(y1, y2)
            line_x = x1

            intersections = []
            for pad_bounds in pad_bounds_list:
                if not pad_bounds:
                    continue
                
                px_min, py_min, px_max, py_max = [to_decimal(str(coord)) for coord in pad_bounds]
                pad_min_x = px_min - gap_decimal
                pad_max_x = px_max + gap_decimal
                pad_min_y = py_min - gap_decimal
                pad_max_y = py_max + gap_decimal

                if (line_x >= pad_min_x and line_x <= pad_max_x and
                    pad_max_y >= start_pos and pad_min_y <= end_pos):
                    
                    inter_start = max(start_pos, pad_min_y)
                    inter_end = min(end_pos, pad_max_y)
                    intersections.append((inter_start, inter_end))

            merged = self.merge_intervals(intersections)

            current_pos = start_pos
            for gap_start, gap_end in merged:
                if current_pos < gap_start:
                    segments.append(((line_x, current_pos), (line_x, gap_start)))
                current_pos = gap_end

            if current_pos < end_pos:
                segments.append(((line_x, current_pos), (line_x, end_pos)))

        return segments



############################################################################### Pads script ###############################################################################################################


    def generate_pads_script(self):
        """Generate comprehensive PADS Layout script with proper chamfer, courtyard, and silkscreen"""
        data = self.get_footprint_data()
        settings = self.settings_panel.get_settings()
        account_settings = AccountManager.load_account_settings()
        
        lines = []
        footprint_name = data.get('footprint_name', 'Unnamed')

        # PADS script header
        lines.append("! PADS Layout Script - Enhanced Version")
        lines.append(f"! Footprint: {footprint_name}")
        lines.append(f"! Generated by LibSienna Footprint Designer")
        lines.append("")

        # Get pads and resolver
        pads = data.get('padstacks', [])
        resolver = PadPositionResolver(pads)

        # Step 1: Create unique padstack definitions
        lines.append("! ===== PADSTACK DEFINITIONS =====")
        lines.append("*DEFINE_PADSTACK*")

        unique_padstacks = {}
        padstack_counter = 1

        for pad in pads:
            padstack_name = self.generate_pad_name_for_script(pad)
            if padstack_name not in unique_padstacks:
                unique_padstacks[padstack_name] = f"PAD{padstack_counter:03d}"
                pad_type = pad.get('type', 'square')

                lines.append(f"! Padstack: {padstack_name}")
                lines.append(f"{unique_padstacks[padstack_name]} {padstack_name}")

                # Get mask/paste settings
                mask_enabled = pad.get('mask_enabled', True)
                paste_enabled = pad.get('paste_enabled', True)
                mask_exp = to_decimal(pad.get('mask_expansion', 0)) if mask_enabled else 0
                paste_exp = to_decimal(pad.get('paste_expansion', 0)) if paste_enabled else 0

                if pad_type == 'square':
                    size = to_decimal(pad.get('size', 1)) * 1000  # Convert to mils
                    lines.append(f" TOP S{size:.0f}")
                    lines.append(f" BOTTOM S{size:.0f}")
                    
                    if mask_exp > 0:
                        mask_size = (size/1000 + 2 * mask_exp) * 1000
                        lines.append(f" SOLDERMASK S{mask_size:.0f}")
                    if paste_exp > 0:
                        paste_size = (size/1000 + 2 * paste_exp) * 1000
                        lines.append(f" PASTE S{paste_size:.0f}")

                elif pad_type in ['rectangle', 'SMD-oblong', 'rounded_rectangle']:
                    length = to_decimal(pad.get('length', 1)) * 1000
                    width = to_decimal(pad.get('width', 1)) * 1000
                    shape = "R" if pad_type == 'rectangle' else "O"  # O for oblong/rounded

                    lines.append(f" TOP {shape}{length:.0f}X{width:.0f}")
                    lines.append(f" BOTTOM {shape}{length:.0f}X{width:.0f}")
                    
                    if mask_exp > 0:
                        mask_l = (length/1000 + 2 * mask_exp) * 1000
                        mask_w = (width/1000 + 2 * mask_exp) * 1000
                        lines.append(f" SOLDERMASK {shape}{mask_l:.0f}X{mask_w:.0f}")
                    if paste_exp > 0:
                        paste_l = (length/1000 + 2 * paste_exp) * 1000
                        paste_w = (width/1000 + 2 * paste_exp) * 1000
                        lines.append(f" PASTE {shape}{paste_l:.0f}X{paste_w:.0f}")

                elif pad_type == 'round':
                    diameter = to_decimal(pad.get('diameter', 1)) * 1000
                    lines.append(f" TOP C{diameter:.0f}")
                    lines.append(f" BOTTOM C{diameter:.0f}")
                    
                    if mask_exp > 0:
                        mask_dia = (diameter/1000 + 2 * mask_exp) * 1000
                        lines.append(f" SOLDERMASK C{mask_dia:.0f}")
                    if paste_exp > 0:
                        paste_dia = (diameter/1000 + 2 * paste_exp) * 1000
                        lines.append(f" PASTE C{paste_dia:.0f}")

                elif pad_type in ['PTH', 'NPTH']:
                    hole_dia = to_decimal(pad.get('hole_diameter', 0.8)) * 1000
                    lines.append(f" DRILL {hole_dia:.0f}")
                    
                    if pad_type == 'PTH':
                        pad_dia = to_decimal(pad.get('pad_diameter', 1.2)) * 1000
                        lines.append(f" TOP C{pad_dia:.0f}")
                        lines.append(f" BOTTOM C{pad_dia:.0f}")

                elif pad_type in ['PTH_oblong', 'NPTH_oblong']:
                    hole_length = to_decimal(pad.get('hole_length', 1.5)) * 1000
                    hole_width = to_decimal(pad.get('hole_width', 0.8)) * 1000
                    lines.append(f" DRILL O{hole_length:.0f}X{hole_width:.0f}")
                    
                    if pad_type == 'PTH_oblong':
                        pad_length = to_decimal(pad.get('pad_length', 2.0)) * 1000
                        pad_width = to_decimal(pad.get('pad_width', 1.2)) * 1000
                        lines.append(f" TOP O{pad_length:.0f}X{pad_width:.0f}")
                        lines.append(f" BOTTOM O{pad_length:.0f}X{pad_width:.0f}")

                elif pad_type == 'PTH_rectangle':
                    hole_length = to_decimal(pad.get('hole_length', 1.5)) * 1000
                    hole_width = to_decimal(pad.get('hole_width', 0.8)) * 1000
                    lines.append(f" DRILL R{hole_length:.0f}X{hole_width:.0f}")
                    
                    pad_length = to_decimal(pad.get('pad_length', 2.0)) * 1000
                    pad_width = to_decimal(pad.get('pad_width', 1.2)) * 1000
                    lines.append(f" TOP R{pad_length:.0f}X{pad_width:.0f}")
                    lines.append(f" BOTTOM R{pad_length:.0f}X{pad_width:.0f}")

                lines.append("")
                padstack_counter += 1

        lines.append("*END_DEFINE_PADSTACK*")
        lines.append("")

        # Step 2: Create part definition with pad placements
        lines.append("! ===== PART DEFINITION =====")
        lines.append("*PART*")
        lines.append(f"{footprint_name}")
        lines.append("")

        lines.append("! Pad placements:")
        for pad in pads:
            padstack_name = self.generate_pad_name_for_script(pad)
            pin_number = pad.get('pin_number', '1')
            abs_x, abs_y = resolver.get_absolute_position(pad)
            
            # Convert to mils and reference the padstack
            x_mils = abs_x * 1000
            y_mils = abs_y * 1000
            lines.append(f"{pin_number} {x_mils:.0f} {y_mils:.0f} {unique_padstacks[padstack_name]}")

        lines.append("")

        # Get dimensions and settings for geometry generation
        origin_offset_x = to_decimal(data.get('origin_offset_x', '0'))
        origin_offset_y = to_decimal(data.get('origin_offset_y', '0'))
        body_length = to_decimal(data.get('body_length', '0'))
        body_width = to_decimal(data.get('body_width', '0'))
        body_shape = data.get('body_shape', 'rectangle')
        body_chamfer = to_decimal(data.get('body_chamfer', '0'))
        chamfer_corners = data.get('chamfer_corners', {})

        # Calculate body corners with origin offset (in mm)
        tl = (origin_offset_x, origin_offset_y)  # Top-left
        tr = (origin_offset_x + body_length, origin_offset_y)  # Top-right
        bl = (origin_offset_x, origin_offset_y - body_width)  # Bottom-left
        br = (origin_offset_x + body_length, origin_offset_y - body_width)  # Bottom-right

        # Calculate pad bounds for silkscreen gap calculation
        pad_bounds_list = []
        for pad in pads:
            abs_x, abs_y = resolver.get_absolute_position(pad)
            pad_bounds = self.calculate_pad_bounds_for_script(pad, abs_x, abs_y)
            if pad_bounds:
                pad_bounds_list.append(pad_bounds)

        # Step 3: Generate Assembly Layer with Chamfer Support
        if body_length > 0 and body_width > 0:
            lines.append("! ===== ASSEMBLY LAYER =====")
            assembly_width = to_decimal(data.get('body_line_width', '0.05')) * 1000

            if body_shape == 'round':
                # Round assembly
                radius = max(body_length, body_width) / Decimal('2')
                center_x = (origin_offset_x + body_length / Decimal('2')) * 1000
                center_y = (origin_offset_y - body_width / Decimal('2')) * 1000
                radius_mils = radius * 1000
                lines.append(f"CIRCLE {center_x:.0f} {center_y:.0f} {radius_mils:.0f} {assembly_width:.0f} ASSEMBLY_TOP")
            else:
                # Rectangular assembly with chamfer support
                if body_chamfer > 0 and any(chamfer_corners.values()):
                    # Generate chamfered body outline
                    lines.append("! Body outline assembly (chamfered)")
                    assembly_segments = self.generate_chamfered_body_segments_pads(
                        tl, tr, bl, br, body_chamfer, chamfer_corners
                    )
                    for (x1, y1), (x2, y2) in assembly_segments:
                        lines.append(f"LINE {x1*1000:.0f} {y1*1000:.0f} {x2*1000:.0f} {y2*1000:.0f} {assembly_width:.0f} ASSEMBLY_TOP")
                else:
                    # Standard rectangular body
                    lines.append("! Body outline assembly")
                    lines.append(f"LINE {tl[0]*1000:.0f} {tl[1]*1000:.0f} {tr[0]*1000:.0f} {tr[1]*1000:.0f} {assembly_width:.0f} ASSEMBLY_TOP")
                    lines.append(f"LINE {tr[0]*1000:.0f} {tr[1]*1000:.0f} {br[0]*1000:.0f} {br[1]*1000:.0f} {assembly_width:.0f} ASSEMBLY_TOP")
                    lines.append(f"LINE {br[0]*1000:.0f} {br[1]*1000:.0f} {bl[0]*1000:.0f} {bl[1]*1000:.0f} {assembly_width:.0f} ASSEMBLY_TOP")
                    lines.append(f"LINE {bl[0]*1000:.0f} {bl[1]*1000:.0f} {tl[0]*1000:.0f} {tl[1]*1000:.0f} {assembly_width:.0f} ASSEMBLY_TOP")

            lines.append("")

        # Step 4: Generate Silkscreen with Gap Logic and Chamfer Support
        if data.get('silkscreen_enabled', True) and body_length > 0 and body_width > 0:
            lines.append("! ===== SILKSCREEN WITH PAD GAPS =====")
            silkscreen_width = to_decimal(data.get('silkscreen_line_width', '0.15')) * 1000
            silkscreen_gap = to_decimal(data.get('silkscreen_airgap', '0.15'))
            follow_chamfer = data.get('silkscreen_follow_chamfer', False)

            if body_shape == 'round':
                # Round silkscreen - simplified approach
                radius = max(body_length, body_width) / Decimal('2')
                center_x = (origin_offset_x + body_length / Decimal('2')) * 1000
                center_y = (origin_offset_y - body_width / Decimal('2')) * 1000
                radius_mils = radius * 1000
                lines.append(f"! NOTE: Round silkscreen with pad gaps requires manual editing")
                lines.append(f"CIRCLE {center_x:.0f} {center_y:.0f} {radius_mils:.0f} {silkscreen_width:.0f} SILK_TOP")
            else:
                # Rectangular silkscreen with proper gap logic
                if follow_chamfer and body_chamfer > 0 and any(chamfer_corners.values()):
                    # Generate chamfered silkscreen with gaps
                    lines.append("! Chamfered silkscreen with pad gaps")
                    silk_segments = self.generate_chamfered_silkscreen_segments_pads(
                        tl, tr, bl, br, body_chamfer, chamfer_corners, pad_bounds_list, silkscreen_gap
                    )
                else:
                    # Standard rectangular silkscreen with gaps
                    lines.append("! Rectangular silkscreen with pad gaps")
                    silk_segments = self.generate_standard_silkscreen_segments_pads(
                        tl, tr, bl, br, pad_bounds_list, silkscreen_gap
                    )

                # Generate the silkscreen line commands
                for (x1, y1), (x2, y2) in silk_segments:
                    lines.append(f"LINE {x1*1000:.0f} {y1*1000:.0f} {x2*1000:.0f} {y2*1000:.0f} {silkscreen_width:.0f} SILK_TOP")

            lines.append("")

        # Step 5: Generate Proper Courtyard with Individual Side Calculations
        lines.append("! ===== COURTYARD WITH PROPER CALCULATIONS =====")
        base_expansion = to_decimal(data.get('courtyard_expansion', '0.25'))
        courtyard_line_width = to_decimal(data.get('courtyard_line_width', '0.1'))
        body_line_width = to_decimal(data.get('body_line_width', '0.05'))
        courtyard_width = courtyard_line_width * 1000

        if body_length > 0 and body_width > 0:
            if body_shape == 'round':
                # Round courtyard logic
                radius = max(body_length, body_width) / Decimal('2')
                center_x = (origin_offset_x + body_length / Decimal('2'))
                center_y = (origin_offset_y - body_width / Decimal('2'))
                
                # Check if pads extend beyond body circle
                max_pad_distance = Decimal('0')
                if pad_bounds_list:
                    for pad_bounds in pad_bounds_list:
                        px_min, py_min, px_max, py_max = [to_decimal(str(coord)) for coord in pad_bounds]
                        # Check all corners of pad bounds
                        pad_corners = [(px_min, py_min), (px_max, py_min), (px_max, py_max), (px_min, py_max)]
                        for corner_x, corner_y in pad_corners:
                            distance = ((corner_x - center_x)**2 + (corner_y - center_y)**2).sqrt()
                            max_pad_distance = max(max_pad_distance, distance)

                # Determine courtyard radius
                if max_pad_distance > radius:
                    courtyard_radius = max_pad_distance + base_expansion + (courtyard_line_width / Decimal('2'))
                else:
                    courtyard_radius = radius + base_expansion + (courtyard_line_width / Decimal('2')) + (body_line_width / Decimal('2'))

                lines.append(f"CIRCLE {center_x*1000:.0f} {center_y*1000:.0f} {courtyard_radius*1000:.0f} {courtyard_width:.0f} BOARD_GEOMETRY")
            else:
                # Rectangular courtyard with proper individual side calculations
                lines.append("! Rectangular courtyard with individual side calculations")
                
                # Body bounds adjusted for origin offset
                body_bounds_adjusted = [tl[0], bl[1], tr[0], tl[1]]  # [min_x, min_y, max_x, max_y]
                
                # Calculate overall pad bounds
                pad_bounds_for_courtyard = None
                if pad_bounds_list:
                    min_x = min(pb[0] for pb in pad_bounds_list)
                    min_y = min(pb[1] for pb in pad_bounds_list)
                    max_x = max(pb[2] for pb in pad_bounds_list)
                    max_y = max(pb[3] for pb in pad_bounds_list)
                    pad_bounds_for_courtyard = [min_x, min_y, max_x, max_y]

                # Determine outermost bounds for each side
                courtyard_line_w = courtyard_line_width / 2
                body_line_w = body_line_width / 2
                body_linecourtyard = courtyard_line_w + body_line_w

                if body_bounds_adjusted and pad_bounds_for_courtyard:
                    # Calculate individual side expansions
                    expansions = {}
                    
                    # Left side
                    if body_bounds_adjusted[0] <= pad_bounds_for_courtyard[0]:
                        outermost_left = body_bounds_adjusted[0]
                        expansions['left'] = base_expansion + body_linecourtyard
                    else:
                        outermost_left = pad_bounds_for_courtyard[0]
                        expansions['left'] = base_expansion + courtyard_line_w

                    # Right side  
                    if body_bounds_adjusted[2] >= pad_bounds_for_courtyard[2]:
                        outermost_right = body_bounds_adjusted[2]
                        expansions['right'] = base_expansion + body_linecourtyard
                    else:
                        outermost_right = pad_bounds_for_courtyard[2]
                        expansions['right'] = base_expansion + courtyard_line_w

                    # Bottom side
                    if body_bounds_adjusted[1] <= pad_bounds_for_courtyard[1]:
                        outermost_bottom = body_bounds_adjusted[1]
                        expansions['bottom'] = base_expansion + body_linecourtyard
                    else:
                        outermost_bottom = pad_bounds_for_courtyard[1]
                        expansions['bottom'] = base_expansion + courtyard_line_w

                    # Top side
                    if body_bounds_adjusted[3] >= pad_bounds_for_courtyard[3]:
                        outermost_top = body_bounds_adjusted[3]
                        expansions['top'] = base_expansion + body_linecourtyard
                    else:
                        outermost_top = pad_bounds_for_courtyard[3]
                        expansions['top'] = base_expansion + courtyard_line_w

                elif body_bounds_adjusted:
                    outermost_left = body_bounds_adjusted[0]
                    outermost_right = body_bounds_adjusted[2]
                    outermost_bottom = body_bounds_adjusted[1]
                    outermost_top = body_bounds_adjusted[3]
                    expansion_val = base_expansion + body_linecourtyard
                    expansions = {'left': expansion_val, 'right': expansion_val, 'bottom': expansion_val, 'top': expansion_val}
                elif pad_bounds_for_courtyard:
                    outermost_left = pad_bounds_for_courtyard[0]
                    outermost_right = pad_bounds_for_courtyard[2]
                    outermost_bottom = pad_bounds_for_courtyard[1]
                    outermost_top = pad_bounds_for_courtyard[3]
                    expansion_val = base_expansion + courtyard_line_w
                    expansions = {'left': expansion_val, 'right': expansion_val, 'bottom': expansion_val, 'top': expansion_val}
                else:
                    lines.append("! No geometry found for courtyard")

                if 'expansions' in locals():
                    # Calculate courtyard bounds with individual expansions
                    cy_left = (outermost_left - expansions['left']) * 1000
                    cy_right = (outermost_right + expansions['right']) * 1000
                    cy_bottom = (outermost_bottom - expansions['bottom']) * 1000
                    cy_top = (outermost_top + expansions['top']) * 1000

                    # Generate courtyard rectangle
                    lines.append(f"LINE {cy_left:.0f} {cy_top:.0f} {cy_right:.0f} {cy_top:.0f} {courtyard_width:.0f} BOARD_GEOMETRY")
                    lines.append(f"LINE {cy_right:.0f} {cy_top:.0f} {cy_right:.0f} {cy_bottom:.0f} {courtyard_width:.0f} BOARD_GEOMETRY")
                    lines.append(f"LINE {cy_right:.0f} {cy_bottom:.0f} {cy_left:.0f} {cy_bottom:.0f} {courtyard_width:.0f} BOARD_GEOMETRY")
                    lines.append(f"LINE {cy_left:.0f} {cy_bottom:.0f} {cy_left:.0f} {cy_top:.0f} {courtyard_width:.0f} BOARD_GEOMETRY")

        lines.append("")
        lines.append("*END*")

        # Save script
        script = '\n'.join(lines)
        output_path = account_settings.get('pads_output_path', os.path.expanduser("~/Documents/PADS"))
        os.makedirs(output_path, exist_ok=True)
        file_name = os.path.join(output_path, f"{footprint_name}_pads_enhanced.pt")

        try:
            with open(file_name, "w") as f:
                f.write(script)
            self.show_script_dialog("Enhanced PADS Script Generated", file_name, script)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save PADS script: {str(e)}")

    # Helper methods for PADS script generation
    def generate_chamfered_body_segments_pads(self, tl, tr, bl, br, chamfer_size, chamfer_corners):
        """Generate chamfered body line segments for PADS"""
        segments = []
        chamfer_size = to_decimal(str(chamfer_size))
        
        # Define corner points with chamfers
        points = []
        
        # Start from top-left, moving clockwise
        if chamfer_corners.get('tl', False):
            points.append((tl[0], tl[1] - chamfer_size))
            points.append((tl[0] + chamfer_size, tl[1]))
        else:
            points.append((tl[0], tl[1]))
        
        # Top edge to top-right
        if chamfer_corners.get('tr', False):
            points.append((tr[0] - chamfer_size, tr[1]))
            points.append((tr[0], tr[1] - chamfer_size))
        else:
            points.append((tr[0], tr[1]))
        
        # Right edge to bottom-right
        if chamfer_corners.get('br', False):
            points.append((br[0], br[1] + chamfer_size))
            points.append((br[0] - chamfer_size, br[1]))
        else:
            points.append((br[0], br[1]))
        
        # Bottom edge to bottom-left
        if chamfer_corners.get('bl', False):
            points.append((bl[0] + chamfer_size, bl[1]))
            points.append((bl[0], bl[1] + chamfer_size))
        else:
            points.append((bl[0], bl[1]))
        
        # Generate line segments
        for i in range(len(points)):
            p1 = points[i]
            p2 = points[(i + 1) % len(points)]
            segments.append((p1, p2))
        
        return segments

    def generate_standard_silkscreen_segments_pads(self, tl, tr, bl, br, pad_bounds_list, gap):
        """Generate standard rectangular silkscreen segments with pad gaps for PADS"""
        segments = []
        
        # Top line
        segments.extend(self.generate_silkscreen_segments_with_gaps_pads(
            tl[0], tl[1], tr[0], tr[1], pad_bounds_list, gap, 'horizontal'))
        
        # Right line
        segments.extend(self.generate_silkscreen_segments_with_gaps_pads(
            tr[0], tr[1], br[0], br[1], pad_bounds_list, gap, 'vertical'))
        
        # Bottom line
        segments.extend(self.generate_silkscreen_segments_with_gaps_pads(
            br[0], br[1], bl[0], bl[1], pad_bounds_list, gap, 'horizontal'))
        
        # Left line
        segments.extend(self.generate_silkscreen_segments_with_gaps_pads(
            bl[0], bl[1], tl[0], tl[1], pad_bounds_list, gap, 'vertical'))
        
        return segments

    def generate_chamfered_silkscreen_segments_pads(self, tl, tr, bl, br, chamfer_size, chamfer_corners, pad_bounds_list, gap):
        """Generate chamfered silkscreen segments with pad gaps for PADS"""
        segments = []
        
        # Get chamfered body segments first
        body_segments = self.generate_chamfered_body_segments_pads(tl, tr, bl, br, chamfer_size, chamfer_corners)
        
        # For each body segment, check for pad gaps
        for (x1, y1), (x2, y2) in body_segments:
            # Determine if this is horizontal or vertical segment
            if abs(x2 - x1) > abs(y2 - y1):
                orientation = 'horizontal'
            else:
                orientation = 'vertical'
            
            # Generate segments with gaps
            gap_segments = self.generate_silkscreen_segments_with_gaps_pads(
                x1, y1, x2, y2, pad_bounds_list, gap, orientation)
            segments.extend(gap_segments)
        
        return segments

    def generate_silkscreen_segments_with_gaps_pads(self, x1, y1, x2, y2, pad_bounds_list, gap, orientation):
        """Generate line segments with gaps where pads would interfere - PADS version"""
        segments = []
        gap_decimal = to_decimal(str(gap))

        if orientation == 'horizontal':
            start_pos = min(x1, x2)
            end_pos = max(x1, x2)
            line_y = y1

            # Find intersections with pads
            intersections = []
            for pad_bounds in pad_bounds_list:
                if not pad_bounds:
                    continue
                
                px_min, py_min, px_max, py_max = [to_decimal(str(coord)) for coord in pad_bounds]
                pad_min_x = px_min - gap_decimal
                pad_max_x = px_max + gap_decimal
                pad_min_y = py_min - gap_decimal
                pad_max_y = py_max + gap_decimal

                # Check if horizontal line intersects with expanded pad
                if (line_y >= pad_min_y and line_y <= pad_max_y and
                    pad_max_x >= start_pos and pad_min_x <= end_pos):
                    
                    inter_start = max(start_pos, pad_min_x)
                    inter_end = min(end_pos, pad_max_x)
                    intersections.append((inter_start, inter_end))

            # Merge overlapping intersections
            merged = self.merge_intervals(intersections)

            # Generate segments between gaps
            current_pos = start_pos
            for gap_start, gap_end in merged:
                if current_pos < gap_start:
                    segments.append(((current_pos, line_y), (gap_start, line_y)))
                current_pos = gap_end

            if current_pos < end_pos:
                segments.append(((current_pos, line_y), (end_pos, line_y)))

        else:  # vertical
            start_pos = min(y1, y2)
            end_pos = max(y1, y2)
            line_x = x1

            intersections = []
            for pad_bounds in pad_bounds_list:
                if not pad_bounds:
                    continue
                
                px_min, py_min, px_max, py_max = [to_decimal(str(coord)) for coord in pad_bounds]
                pad_min_x = px_min - gap_decimal
                pad_max_x = px_max + gap_decimal
                pad_min_y = py_min - gap_decimal
                pad_max_y = py_max + gap_decimal

                if (line_x >= pad_min_x and line_x <= pad_max_x and
                    pad_max_y >= start_pos and pad_min_y <= end_pos):
                    
                    inter_start = max(start_pos, pad_min_y)
                    inter_end = min(end_pos, pad_max_y)
                    intersections.append((inter_start, inter_end))

            merged = self.merge_intervals(intersections)

            current_pos = start_pos
            for gap_start, gap_end in merged:
                if current_pos < gap_start:
                    segments.append(((line_x, current_pos), (line_x, gap_start)))
                current_pos = gap_end

            if current_pos < end_pos:
                segments.append(((line_x, current_pos), (line_x, end_pos)))

        return segments




    def generate_xpedition_script(self):
        """Generate Xpedition Layout script"""
        data = self.get_footprint_data()
        settings = self.settings_panel.get_settings()
        
        lines = []
        footprint_name = data.get('footprint_name', 'Unnamed')
        
        # Xpedition script header
        lines.append("# Xpedition Layout Script")
        lines.append(f"# Footprint: {footprint_name}")
        lines.append("")
        
        lines.append("BeginPart")
        lines.append(f"PartName = {footprint_name}")
        
        # Generate pads
        pads = data.get('padstacks', [])
        resolver = PadPositionResolver(pads)
        
        for pad in pads:
            pad_type = pad.get('type', 'square')
            name = pad.get('pin_number', '1')
            abs_x, abs_y = resolver.get_absolute_position(pad)
            
            lines.append(f"BeginPin")
            lines.append(f"PinName = {name}")
            lines.append(f"X = {abs_x}")
            lines.append(f"Y = {abs_y}")
            
            if pad_type == 'square':
                size = to_decimal(pad.get('size', 1))
                lines.append(f"PadShape = Rectangle")
                lines.append(f"PadWidth = {size}")
                lines.append(f"PadHeight = {size}")
            elif pad_type in ['rectangle', 'SMD-oblong']:
                length = to_decimal(pad.get('length', 1))
                width = to_decimal(pad.get('width', 1))
                lines.append(f"PadShape = Rectangle")
                lines.append(f"PadWidth = {length}")
                lines.append(f"PadHeight = {width}")
            elif pad_type == 'round':
                diameter = to_decimal(pad.get('diameter', 1))
                lines.append(f"PadShape = Circle")
                lines.append(f"PadDiameter = {diameter}")
            elif pad_type in ['PTH', 'NPTH']:
                hole_dia = to_decimal(pad.get('hole_diameter', 0.8))
                pad_dia = to_decimal(pad.get('pad_diameter', 1.2)) if pad_type == 'PTH' else hole_dia
                lines.append(f"PadShape = Circle")
                lines.append(f"PadDiameter = {pad_dia}")
                lines.append(f"HoleDiameter = {hole_dia}")
            
            lines.append("EndPin")
        
        lines.append("EndPart")
        
        # Save script
        script = '\n'.join(lines)
        output_path = settings.get('xpedition_output_path', os.path.expanduser("~/Documents/Xpedition"))
        os.makedirs(output_path, exist_ok=True)
        file_name = os.path.join(output_path, f"{footprint_name}_xpedition.txt")
        
        try:
            with open(file_name, "w") as f:
                f.write(script)
            self.show_script_dialog("Xpedition Script Generated", file_name, script)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save Xpedition script: {str(e)}")

    def show_script_dialog(self, title, filename, script):
        """Show script generation dialog"""
        dialog = QMessageBox(self)
        dialog.setWindowTitle(title)
        dialog.setText(f"Script saved to:\n{filename}")
        dialog.setDetailedText(script)
        dialog.setIcon(QMessageBox.Icon.Information)
        dialog.exec()

    def calculate_pad_bounds_for_script(self, pad, abs_x, abs_y):
        """Calculate pad bounds for script generation"""
        pad_type = pad.get('type', 'square')
        
        # Convert inputs to Decimal
        abs_x = to_decimal(str(abs_x))
        abs_y = to_decimal(str(abs_y))
        
        if pad_type == 'square':
            size = to_decimal(pad.get('size', '1'))
            half_size = size / Decimal('2')
            return (abs_x - half_size, abs_y - half_size, abs_x + half_size, abs_y + half_size)
            
        elif pad_type in ['rectangle', 'rounded_rectangle', 'SMD-oblong']:
            length = to_decimal(pad.get('length', '1'))
            width = to_decimal(pad.get('width', '1'))
            half_length = length / Decimal('2')
            half_width = width / Decimal('2')
            return (abs_x - half_length, abs_y - half_width, abs_x + half_length, abs_y + half_width)
            
        elif pad_type == 'PTH_rectangle':
            pad_length = to_decimal(pad.get('pad_length', '2.0'))
            pad_width = to_decimal(pad.get('pad_width', '1.2'))
            half_length = pad_length / Decimal('2')
            half_width = pad_width / Decimal('2')
            return (abs_x - half_length, abs_y - half_width, abs_x + half_length, abs_y + half_width)
            
        elif pad_type in ['round', 'D-shape']:
            diameter = to_decimal(pad.get('diameter', '1'))
            half_diameter = diameter / Decimal('2')
            return (abs_x - half_diameter, abs_y - half_diameter, abs_x + half_diameter, abs_y + half_diameter)
            
        elif pad_type in ['PTH', 'NPTH']:
            if pad_type == 'PTH':
                diameter = to_decimal(pad.get('pad_diameter', '1.2'))
            else:
                diameter = to_decimal(pad.get('hole_diameter', '0.8'))
            half_diameter = diameter / Decimal('2')
            return (abs_x - half_diameter, abs_y - half_diameter, abs_x + half_diameter, abs_y + half_diameter)
        
        # ADD MISSING CASES:
        elif pad_type in ['PTH_oblong', 'NPTH_oblong']:
            if pad_type == 'PTH_oblong':
                length = to_decimal(pad.get('pad_length', '2.0'))
                width = to_decimal(pad.get('pad_width', '1.2'))
            else:
                length = to_decimal(pad.get('hole_length', '1.5'))
                width = to_decimal(pad.get('hole_width', '0.8'))
            
            # Handle rotation
            rotation = pad.get('rotation', 0)
            try:
                rotation_deg = float(to_decimal(str(rotation)))
            except (ValueError, TypeError):
                rotation_deg = 0
            
            if rotation_deg != 0:
                return self._calculate_rotated_bounds_for_script(abs_x, abs_y, length, width, rotation_deg)
            else:
                half_length = length / Decimal('2')
                half_width = width / Decimal('2')
                return (abs_x - half_length, abs_y - half_width, abs_x + half_length, abs_y + half_width)
        
        elif pad_type == 'NPTH_rectangle':  # ADD THIS MISSING CASE
            hole_length = to_decimal(pad.get('hole_length', '1.5'))
            hole_width = to_decimal(pad.get('hole_width', '0.8'))
            
            # Handle rotation
            rotation = pad.get('rotation', 0)
            try:
                rotation_deg = float(to_decimal(str(rotation)))
            except (ValueError, TypeError):
                rotation_deg = 0
            
            if rotation_deg != 0:
                return self._calculate_rotated_bounds_for_script(abs_x, abs_y, hole_length, hole_width, rotation_deg)
            else:
                half_length = hole_length / Decimal('2')
                half_width = hole_width / Decimal('2')
                return (abs_x - half_length, abs_y - half_width, abs_x + half_length, abs_y + half_width)
        
        elif pad_type == 'custom':
            # Handle custom polygon bounds
            polygon_points = self.calculate_polygon_points_absolute(pad, abs_x, abs_y)
            if polygon_points:
                xs = [p.x() for p in polygon_points]
                ys = [p.y() for p in polygon_points]
                return (min(xs), min(ys), max(xs), max(ys))
        
        # Default fallback
        half_unit = Decimal('0.5')
        return (abs_x - half_unit, abs_y - half_unit, abs_x + half_unit, abs_y + half_unit)

    def start_update_thread(self):
        self.update_thread = UpdateThread(self)
        self.update_thread.update_signal.connect(self.renderer.update_footprint)
        self.update_thread.start()

    def closeEvent(self, event):
        """Save settings on close"""
        self.save_app_settings()
        if hasattr(self, 'update_thread'):
            self.update_thread.stop()
            self.update_thread.wait()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Set application-wide dark theme
    app.setStyle('Fusion')
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(43, 43, 43))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Base, QColor(60, 60, 60))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(80, 80, 80))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Button, QColor(74, 74, 74))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))
    app.setPalette(palette)

    window = FootprintDesigner()
    window.show()

    sys.exit(app.exec())














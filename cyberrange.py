from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import json
import os
from datetime import datetime, timedelta
import sqlite3
import threading
import time

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# Configuration
GNS3_SERVER_URL = 'http://10.48.229.210:80'  # Default GNS3 server URL
GNS3_API_BASE = f'{GNS3_SERVER_URL}/v2'

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username, email, role='student'):
        self.id = id
        self.username = username
        self.email = email
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect('cyberrange.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    
    if user_data:
        return User(user_data[0], user_data[1], user_data[2], user_data[4])
    return None

def init_db():
    """Initialize the database with required tables"""
    conn = sqlite3.connect('cyberrange.db')
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'student',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Scenarios table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scenarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            difficulty TEXT DEFAULT 'beginner',
            project_id TEXT,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    ''')
    
    # User sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            scenario_id INTEGER,
            project_id TEXT,
            status TEXT DEFAULT 'active',
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ended_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (scenario_id) REFERENCES scenarios (id)
        )
    ''')
    
    # Create default admin user
    cursor.execute('SELECT * FROM users WHERE username = ?', ('admin',))
    if not cursor.fetchone():
        admin_hash = generate_password_hash('admin123')
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, role)
            VALUES (?, ?, ?, ?)
        ''', ('admin', 'admin@cyberrange.local', admin_hash, 'instructor'))
    
    conn.commit()
    conn.close()

class GNS3Client:
    """Client for interacting with GNS3 API"""
    
    def __init__(self, server_url=GNS3_SERVER_URL):
        self.server_url = server_url
        self.api_base = f'{server_url}/v2'
    
    def get_projects(self):
        """Get all projects from GNS3"""
        try:
            response = requests.get(f'{self.api_base}/projects')
            return response.json() if response.status_code == 200 else []
        except:
            return []
    
    def create_project(self, name, scenario_id=None):
        """Create a new GNS3 project"""
        try:
            project_name = f"cyberrange_{scenario_id}_{name}" if scenario_id else name
            data = {'name': project_name}
            response = requests.post(f'{self.api_base}/projects', json=data)
            return response.json() if response.status_code == 201 else None
        except:
            return None
    
    def duplicate_project(self, source_project_id, new_name):
        """Duplicate an existing project for a user"""
        try:
            data = {'name': new_name}
            response = requests.post(f'{self.api_base}/projects/{source_project_id}/duplicate', json=data)
            return response.json() if response.status_code == 201 else None
        except:
            return None
    
    def get_project_nodes(self, project_id):
        """Get all nodes in a project"""
        try:
            response = requests.get(f'{self.api_base}/projects/{project_id}/nodes')
            return response.json() if response.status_code == 200 else []
        except:
            return []
    
    def start_project(self, project_id):
        """Start all nodes in a project"""
        try:
            response = requests.post(f'{self.api_base}/projects/{project_id}/nodes/start')
            return response.status_code == 204
        except:
            return False
    
    def stop_project(self, project_id):
        """Stop all nodes in a project"""
        try:
            response = requests.post(f'{self.api_base}/projects/{project_id}/nodes/stop')
            return response.status_code == 204
        except:
            return False
    
    def delete_project(self, project_id):
        """Delete a project"""
        try:
            response = requests.delete(f'{self.api_base}/projects/{project_id}')
            return response.status_code == 204
        except:
            return False

# Initialize GNS3 client
gns3 = GNS3Client()

@app.route('/')
def index():
    """Main dashboard"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('cyberrange.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data and check_password_hash(user_data[3], password):
            user = User(user_data[0], user_data[1], user_data[2], user_data[4])
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        conn = sqlite3.connect('cyberrange.db')
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute('SELECT * FROM users WHERE username = ? OR email = ?', (username, email))
        if cursor.fetchone():
            flash('Username or email already exists')
            conn.close()
            return render_template('register.html')
        
        # Create new user
        password_hash = generate_password_hash(password)
        cursor.execute('''
            INSERT INTO users (username, email, password_hash)
            VALUES (?, ?, ?)
        ''', (username, email, password_hash))
        
        conn.commit()
        conn.close()
        
        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard"""
    conn = sqlite3.connect('cyberrange.db')
    cursor = conn.cursor()
    
    # Get user's active sessions
    cursor.execute('''
        SELECT us.*, s.name, s.description 
        FROM user_sessions us
        JOIN scenarios s ON us.scenario_id = s.id
        WHERE us.user_id = ? AND us.status = 'active'
    ''', (current_user.id,))
    active_sessions = cursor.fetchall()
    
    # Get available scenarios
    cursor.execute('SELECT * FROM scenarios')
    scenarios = cursor.fetchall()
    
    conn.close()
    
    return render_template('dashboard.html', 
                         active_sessions=active_sessions, 
                         scenarios=scenarios,
                         user_role=current_user.role)

@app.route('/scenarios')
@login_required
def scenarios():
    """List all available scenarios"""
    conn = sqlite3.connect('cyberrange.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM scenarios')
    scenarios = cursor.fetchall()
    conn.close()
    
    return render_template('scenarios.html', scenarios=scenarios)

@app.route('/create_scenario', methods=['GET', 'POST'])
@login_required
def create_scenario():
    """Create a new scenario (instructors only)"""
    if current_user.role != 'instructor':
        flash('Access denied. Instructor privileges required.')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        difficulty = request.form['difficulty']
        
        # Create GNS3 project for this scenario
        project = gns3.create_project(name)
        if not project:
            flash('Failed to create GNS3 project')
            return render_template('create_scenario.html')
        
        # Save scenario to database
        conn = sqlite3.connect('cyberrange.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO scenarios (name, description, difficulty, project_id, created_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, description, difficulty, project['project_id'], current_user.id))
        conn.commit()
        conn.close()
        
        flash('Scenario created successfully!')
        return redirect(url_for('scenarios'))
    
    return render_template('create_scenario.html')

@app.route('/launch_scenario/<int:scenario_id>')
@login_required
def launch_scenario(scenario_id):
    """Launch a scenario for the current user"""
    conn = sqlite3.connect('cyberrange.db')
    cursor = conn.cursor()
    
    # Get scenario details
    cursor.execute('SELECT * FROM scenarios WHERE id = ?', (scenario_id,))
    scenario = cursor.fetchone()
    
    if not scenario:
        flash('Scenario not found')
        return redirect(url_for('scenarios'))
    
    # Check if user already has an active session for this scenario
    cursor.execute('''
        SELECT * FROM user_sessions 
        WHERE user_id = ? AND scenario_id = ? AND status = 'active'
    ''', (current_user.id, scenario_id))
    
    if cursor.fetchone():
        flash('You already have an active session for this scenario')
        return redirect(url_for('dashboard'))
    
    # Duplicate the scenario project for this user
    new_project_name = f"{scenario[1]}_{current_user.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    duplicated_project = gns3.duplicate_project(scenario[4], new_project_name)
    
    if not duplicated_project:
        flash('Failed to launch scenario')
        conn.close()
        return redirect(url_for('scenarios'))
    
    # Create user session
    cursor.execute('''
        INSERT INTO user_sessions (user_id, scenario_id, project_id, status)
        VALUES (?, ?, ?, 'active')
    ''', (current_user.id, scenario_id, duplicated_project['project_id']))
    
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    # Start the project
    gns3.start_project(duplicated_project['project_id'])
    
    flash('Scenario launched successfully!')
    return redirect(url_for('session_view', session_id=session_id))

@app.route('/session/<int:session_id>')
@login_required
def session_view(session_id):
    """View an active session"""
    conn = sqlite3.connect('cyberrange.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT us.*, s.name, s.description 
        FROM user_sessions us
        JOIN scenarios s ON us.scenario_id = s.id
        WHERE us.id = ? AND us.user_id = ?
    ''', (session_id, current_user.id))
    
    session_data = cursor.fetchone()
    conn.close()
    
    if not session_data:
        flash('Session not found')
        return redirect(url_for('dashboard'))
    
    # Get project nodes
    nodes = gns3.get_project_nodes(session_data[3])  # project_id
    
    return render_template('session.html', 
                         session=session_data, 
                         nodes=nodes,
                         gns3_url=f"{GNS3_SERVER_URL}/static/web-ui/server/1/project/{session_data[3]}")

@app.route('/end_session/<int:session_id>')
@login_required
def end_session(session_id):
    """End an active session"""
    conn = sqlite3.connect('cyberrange.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM user_sessions 
        WHERE id = ? AND user_id = ? AND status = 'active'
    ''', (session_id, current_user.id))
    
    session_data = cursor.fetchone()
    
    if session_data:
        # Stop and delete the GNS3 project
        gns3.stop_project(session_data[3])  # project_id
        gns3.delete_project(session_data[3])
        
        # Update session status
        cursor.execute('''
            UPDATE user_sessions 
            SET status = 'ended', ended_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (session_id,))
        
        conn.commit()
        flash('Session ended successfully')
    else:
        flash('Session not found or already ended')
    
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/api/nodes/<project_id>')
@login_required
def api_get_nodes(project_id):
    """API endpoint to get project nodes"""
    nodes = gns3.get_project_nodes(project_id)
    return jsonify(nodes)

@app.route('/admin')
@login_required
def admin():
    """Admin panel (instructors only)"""
    if current_user.role != 'instructor':
        flash('Access denied. Instructor privileges required.')
        return redirect(url_for('dashboard'))
    
    conn = sqlite3.connect('cyberrange.db')
    cursor = conn.cursor()
    
    # Get all users
    cursor.execute('SELECT * FROM users')
    users = cursor.fetchall()
    
    # Get all scenarios
    cursor.execute('SELECT * FROM scenarios')
    scenarios = cursor.fetchall()
    
    # Get active sessions
    cursor.execute('''
        SELECT us.*, u.username, s.name as scenario_name
        FROM user_sessions us
        JOIN users u ON us.user_id = u.id
        JOIN scenarios s ON us.scenario_id = s.id
        WHERE us.status = 'active'
    ''')
    active_sessions = cursor.fetchall()
    
    conn.close()
    
    return render_template('admin.html', 
                         users=users, 
                         scenarios=scenarios, 
                         active_sessions=active_sessions)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)

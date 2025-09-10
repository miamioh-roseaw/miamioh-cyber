GNS3 Cyberrange Flask Wrapper
A comprehensive Flask-based wrapper for GNS3 that transforms it into a multi-user cyberrange platform for cybersecurity training.

Features
Multi-user authentication with role-based access (students/instructors)
Scenario management - Create, launch, and manage cybersecurity training scenarios
Session isolation - Each user gets their own isolated copy of scenarios
Web interface - Clean, responsive UI for managing training sessions
Admin panel - Instructor dashboard for monitoring and management
GNS3 integration - Seamless integration with GNS3 server API
Requirements
System Requirements
Python 3.8+
GNS3 Server running (version 2.2+)
SQLite3
Python Dependencies
txt
Flask==2.3.3
Flask-Login==0.6.3
Werkzeug==2.3.7
requests==2.31.0
Installation
Clone or download the application files
bash
mkdir gns3-cyberrange
cd gns3-cyberrange
Install Python dependencies
bash
pip install -r requirements.txt
Create the templates directory structure
bash
mkdir templates
Create the following template files in the templates/ directory:
base.html
index.html
login.html
register.html
dashboard.html
scenarios.html
create_scenario.html
session.html
admin.html
Configure GNS3 Server Make sure GNS3 server is running and accessible. Update the configuration in app.py:
python
GNS3_SERVER_URL = 'http://localhost:3080'  # Change if different
Initialize the application
bash
python app.py
Configuration
GNS3 Server Setup
Install and start GNS3 server
Ensure the server is accessible at http://localhost:3080 (or update the URL in config)
Make sure the GNS3 server allows API access
Default Credentials
Admin Username: admin
Admin Password: admin123
⚠️ Important: Change the default admin password after first login!

Security Configuration
Update the following in app.py:

python
app.secret_key = 'your-secret-key-change-this'  # Change this!
Usage
For Students
Register for an account at /register
Browse available scenarios at /scenarios
Launch a scenario to get your own isolated environment
Access the GNS3 web interface through the session view
End sessions when done to free up resources
For Instructors
Login with instructor credentials
Create new scenarios at /create_scenario
Configure the GNS3 project topology after creation
Monitor student activity via the admin panel
Manage system resources and user access
API Endpoints
The application provides several API endpoints for integration:

GET /api/nodes/<project_id> - Get nodes in a project
POST /launch_scenario/<scenario_id> - Launch a scenario
GET /end_session/<session_id> - End a session
Directory Structure
gns3-cyberrange/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── cyberrange.db         # SQLite database (auto-created)
├── templates/            # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── scenarios.html
│   ├── create_scenario.html
│   ├── session.html
│   └── admin.html
└── static/              # Static files (CSS, JS, images)
Database Schema
The application uses SQLite with the following tables:

users - User accounts and authentication
scenarios - Training scenario definitions
user_sessions - Active user sessions and history
Workflow
Creating a Scenario (Instructor)
Login as instructor
Navigate to "Create Scenario"
Fill in scenario details (name, description, difficulty)
System creates empty GNS3 project
Configure network topology in GNS3
Scenario is now available to students
Launching a Scenario (Student)
Student selects scenario from list
System duplicates the master GNS3 project
Creates isolated user session
Starts the network devices
Provides web interface access
Student can access console connections
Advanced Configuration
Custom GNS3 Templates
Place custom GNS3 appliance templates in the GNS3 server's appliances directory to make them available in scenarios.

Resource Management
Monitor resource usage through the admin panel. Consider implementing:

Session timeouts
Resource quotas per user
Scheduled cleanup of old projects
Network Isolation
For production use, consider:

VPN access to lab networks
Network segmentation
Firewall rules for isolation
Troubleshooting
Common Issues
GNS3 Server Connection Failed
Verify GNS3 server is running
Check the server URL configuration
Ensure API access is enabled
Session Creation Fails
Check GNS3 server resources
Verify project permissions
Monitor disk space
Template Loading Issues
Check GNS3 appliance configurations
Verify image paths
Ensure proper permissions
Logs and Debugging
Enable Flask debugging for development:

python
app.run(debug=True, host='0.0.0.0', port=5000)
Security Considerations
Change default passwords
Use HTTPS in production
Implement proper session management
Regular security updates
Network isolation between scenarios
Monitor resource usage
Contributing
To extend the platform:

Add new scenario types
Implement additional GNS3 features
Enhance the web interface
Add monitoring and analytics
Integrate with external tools
License
This project is provided as-is for educational purposes. Ensure compliance with GNS3 licensing when using in commercial environments.


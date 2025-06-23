# License Manager Flask Application

A comprehensive license management system built with Flask for managing Cadence, Mentor, Altium, and custom application licenses within a local network.

## Features

- **Dashboard**: Centralized view of all license servers and usage statistics
- **License Server Management**: Support for Cadence, Mentor, and Altium license servers
- **Custom Applications**: Manage licenses for custom Python applications
- **Footprint Database**: Database management with filtering and statistics
- **User Management**: Admin panel for user creation and management
- **Activity Logging**: Track all user activities and system events
- **Background Monitoring**: Automatic license usage monitoring via terminal commands

## Installation

1. Install Python 3.8 or higher
2. Install required packages:
   \`\`\`bash
   pip install -r requirements.txt
   \`\`\`

3. Run the application:
   \`\`\`bash
   python app.py
   \`\`\`

4. Access the application at `http://your-server-ip:5000`

## Default Login

- Username: `admin`
- Password: `admin123`

## Configuration

### Adding License Servers

1. Login as admin
2. Go to Settings page
3. Click "Add Server"
4. Configure:
   - Server Name: Descriptive name
   - Server Type: cadence/mentor/altium
   - Terminal Command: Command to check license usage
   - Total Licenses: Number of available licenses

### Example Terminal Commands

**Cadence:**
\`\`\`bash
lmstat -a -c /path/to/cadence/license.dat
\`\`\`

**Mentor:**
\`\`\`bash
lmstat -a -c /path/to/mentor/license.dat
\`\`\`

**Altium:**
\`\`\`bash
lmstat -a -c /path/to/altium/license.dat
\`\`\`

## API Endpoints

### License Verification API

**POST** `/api/verify_license`

Request body:
\`\`\`json
{
    "username": "user@example.com",
    "email": "user@example.com", 
    "server_id": 1
}
\`\`\`

Response:
\`\`\`json
{
    "status": "verified|denied",
    "message": "License verification message"
}
\`\`\`

## Network Configuration

The application runs on all network interfaces (`0.0.0.0:5000`) by default, making it accessible from other machines on the local network.

To access from other machines:
- Find your server's IP address: `ipconfig` (Windows) or `ifconfig` (Linux/Mac)
- Access via: `http://SERVER_IP:5000`

## Security Notes

- Change default admin password immediately
- Use strong passwords for all users
- Consider using HTTPS in production
- Regularly backup the SQLite database
- Monitor activity logs for suspicious activity

## Database

The application uses SQLite database (`license_manager.db`) which is created automatically on first run.

## Background Monitoring

The system automatically runs terminal commands every 5 minutes to collect license usage data. This runs in a separate thread and updates the database with current usage information.

## Troubleshooting

1. **Port already in use**: Change the port in `app.py` line: `app.run(host='0.0.0.0', port=5000, debug=True)`

2. **Database errors**: Delete `license_manager.db` to reset the database

3. **Terminal commands not working**: Ensure the license server commands are correct and accessible from the server

4. **Network access issues**: Check firewall settings and ensure port 5000 is open

## Support

For issues and feature requests, contact your system administrator.

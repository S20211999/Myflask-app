
# BROKEN CODE:
elif action == 'delete_default_activity':
    response = self.delete_default_activity(request['activity_id'])
    # Missing the 'delete_generated' parameter!

# FIXED CODE:
elif action == 'delete_default_activity':
    response = self.delete_default_activity(
        request['activity_id'],
        request.get('delete_generated', False)
    )
def delete_default(self, activity_id):
    """Delete default activity template"""
    # Simple confirmation dialog
    reply = QMessageBox.question(
        self, 
        'Delete Default Activity', 
        'Are you sure you want to delete this default activity template?',
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    
    if reply == QMessageBox.StandardButton.No:
        return
    
    conn = ServerConnection()
    if conn.connect():
        response = conn.send_request({
            'action': 'delete_default_activity', 
            'activity_id': activity_id,
            'delete_generated': False  # Only delete template, keep generated activities
        })
        conn.close()
        
        if response.get('success'):
            self.load_default_activities()
            QMessageBox.information(self, 'Success', 'Default activity template deleted')
        else:
            QMessageBox.warning(self, 'Error', response.get('error', 'Failed to delete'))




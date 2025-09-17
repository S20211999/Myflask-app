The error occurs because the `add_table_widget` route is missing from your Flask application. The template `footprint.html` is trying to reference this route, but it doesn't exist in your code.

Here's the missing route you need to add to your Flask app:

```python
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
```

Add these routes to your Flask application after the existing routes. The routes handle:

1. **`add_table_widget`** - Allows admins to add new table widgets for the footprint database
2. **`delete_table_widget`** - Allows admins to delete existing table widgets

Also, you might want to add this missing column to your `LicenseServer` model if you're using the `path` field in your server management:

```python
class LicenseServer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    server_type = db.Column(db.String(50), nullable=False)
    command = db.Column(db.Text, nullable=False)
    path = db.Column(db.String(255))  # Add this line if missing
    total_licenses = db.Column(db.Integer, default=0)
    is_enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
```

Additionally, you need to add these missing fields to your `LicenseUsage` model based on your code references:

```python
class LicenseUsage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.Integer, db.ForeignKey('license_server.id'))
    username = db.Column(db.String(80))
    device_name = db.Column(db.String(100))
    version = db.Column(db.String(50))  # Add this
    in_time = db.Column(db.DateTime)
    out_time = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='active')
    
    # Add these properties for compatibility
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
```

After adding these routes and model updates, your footprint page should work correctly without the BuildError.

[1](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/14715858/63fcdbd0-c7de-4c39-96c2-ca2673ca1ab9/paste.txt)

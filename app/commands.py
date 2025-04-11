"""
Custom Flask CLI commands for GeoLLM Enterprise
"""
import click
import getpass
import datetime
from flask import current_app
from flask.cli import with_appcontext
import os
import shutil
import json

from app.extensions import db
from app.auth.models import User, ApiKey, UserProfile
from app.history.models import QueryHistory, GeoSpatialData


@click.command('init-db')
@with_appcontext
def init_db_command():
    """Initialize the database and create tables."""
    try:
        db.create_all()
        click.secho('Database tables created successfully.', fg='green')
    except Exception as e:
        click.secho(f'Error initializing database: {str(e)}', fg='red')
        raise


@click.command('seed-data')
@with_appcontext
def seed_data_command():
    """Seed the database with initial data."""
    try:
        # Check if we already have data
        if User.query.count() > 0:
            if not click.confirm('Database already contains data. Do you want to proceed?'):
                click.echo('Operation cancelled.')
                return
        
        # Create default admin user if it doesn't exist
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@example.com',
                is_admin=True,
                created_at=datetime.datetime.utcnow(),
                is_active=True
            )
            admin.password = 'adminpassword'  # Will be hashed by the model
            db.session.add(admin)
            db.session.commit()
            
            # Create profile for admin
            profile = UserProfile(user_id=admin.id)
            db.session.add(profile)
            db.session.commit()
            
            click.secho('Created default admin user (admin@example.com)', fg='green')
        
        # Create sample data sources
        click.secho('Sample data seeded successfully!', fg='green')
    except Exception as e:
        db.session.rollback()
        click.secho(f'Error seeding database: {str(e)}', fg='red')
        raise


@click.command('create-admin')
@click.option('--username', prompt=True, help='Admin username')
@click.option('--email', prompt=True, help='Admin email')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='Admin password')
@with_appcontext
def create_admin_command(username, email, password):
    """Create a new admin user."""
    try:
        # Check if user exists
        if User.query.filter((User.username == username) | (User.email == email)).first():
            click.secho(f'User with username "{username}" or email "{email}" already exists!', fg='red')
            return
        
        # Create admin user
        admin = User(
            username=username,
            email=email,
            is_admin=True,
            created_at=datetime.datetime.utcnow(),
            is_active=True
        )
        admin.password = password  # Will be hashed by the model
        db.session.add(admin)
        db.session.commit()
        
        # Create profile for admin
        profile = UserProfile(user_id=admin.id)
        db.session.add(profile)
        db.session.commit()
        
        click.secho(f'Admin user "{username}" created successfully!', fg='green')
    except Exception as e:
        db.session.rollback()
        click.secho(f'Error creating admin user: {str(e)}', fg='red')
        raise


@click.command('reset-password')
@click.option('--username', prompt=True, help='Username of account to reset')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='New password')
@with_appcontext
def reset_password_command(username, password):
    """Reset a user's password."""
    try:
        # Find user
        user = User.query.filter_by(username=username).first()
        
        if not user:
            click.secho(f'User "{username}" not found!', fg='red')
            return
        
        # Update password
        user.password = password  # Will be hashed by the model
        db.session.commit()
        
        click.secho(f'Password for user "{username}" updated successfully!', fg='green')
    except Exception as e:
        db.session.rollback()
        click.secho(f'Error resetting password: {str(e)}', fg='red')
        raise


@click.command('create-api-key')
@click.option('--username', prompt=True, help='Username to create API key for')
@click.option('--name', prompt=True, help='Name of the API key')
@click.option('--expires', type=int, default=90, help='Expiration in days (default: 90)')
@with_appcontext
def create_api_key_command(username, name, expires):
    """Create a new API key for a user."""
    try:
        # Find user
        user = User.query.filter_by(username=username).first()
        
        if not user:
            click.secho(f'User "{username}" not found!', fg='red')
            return
        
        # Create API key
        api_key = ApiKey.generate_key(
            user_id=user.id,
            name=name,
            expires_days=expires
        )
        
        click.secho(f'API key created for user "{username}":', fg='green')
        click.secho(f'Name: {api_key.name}', fg='blue')
        click.secho(f'Key: {api_key.key}', fg='blue')
        click.secho(f'Expires: {api_key.expires_at}', fg='blue')
        click.secho('WARNING: This key will not be shown again. Store it securely.', fg='yellow')
    except Exception as e:
        db.session.rollback()
        click.secho(f'Error creating API key: {str(e)}', fg='red')
        raise


@click.command('list-users')
@with_appcontext
def list_users_command():
    """List all registered users."""
    try:
        users = User.query.all()
        
        if not users:
            click.secho('No users found.', fg='yellow')
            return
        
        click.secho(f'Found {len(users)} user(s):', fg='green')
        for user in users:
            admin_status = '[ADMIN]' if user.is_admin else ''
            active_status = '[INACTIVE]' if not user.is_active else ''
            click.secho(f'ID: {user.id}, Username: {user.username}, Email: {user.email} {admin_status} {active_status}')
    except Exception as e:
        click.secho(f'Error listing users: {str(e)}', fg='red')
        raise


@click.command('backup-db')
@click.option('--output', default='./backups', help='Output directory for backup file')
@with_appcontext
def backup_db_command(output):
    """Backup the database."""
    try:
        # Ensure output directory exists
        os.makedirs(output, exist_ok=True)
        
        # Create timestamp for filename
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'geollm_backup_{timestamp}.sql'
        filepath = os.path.join(output, filename)
        
        # Get database URI from config
        db_uri = current_app.config['SQLALCHEMY_DATABASE_URI']
        
        if 'postgresql' in db_uri:
            # PostgreSQL backup
            from urllib.parse import urlparse
            
            # Parse the database URI
            parsed_uri = urlparse(db_uri)
            username = parsed_uri.username
            password = parsed_uri.password
            database = parsed_uri.path[1:]  # Remove leading slash
            hostname = parsed_uri.hostname
            port = parsed_uri.port or 5432
            
            # Build the pg_dump command
            command = f'PGPASSWORD={password} pg_dump -h {hostname} -p {port} -U {username} -d {database} -f {filepath}'
            
            # Execute the command
            result = os.system(command)
            
            if result == 0:
                click.secho(f'Database backup created successfully: {filepath}', fg='green')
            else:
                click.secho(f'Error creating database backup (code: {result})', fg='red')
        elif 'sqlite' in db_uri:
            # SQLite backup - just copy the file
            sqlite_path = db_uri.replace('sqlite:///', '')
            shutil.copy2(sqlite_path, filepath)
            click.secho(f'SQLite database backup created successfully: {filepath}', fg='green')
        else:
            click.secho(f'Unsupported database type for backup: {db_uri}', fg='red')
    except Exception as e:
        click.secho(f'Error backing up database: {str(e)}', fg='red')
        raise


@click.command('clean-history')
@click.option('--days', default=30, help='Delete history older than this many days')
@click.option('--dry-run', is_flag=True, help='Only show what would be deleted without actually deleting')
@click.option('--user', help='Limit to a specific username')
@with_appcontext
def clean_history_command(days, dry_run, user):
    """Clean up old query history."""
    try:
        # Calculate cutoff date
        cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=days)
        
        # Build query
        query = QueryHistory.query.filter(QueryHistory.created_at < cutoff_date)
        
        # Filter by user if specified
        if user:
            user_obj = User.query.filter_by(username=user).first()
            if not user_obj:
                click.secho(f'User "{user}" not found!', fg='red')
                return
            query = query.filter_by(user_id=user_obj.id)
        
        # Count queries to be deleted
        count = query.count()
        
        if count == 0:
            click.secho('No queries found matching the criteria.', fg='yellow')
            return
        
        # Show what will be deleted
        click.secho(f'Will delete {count} queries older than {days} days ({cutoff_date.isoformat()}).', fg='yellow')
        
        if dry_run:
            click.secho('Dry run - no queries were deleted.', fg='blue')
            return
            
        # Confirm deletion
        if not click.confirm('Do you want to proceed with deletion?'):
            click.echo('Operation cancelled.')
            return
        
        # Delete queries
        deleted_count = query.delete()
        db.session.commit()
        
        click.secho(f'Successfully deleted {deleted_count} queries.', fg='green')
    except Exception as e:
        db.session.rollback()
        click.secho(f'Error cleaning history: {str(e)}', fg='red')
        raise


@click.command('export-queries')
@click.option('--user', help='Export only queries from this username')
@click.option('--output', default='./exports', help='Output directory for export file')
@click.option('--format', type=click.Choice(['json', 'csv']), default='json', help='Export format')
@with_appcontext
def export_queries_command(user, output, format):
    """Export query history to a file."""
    try:
        # Ensure output directory exists
        os.makedirs(output, exist_ok=True)
        
        # Create timestamp for filename
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Build query
        query = QueryHistory.query
        
        # Filter by user if specified
        if user:
            user_obj = User.query.filter_by(username=user).first()
            if not user_obj:
                click.secho(f'User "{user}" not found!', fg='red')
                return
            query = query.filter_by(user_id=user_obj.id)
            filename = f'queries_{user}_{timestamp}.{format}'
        else:
            filename = f'queries_all_{timestamp}.{format}'
        
        filepath = os.path.join(output, filename)
        
        # Fetch queries
        queries = query.all()
        
        if not queries:
            click.secho('No queries found.', fg='yellow')
            return
        
        if format == 'json':
            # Export as JSON
            data = [q.to_dict() for q in queries]
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        elif format == 'csv':
            # Export as CSV
            import csv
            with open(filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                
                # Write header
                writer.writerow(['id', 'user_id', 'prompt', 'created_at', 'duration_ms', 'is_favorited'])
                
                # Write data
                for q in queries:
                    writer.writerow([
                        q.id,
                        q.user_id,
                        q.prompt,
                        q.created_at.isoformat(),
                        q.duration_ms,
                        q.is_favorited
                    ])
        
        click.secho(f'Successfully exported {len(queries)} queries to {filepath}', fg='green')
    except Exception as e:
        click.secho(f'Error exporting queries: {str(e)}', fg='red')
        raise


@click.command('check-system')
@with_appcontext
def check_system_command():
    """Check the system status and components."""
    click.secho('Performing system check...', fg='blue')
    
    errors = []
    warnings = []
    
    # Check database connection
    click.echo('Checking database connection... ', nl=False)
    try:
        # Try a simple query
        db.session.execute('SELECT 1').fetchall()
        click.secho('OK', fg='green')
    except Exception as e:
        errors.append(f'Database error: {str(e)}')
        click.secho('FAILED', fg='red')
    
    # Check API keys
    click.echo('Checking for expired API keys... ', nl=False)
    try:
        expired_count = ApiKey.query.filter(
            ApiKey.expires_at < datetime.datetime.utcnow(),
            ApiKey.is_active == True
        ).count()
        
        if expired_count > 0:
            warnings.append(f'Found {expired_count} expired but still active API keys')
            click.secho(f'WARNING ({expired_count} expired keys)', fg='yellow')
        else:
            click.secho('OK', fg='green')
    except Exception as e:
        warnings.append(f'Could not check API keys: {str(e)}')
        click.secho('ERROR', fg='red')
    
    # Check for required environment variables
    click.echo('Checking environment variables... ', nl=False)
    missing_vars = []
    for var in ['SECRET_KEY', 'OPENAI_API_KEY']:
        if not current_app.config.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        warnings.append(f'Missing environment variables: {", ".join(missing_vars)}')
        click.secho(f'WARNING (missing: {", ".join(missing_vars)})', fg='yellow')
    else:
        click.secho('OK', fg='green')
    
    # Check disk space
    click.echo('Checking disk space... ', nl=False)
    try:
        import shutil
        total, used, free = shutil.disk_usage('/')
        
        # Convert to GB
        free_gb = free / (1024 ** 3)
        total_gb = total / (1024 ** 3)
        used_percent = (used / total) * 100
        
        if free_gb < 1:
            errors.append(f'Low disk space: {free_gb:.2f} GB free ({used_percent:.1f}% used)')
            click.secho(f'CRITICAL ({free_gb:.2f} GB free)', fg='red')
        elif free_gb < 5:
            warnings.append(f'Low disk space: {free_gb:.2f} GB free ({used_percent:.1f}% used)')
            click.secho(f'WARNING ({free_gb:.2f} GB free)', fg='yellow')
        else:
            click.secho(f'OK ({free_gb:.2f} GB free)', fg='green')
    except Exception as e:
        warnings.append(f'Could not check disk space: {str(e)}')
        click.secho('ERROR', fg='red')
    
    # Summary
    click.echo('\nSystem Check Summary:')
    if not errors and not warnings:
        click.secho('All systems operational!', fg='green')
    
    if warnings:
        click.secho(f'{len(warnings)} warning(s):', fg='yellow')
        for i, warning in enumerate(warnings, 1):
            click.secho(f'  {i}. {warning}', fg='yellow')
    
    if errors:
        click.secho(f'{len(errors)} error(s):', fg='red')
        for i, error in enumerate(errors, 1):
            click.secho(f'  {i}. {error}', fg='red')


@click.command('generate-shell-completion')
@click.option('--shell', type=click.Choice(['bash', 'zsh', 'fish']), default='bash', help='Shell type')
@click.option('--output', help='Output file (defaults to stdout)')
def generate_shell_completion_command(shell, output):
    """Generate shell completion script."""
    import subprocess
    
    if shell == 'bash':
        command = 'flask --completion bash'
    elif shell == 'zsh':
        command = 'flask --completion zsh'
    elif shell == 'fish':
        command = 'flask --completion fish'
    
    if output:
        with open(output, 'w') as f:
            subprocess.run(command, shell=True, stdout=f)
        click.secho(f'Completion script for {shell} written to {output}', fg='green')
    else:
        result = subprocess.run(command, shell=True)
        if result.returncode != 0:
            click.secho(f'Error generating completion script for {shell}', fg='red')

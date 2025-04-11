"""
Application factory pattern
"""
import os
from flask import Flask, render_template, request, jsonify
from flask_migrate import Migrate
from app.extensions import db, login_manager, jwt, cache, limiter, mail, assets
from app.celery_app import create_celery_app
from app.config import config

# Import blueprints
from app.main.routes import main_bp
from app.auth.routes import auth_bp
from app.api.routes import api_bp
from app.history.routes import history_bp


def create_app(config_name='default'):
    """
    Create and configure the Flask application
    
    Args:
        config_name: Configuration name (default, development, testing, production)
        
    Returns:
        Configured Flask application
    """
    import os
    import logging
    from flask import Flask
    
    from app.config import config
    from app.extensions import (
        db, migrate, bcrypt, login_manager, 
        jwt, mail, cache, limiter, cors
    )
    
    # Create app
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Configure logging
    if app.config['LOG_TO_STDOUT']:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        app.logger.addHandler(stream_handler)
        app.logger.setLevel(logging.INFO)
    else:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = logging.FileHandler('logs/geollm.log')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
    
    app.logger.info('GeoLLM startup')
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    cache.init_app(app)
    limiter.init_app(app)
    cors.init_app(app)
    
    # Initialize Earth Engine in a background thread to not block startup
    with app.app_context():
        init_earth_engine_async(app)
    
    # Register blueprints
    from app.auth.routes import auth_bp
    from app.main.routes import main_bp
    from app.api.routes import api_bp
    from app.history.routes import history_bp
    from app.geo.routes import geo_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(geo_bp)
    
    # Register the agent blueprint if it exists
    try:
        from app.routes.agent_api import agent_api
        app.register_blueprint(agent_api)
        app.logger.info("Agent API blueprint registered successfully")
    except ImportError:
        app.logger.warning("Agent API blueprint not found - agent architecture not available")
    
    return app


def init_earth_engine_async(app):
    """Initialize Earth Engine in a background thread"""
    import threading
    
    def _init_earth_engine():
        try:
            from app.geo.data_sources import get_data_source_manager
            # This will initialize Earth Engine when the data source manager is created
            data_source_manager = get_data_source_manager()
            app.logger.info("Earth Engine initialized successfully in background thread")
        except Exception as e:
            app.logger.error(f"Failed to initialize Earth Engine in background thread: {str(e)}")
    
    # Start the initialization in a separate thread
    thread = threading.Thread(target=_init_earth_engine)
    thread.daemon = True
    thread.start()


def register_error_handlers(app):
    """Register error handlers for the application"""
    from flask import render_template, jsonify
    
    # Handle 404 errors
    @app.errorhandler(404)
    def page_not_found(e):
        if request.path.startswith('/api/'):
            return jsonify(error=str(e)), 404
        return render_template('errors/404.html'), 404
    
    # Handle 500 errors
    @app.errorhandler(500)
    def internal_server_error(e):
        if request.path.startswith('/api/'):
            return jsonify(error=str(e)), 500
        return render_template('errors/500.html'), 500
    
    # Handle 403 errors
    @app.errorhandler(403)
    def forbidden(e):
        if request.path.startswith('/api/'):
            return jsonify(error=str(e)), 403
        return render_template('errors/403.html'), 403
    
def initialize_extensions(app):
    """Initialize Flask extensions"""
    db.init_app(app)
    Migrate(app, db)
    
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    
    jwt.init_app(app)
    
    # Set up cache with Redis if available
    cache_config = app.config.get('CACHE_CONFIG', {'CACHE_TYPE': 'SimpleCache'})
    cache.init_app(app, config=cache_config)
    
    # Configure limiter with Redis if available
    redis_url = app.config.get('REDIS_URL')
    if redis_url:
        limiter.storage_uri = redis_url
    limiter.init_app(app)
    
    mail.init_app(app)
    assets.init_app(app)
    
    # Register asset bundles if the module exists
    try:
        from app.assets import register_asset_bundles
        register_asset_bundles(assets)
    except ImportError:
        app.logger.warning("Asset bundling is disabled (app.assets module not found)")


def register_blueprints(app):
    """Register Flask blueprints"""
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(history_bp, url_prefix='/history')


def register_error_handlers(app):
    """Register error handlers"""
    
    @app.errorhandler(400)
    def bad_request(error):
        return render_template('errors/400.html'), 400

    @app.errorhandler(403)
    def forbidden(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        return render_template('errors/500.html'), 500


def register_commands(app):
    """Register Flask CLI commands"""
    from app.commands import init_db_command, seed_data_command
    
    app.cli.add_command(init_db_command)
    app.cli.add_command(seed_data_command)


def configure_logging(app):
    """Configure application logging"""
    import logging
    from logging.handlers import RotatingFileHandler
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration
    
    if not app.debug and not app.testing:
        if app.config.get('SENTRY_DSN'):
            sentry_sdk.init(
                dsn=app.config['SENTRY_DSN'],
                integrations=[FlaskIntegration()],
                traces_sample_rate=app.config.get('SENTRY_TRACES_SAMPLE_RATE', 0.1),
                environment=app.config.get('ENVIRONMENT', 'production'),
            )
        
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.mkdir('logs')
            
        # Configure file handler
        file_handler = RotatingFileHandler(
            'logs/geollm.log', maxBytes=10485760, backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        
        # Add handlers to Flask app and basic logger
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('GeoLLM startup')


def register_context_processors(app):
    """Register context processors with the app"""
    
    @app.context_processor
    def inject_global_variables():
        """Inject global variables into all templates"""
        from datetime import datetime
        from flask import current_app
        
        return {
            'current_year': datetime.now().year,
            'current_app': current_app
        }
    

def check_earth_engine_config():
    """Verify that Earth Engine is properly configured"""
    from flask import current_app
    import os
    
    # Check for Earth Engine service account key
    gee_key = current_app.config.get('GEE_SERVICE_ACCOUNT_KEY')
    if not gee_key:
        current_app.logger.error("GEE_SERVICE_ACCOUNT_KEY not configured in app settings")
        return False
    
    # Check if the key file exists
    if not os.path.exists(gee_key):
        current_app.logger.error(f"Earth Engine service account key file not found: {gee_key}")
        return False
    
    # Try to initialize Earth Engine
    try:
        from app.geo.earth_engine_source import EarthEngineDataSource
        ee_source = EarthEngineDataSource(gee_key)
        # Test the initialization
        if not ee_source.initialized:
            current_app.logger.error("Earth Engine initialization failed")
            return False
        
        current_app.logger.info("Earth Engine successfully initialized")
        return True
    except Exception as e:
        current_app.logger.error(f"Earth Engine initialization error: {str(e)}")
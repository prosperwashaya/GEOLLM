"""
Celery application factory for task processing
"""
from celery import Celery
from celery.schedules import crontab


def create_celery_app(app=None):
    """
    Create a Celery application instance
    
    Args:
        app: Flask application instance
        
    Returns:
        Celery application instance
    """
    
    # Create Celery app
    celery_app = Celery(
        app.import_name if app else 'geollm',
        broker=app.config['CELERY_BROKER_URL'] if app else None,
        backend=app.config['CELERY_RESULT_BACKEND'] if app else None,
        include=[
            'app.auth.tasks',
            'app.geo.tasks',
            'app.llm.tasks'
        ]
    )
    
    # Configure from Flask app
    if app:
        # Update Celery configuration from Flask config
        celery_app.conf.update(app.config)
        
        # Configure periodic tasks
        celery_app.conf.beat_schedule = {
            'cleanup-expired-tokens': {
                'task': 'app.auth.tasks.cleanup_expired_tokens',
                'schedule': crontab(hour=0, minute=0)  # run daily at midnight
            },
            'update-geo-data-cache': {
                'task': 'app.geo.tasks.update_geo_data_cache',
                'schedule': crontab(hour='*/6')  # run every 6 hours
            },
            'clear-old-sessions': {
                'task': 'app.auth.tasks.clear_old_sessions',
                'schedule': crontab(hour=2, minute=0)  # run daily at 2am
            }
        }
        
        # Configure task routes for different queues
        celery_app.conf.task_routes = {
            'app.geo.tasks.*': {'queue': 'geo'},
            'app.llm.tasks.*': {'queue': 'llm'},
            'app.auth.tasks.*': {'queue': 'auth'}
        }
        
        class ContextTask(celery_app.Task):
            """Make Celery tasks work with Flask app context"""
            
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)
                    
        celery_app.Task = ContextTask
    
    return celery_app


# If this module is executed directly
if __name__ == '__main__':
    # Create standalone Celery app for worker processes
    app = create_celery_app()

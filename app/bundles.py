"""
Asset bundle registration for Flask-Assets
"""
from flask_assets import Bundle


def register_asset_bundles(assets):
    """
    Register asset bundles with Flask-Assets
    
    Args:
        assets: Flask-Assets Environment instance
    """
    # CSS bundles
    css_base = Bundle(
        'css/style.css',
        filters='cssmin',
        output='dist/css/base.min.css'
    )
    
    css_admin = Bundle(
        'css/admin.css',
        filters='cssmin',
        output='dist/css/admin.min.css'
    )
    
    # JavaScript bundles
    js_base = Bundle(
        'js/main.js',
        filters='jsmin',
        output='dist/js/base.min.js'
    )
    
    js_map = Bundle(
        'js/map.js',
        filters='jsmin',
        output='dist/js/map.min.js'
    )
    
    js_admin = Bundle(
        'js/admin.js',
        filters='jsmin',
        output='dist/js/admin.min.js'
    )
    
    # Register bundles
    assets.register('css_base', css_base)
    assets.register('css_admin', css_admin)
    assets.register('js_base', js_base)
    assets.register('js_map', js_map)
    assets.register('js_admin', js_admin)
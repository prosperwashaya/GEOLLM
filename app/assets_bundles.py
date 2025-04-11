"""
Asset bundle management for Flask-Assets
"""
from flask_assets import Bundle


def register_asset_bundles(assets):
    """
    Register asset bundles for CSS and JavaScript files
    
    Args:
        assets: Flask-Assets environment
    """
    # CSS bundles
    css_all = Bundle(
        'css/style.css',
        filters='cssmin',
        output='dist/css/all.min.css'
    )
    
    # JavaScript bundles
    js_main = Bundle(
        'js/main.js',
        filters='jsmin',
        output='dist/js/main.min.js'
    )
    
    js_map = Bundle(
        'js/map.js',
        filters='jsmin',
        output='dist/js/map.min.js'
    )
    
    # Register bundles
    assets.register('css_all', css_all)
    assets.register('js_main', js_main)
    assets.register('js_map', js_map)

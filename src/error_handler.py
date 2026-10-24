import logging
from logging.handlers import RotatingFileHandler
import os
import sys
from flask import jsonify

def setup_logging(app):
    """Configure application logging for production"""
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # File handler - 10MB limit per file, keep 10 backups
    file_handler = RotatingFileHandler(
        'logs/stock_sense.log',
        maxBytes=10485760, 
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.INFO)
    
    app.logger.info('Stock Sense Production Logging Initialized')

def register_error_handlers(app):
    """Register global API error handlers"""
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'status': 'error',
            'error': 'Bad Request',
            'message': str(error)
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            'status': 'error',
            'error': 'Unauthorized',
            'message': 'Authentication failed'
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            'status': 'error',
            'error': 'Forbidden',
            'message': 'Perspective denied'
        }), 403
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'status': 'error',
            'error': 'Not Found',
            'message': 'Intelligence resource not located'
        }), 404
        
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({
            "status": "error",
            "error": "Too Many Requests",
            "message": "Rate limit exceeded. Slow down your intelligence requests."
        }), 429
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'Server Error: {error}', exc_info=True)
        return jsonify({
            'status': 'error',
            'error': 'Internal Server Error',
            'message': 'An unexpected intelligence collapse occurred'
        }), 500

import logging
from logging.handlers import RotatingFileHandler
import os
import sys
from pathlib import Path
from flask import jsonify

from config import Config

def setup_logging(app):
    """Configure application logging for production"""
    log_dir = Path(Config.BASE_DIR) / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / 'stock_sense.log'
    
    # File handler - 10MB limit per file, keep 10 backups
    file_handler = RotatingFileHandler(
        str(log_file),
        maxBytes=10485760, 
        backupCount=10,
        encoding='utf-8'
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
        msg = getattr(error, 'description', 'Bad Request')
        return jsonify({
            'status': 'error',
            'error': 'Bad Request',
            'message': str(msg)
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            'status': 'error',
            'error': 'Unauthorized',
            'message': 'Authentication failed or missing credentials.'
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            'status': 'error',
            'error': 'Forbidden',
            'message': 'Access denied.'
        }), 403
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'status': 'error',
            'error': 'Not Found',
            'message': 'Requested resource not found.'
        }), 404
        
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({
            "status": "error",
            "error": "Too Many Requests",
            "message": "Rate limit exceeded. Please wait before submitting more requests."
        }), 429
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'Server Error: {error}', exc_info=True)
        return jsonify({
            'status': 'error',
            'error': 'Internal Server Error',
            'message': 'An unexpected internal server error occurred.'
        }), 500

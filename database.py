from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
import os

db = SQLAlchemy()
migrate = Migrate()

def init_db(app):
    db.init_app(app)
    migrate.init_app(app, db)
    
    with app.app_context():
        db.create_all()
        
        # Create default admin user if not exists
        from models import Admin
        admin = Admin.query.filter_by(username='admin').first()
        if not admin:
            from werkzeug.security import generate_password_hash
            admin = Admin(
                username='admin',
                password_hash=generate_password_hash('admin123'),
                email='admin@company.com'
            )
            db.session.add(admin)
            db.session.commit()
            print("Default admin user created: username=admin, password=admin123")

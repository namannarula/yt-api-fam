from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
db = SQLAlchemy(app)

from app.models import video_model  # Import the Video model

from app.routes import video_routes  # Import the Blueprint from the video_routes module
app.register_blueprint(video_routes.bp, url_prefix='/api')

from app.scheduler import fetch_scheduler  # Import the start_scheduler function
fetch_scheduler.start_scheduler(app)
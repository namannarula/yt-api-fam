from googleapiclient.discovery import build
import os
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from googleapiclient.errors import HttpError


load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///videos.db'
db = SQLAlchemy(app)

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    youtube_id = db.Column(db.String(100), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    publish_datetime = db.Column(db.DateTime, nullable=False)
    thumbnail_default = db.Column(db.String(200), nullable=False)
    def __repr__(self):
        return f'<Video {self.title}>'

with app.app_context():
    db.create_all()

api_keys = [os.getenv("yt_api_key_1"), os.getenv("yt_api_key_2"), os.getenv("yt_api_key_3")]
api_keys = [key for key in api_keys if key]

search_query = 'macbook pro m3 review'

def fetch_latest_videos(app):
    global current_key_index

    with app.app_context():
        try:
            youtube = build('youtube', 'v3', developerKey=api_keys[current_key_index])
            request = youtube.search().list(
                part='snippet',
                maxResults=50,
                order='date',
                type='video',
                q=search_query
            )
            response = request.execute()

            for search_result in response.get('items', []):
                if search_result['id']['kind'] == 'youtube#video':
                    video_id = search_result['id']['videoId']
                    existing_video = Video.query.filter_by(youtube_id=video_id).first()
                    if existing_video is None:
                        video = Video(
                            youtube_id=video_id,
                            title=search_result['snippet']['title'],
                            description=search_result['snippet']['description'],
                            publish_datetime=datetime.datetime.strptime(search_result['snippet']['publishedAt'], '%Y-%m-%dT%H:%M:%SZ'),
                            thumbnail_default=search_result['snippet']['thumbnails']['default']['url']
                        )
                        db.session.add(video)

            db.session.commit()

        except HttpError as e:
            print(f'An HTTP error occurred: {e}')

            current_key_index = (current_key_index + 1) % len(api_keys)
            print(f'Switched to API key: {api_keys[current_key_index]}')

            fetch_latest_videos(app)

def start_scheduler(app):
    global current_key_index
    current_key_index = 0
    scheduler = BackgroundScheduler()
    scheduler.add_job(fetch_latest_videos, 'interval', minutes=1, args=[app])
    scheduler.start()

@app.route('/videos', methods=['GET'])
def get_videos():
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))

    videos = Video.query.order_by(Video.publish_datetime.desc()).paginate(page=page, per_page=per_page)

    video_list = []
    for video in videos.items:
        video_data = {
            'title': video.title,
            'description': video.description,
            'publish_datetime': video.publish_datetime.isoformat(),
            'thumbnails': {
                'default': video.thumbnail_default
            }
        }
        video_list.append(video_data)

    response = {
        'videos': video_list,
        'total_pages': videos.pages,
        'current_page': page
    }

    return jsonify(response)

@app.route('/search', methods=['GET'])
def search_videos():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'error': 'Search query is required.'}), 400

    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))

    videos = Video.query.filter(
        db.or_(
            Video.title.ilike(f'%{query}%'),
            Video.description.ilike(f'%{query}%')
        )
    ).order_by(Video.publish_datetime.desc()).paginate(page=page, per_page=per_page)

    video_list = []
    for video in videos.items:
        video_data = {
            'title': video.title,
            'description': video.description,
            'publish_datetime': video.publish_datetime.isoformat(),
            'thumbnails': {
                'default': video.thumbnail_default
            }
        }
        video_list.append(video_data)

    response = {
        'videos': video_list,
        'total_pages': videos.pages,
        'current_page': page
    }

    return jsonify(response)

if __name__ == '__main__':
    with app.app_context():
        start_scheduler(app)

    app.run(debug=True, port=5001)
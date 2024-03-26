from googleapiclient.discovery import build
import os
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from googleapiclient.errors import HttpError
import time
from flask_caching import Cache
import redis

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:password@postgres:5432/database_name'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_QUERY_CACHE_OPTIONS'] = {'timeout': 300}
redis_client = redis.Redis(host='redis', port=6379, db=0)
db = SQLAlchemy(app)
cache = Cache(app, config={
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_HOST': 'redis',
    'CACHE_REDIS_PORT': 6379,
    'CACHE_REDIS_DB': 0,
    'CACHE_DEFAULT_TIMEOUT': 300
})


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


class APIKeyManager:
    def __init__(self, api_keys, cooldown_period=6 * 60 * 60):
        self.api_keys = api_keys
        self.cooldown_period = cooldown_period
        self.disabled_keys = {}
    def get_next_key(self):
        available_keys = [key for key in self.api_keys if key not in self.disabled_keys or self.disabled_keys[key] < time.time()]
        if not available_keys:
            raise Exception("No API keys available")
        return available_keys[0]

    def disable_key(self, key):
        self.disabled_keys[key] = time.time() + self.cooldown_period

search_query = 'macbook pro m3 review'

@cache.memoize(timeout=300)
def fetch_latest_videos(app, api_key_manager):
    with app.app_context():
        try:
            key = api_key_manager.get_next_key()
            youtube = build('youtube', 'v3', developerKey=key)
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
            api_key_manager.disable_key(key)
            key = api_key_manager.get_next_key()
            youtube = build('youtube', 'v3', developerKey=key)


api_key_manager = APIKeyManager(api_keys)
def start_scheduler(app):
    global api_key_manager
    scheduler = BackgroundScheduler()

    scheduler.add_job(fetch_latest_videos, 'interval', minutes=1, args=[app, api_key_manager])
    scheduler.start()

@app.route('/videos', methods=['GET'])
def get_videos():
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    videos = Video.query.options(cache.cache_key('all_videos'),
                                 cache.cache_timeout(3600)).order_by(Video.publish_datetime.desc()).paginate(page=page, per_page=per_page)
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

    query_words = query.split()
    search_conditions = []
    for word in query_words:
        word_condition = db.or_(
            Video.title.ilike(f'%{word}%'),
            Video.description.ilike(f'%{word}%')
        )
        search_conditions.append(word_condition)

    videos = Video.query.filter(
        db.and_(*search_conditions)
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
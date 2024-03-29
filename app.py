from googleapiclient.discovery import build
import os
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from googleapiclient.errors import HttpError
import time
import redis
from sqlalchemy import Column, Integer, String, Text, DateTime
import json

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
db = SQLAlchemy(app)

redis_client = redis.Redis(host='redis', port=6379, db=0)

class Video(db.Model):
    id = Column(Integer, primary_key=True)
    youtube_id = Column(String(100), unique=True, nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    publish_datetime = Column(DateTime, nullable=False)
    thumbnail_default = Column(String(200), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)

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
                publishedAfter='2023-01-01T00:00:00Z',
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

            cache_keys_to_delete = [f'latest_videos:{search_query}:{page}' for page in range(1, Video.query.order_by(Video.publish_datetime.desc()).paginate().pages + 1)]
            redis_client.delete(*cache_keys_to_delete)

        except HttpError as e:
            print(f'An HTTP error occurred: {e}')
            api_key_manager.disable_key(key)
            key = api_key_manager.get_next_key()
            youtube = build('youtube', 'v3', developerKey=key)

api_key_manager = APIKeyManager(api_keys)
def start_scheduler(app):
    global api_key_manager
    scheduler = BackgroundScheduler()

    scheduler.add_job(fetch_latest_videos, 'interval', seconds=60, args=[app, api_key_manager])
    scheduler.start()

@app.route('/videos', methods=['GET'])
def get_videos():
    cursor = request.args.get('cursor', None)
    per_page = int(request.args.get('per_page', 10))
    cache_key = f'latest_videos:{search_query}:{cursor or ""}'

    if redis_client.get(cache_key) is None:
        query = Video.query.order_by(Video.created_at.desc())

        if cursor:
            last_video = Video.query.filter_by(id=cursor).first()
            if last_video:
                query = query.filter(Video.created_at < last_video.created_at)

        videos = query.limit(per_page + 1).all()

        has_next_page = len(videos) > per_page
        video_list = [
            {
                'id': video.id,
                'title': video.title,
                'description': video.description,
                'publish_datetime': video.publish_datetime.isoformat(),
                'thumbnails': {
                    'default': video.thumbnail_default
                }
            }
            for video in videos[:per_page]
        ]

        next_cursor = videos[-1].id if has_next_page else None

        response = {
            'videos': video_list,
            'next_cursor': next_cursor
        }

        redis_client.set(cache_key, json.dumps(response), ex=60)

        return jsonify(response)

    cached_response = redis_client.get(cache_key)
    if cached_response:
        cached_response = json.loads(cached_response)
        return jsonify(cached_response)
@app.route('/search', methods=['GET'])
def search_videos():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'error': 'Search query is required.'}), 400

    cursor = request.args.get('cursor', None)
    per_page = int(request.args.get('per_page', 10))

    query_words = query.split()
    search_conditions = []
    for word in query_words:
        word_condition = db.or_(
            Video.title.ilike(f'%{word}%'),
            Video.description.ilike(f'%{word}%')
        )
        search_conditions.append(word_condition)

    query = Video.query.filter(
        db.and_(*search_conditions)
    ).order_by(Video.publish_datetime.desc())

    if cursor:
        last_video = Video.query.filter_by(id=cursor).first()
        if last_video:
            query = query.filter(Video.publish_datetime < last_video.publish_datetime)

    videos = query.limit(per_page + 1).all()

    has_next_page = len(videos) > per_page
    video_list = [
        {
            'id': video.id,
            'title': video.title,
            'description': video.description,
            'publish_datetime': video.publish_datetime.isoformat(),
            'thumbnails': {
                'default': video.thumbnail_default
            }
        }
        for video in videos[:per_page]
    ]

    next_cursor = videos[-1].id if has_next_page else None

    response = {
        'videos': video_list,
        'next_cursor': next_cursor
    }

    return jsonify(response)

if __name__ == 'app':
    with app.app_context():
        start_scheduler(app)
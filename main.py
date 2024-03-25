from googleapiclient.discovery import build
import os
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
import datetime

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///videos.db'
db = SQLAlchemy(app)

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    publish_datetime = db.Column(db.DateTime, nullable=False)
    thumbnail_default = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return f'<Video {self.title}>'

with app.app_context():
    db.create_all()

yt_api_key = os.getenv("yt_api_key_1")

search_query = 'macbook pro m3 review'

youtube = build('youtube', 'v3', developerKey=yt_api_key)

def fetch_latest_videos():
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
            video = Video(
                title=search_result['snippet']['title'],
                description=search_result['snippet']['description'],
                publish_datetime=datetime.datetime.strptime(search_result['snippet']['publishedAt'], '%Y-%m-%dT%H:%M:%SZ'),
                thumbnail_default=search_result['snippet']['thumbnails']['default']['url'],
            )
            db.session.add(video)

    db.session.commit()

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
        fetch_latest_videos()

    app.run(debug=True, port=5001)
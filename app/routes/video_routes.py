from flask import Blueprint, jsonify, request
from app.models.video_model import Video
from app import db, redis_client
import redis
import json

bp = Blueprint('video_routes', __name__)

search_query = 'macbook pro m3 review'

@bp.route('/videos', methods=['GET'])
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

@bp.route('/search', methods=['GET'])
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
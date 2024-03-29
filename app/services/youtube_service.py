from googleapiclient.discovery import build
from app.models.video_model import Video
from app import db, redis_client
import datetime
from googleapiclient.errors import HttpError


def fetch_latest_videos(app, api_key_manager, search_query):
    with app.app_context():
        print("Fetching videos from YT")
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
            redis_client.delete(f'latest_videos:{search_query}')

        except HttpError as e:
            print(f'An HTTP error occurred: {e}')
            api_key_manager.disable_key(key)
            key = api_key_manager.get_next_key()
            youtube = build('youtube', 'v3', developerKey=key)
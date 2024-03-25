from googleapiclient.discovery import build
import os
from dotenv import load_dotenv

load_dotenv()

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

    videos = []
    for search_result in response.get('items', []):
        if search_result['id']['kind'] == 'youtube#video':
            video = {
                'title': search_result['snippet']['title'],
                'description': search_result['snippet']['description'],
                'publish_datetime': search_result['snippet']['publishedAt'],
                'thumbnails': search_result['snippet']['thumbnails']
            }
            videos.append(video)

    return videos

latest_videos = fetch_latest_videos()
print(latest_videos)

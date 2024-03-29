from app.services.youtube_service import fetch_latest_videos
from app.services.api_key_manager import APIKeyManager
import os
from apscheduler.schedulers.background import BackgroundScheduler

api_keys = [os.getenv("yt_api_key_1"), os.getenv("yt_api_key_2"), os.getenv("yt_api_key_3")]
api_keys = [key for key in api_keys if key]
api_key_manager = APIKeyManager(api_keys)
search_query = 'macbook pro m3 review'

def start_scheduler(app):
    print("scheduler ran")
    global api_key_manager
    scheduler = BackgroundScheduler()
    scheduler.add_job(fetch_latest_videos, 'interval', seconds=10, args=[app, api_key_manager, search_query])
    scheduler.start()


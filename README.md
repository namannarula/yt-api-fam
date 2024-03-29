# YouTube Video Fetcher

## Features

- Continuous background fetching of latest videos from YouTube based on a predefined search query
- Storing video metadata (title, description, publish datetime, thumbnails) in a PostgreSQL database
- Paginated GET API to retrieve the latest videos sorted by publish datetime
- Search API to search for videos based on title and description
- Scalability with support for multiple API keys and distributed caching
- Docker containerization for easy deployment

## Prerequisites
- Docker

## Installation

1. Clone the repository:
    1. git clone https://github.com/namannarula/yt-api-fam.git
    2. cd yt-api-fam
2. Create a `.env` file in the project root directory with your YouTube API keys: (adding .env.example for reference)
```
yt_api_key_1=YOUR_API_KEY_1 
yt_api_key_2=YOUR_API_KEY_2 
yt_api_key_3=YOUR_API_KEY_3
```
3. Build and run the Docker containers:
   `docker-compose up --build`

The application will be accessible at `http://localhost:5001`.

## API Usage

### GET /api/videos
Retrieves the latest videos in a paginated format.

**Parameters:**
- `cursor` (optional): The ID of the last video from the previous page. Used for pagination.
- `per_page` (optional, default: 10): The number of videos to return per page.

**Example:**
GET /api/videos?per_page=20&cursor=42

### GET /api/search
Searches for videos based on the title and description.

**Parameters:**
- `q`: The search query.
- `cursor` (optional): The ID of the last video from the previous page. Used for pagination.
- `per_page` (optional, default: 10): The number of videos to return per page.

**Example:**
GET /api/search?q=macbook+unboxing&per_page=15

## Known Issues
- Load balancing needs to be added / horizontal scalability needs to be added.
- Once the application has run, it will take 10 seconds to fetch the first result via the API
- No caching on /search
- 
import requests
import json
from PIL import Image
from io import BytesIO
import time
import subprocess

# Load configuration from file
config_file_path = 'config.json'

with open(config_file_path) as config_file:
    config = json.load(config_file)

client_id = config['client_id']
tmdb_api_key = config['tmdb_api_key']
trakt_username = config['trakt_username']  # Get Trakt username from config

headers = {
    'Content-Type': 'application/json',
    'trakt-api-key': client_id,
    'trakt-api-version': '2',
}

previous_poster_url = None  # To store the current poster URL
temp_image_path = '/tmp/current_poster.png'

def fetch_currently_watching():
    watching_url = f'https://api.trakt.tv/users/{trakt_username}/watching'
    try:
        response = requests.get(watching_url, headers=headers)
        response.raise_for_status()
        return response.json() if response.status_code == 200 else None
    except requests.RequestException:
        return None

def fetch_poster_from_tmdb(tmdb_id, is_movie=True, season_number=None):
    base_url = 'https://api.themoviedb.org/3'
    endpoint = f"/{'movie' if is_movie else 'tv'}/{tmdb_id}"
    if not is_movie and season_number:
        endpoint += f"/season/{season_number}"
    tmdb_url = f"{base_url}{endpoint}?api_key={tmdb_api_key}"
    try:
        response = requests.get(tmdb_url)
        response.raise_for_status()
        data = response.json()
        poster_path = data.get('poster_path')
        if poster_path:
            return f'https://image.tmdb.org/t/p/original{poster_path}'
    except requests.RequestException:
        return None

def rotate_and_save_image(img, path, rotation_degree=90):
    img = img.rotate(rotation_degree, expand=True)
    img.save(path)

def display_poster(poster_url):
    global previous_poster_url
    
    if poster_url and poster_url != previous_poster_url:
        try:
            image_response = requests.get(poster_url)
            image_response.raise_for_status()
            img = Image.open(BytesIO(image_response.content))
            rotate_and_save_image(img, temp_image_path)
            subprocess.run(['sudo', 'fbi', '-T', '1', '-d', '/dev/fb0', '-a', '-noverbose', temp_image_path], check=True)
            previous_poster_url = poster_url
        except (requests.RequestException, subprocess.CalledProcessError):
            pass

def display_watching_info(watching_data):
    if isinstance(watching_data, dict):
        media_type = watching_data.get('type')
        if media_type == 'movie':
            movie_id = watching_data.get('movie', {}).get('ids', {}).get('tmdb')
            if movie_id:
                poster_url = fetch_poster_from_tmdb(movie_id, is_movie=True)
                if poster_url:
                    display_poster(poster_url)
        elif media_type == 'episode':
            episode = watching_data.get('episode')
            show_id = watching_data.get('show', {}).get('ids', {}).get('tmdb')
            if episode and show_id:
                season_number = episode.get('season')
                if season_number:
                    poster_url = fetch_poster_from_tmdb(show_id, is_movie=False, season_number=season_number)
                    if poster_url:
                        display_poster(poster_url)

def main():
    global previous_poster_url

    while True:
        watching_data = fetch_currently_watching()
        if watching_data:
            display_watching_info(watching_data)
        time.sleep(5)  # Check every 5 seconds

if __name__ == '__main__':
    main()

import os
import json
import time
import threading
import asyncio
import aiohttp
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from features.channel_checker import check_channels
from features.stream_validator import validate_stream
import logging


# constants
M3U_URL = "https://iptv-org.github.io/iptv/index.m3u"
BATCH_SIZE = 20 # number of channels to process in each batch
FILES = {
        "streams": "iptv_streams.json", # valid streams
        "dead": "dead_steams.json", # dead streams
        "invalid": "invalid_links.json" # invalid links
}
DIRECTORIES = ['webroot', 'webroot/js']

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Ensure required directories and files exist
for directory in DIRECTORIES:
    os.makedirs(directory, exist_ok=True)
for file in FILES.values():
    if not os.path.exists(file):
        with open(file, 'w') as f:
            json.dump([], f)

# Initialize Flask app
app = Flask(__name__, template_folder='webroot', static_folder='webroot')
CORS(app) 

#checks if link exists
async def check_link_exists(session, url):
    try:
        async with session.get(url, timeout=15) as response:
            if response.status in [200, 302]:
                return True
            else:
                logging.warning(f"Invalid link: {url} (status: {response.status})")
                return False
    except Exception as e:
        logging.error(f"Error checking link {url}: {e}")
        return False


# Asynchronously validate a single channel.
async def validate_channel(session, channel):
    
    try:
        logging.info(f"Validating channel: {channel['url']}")
        if await validate_stream(session, channel['url']): 
            channel['status'] = 'online'
            return channel, True
        else:
            channel['status'] = 'offline'
            return channel, False
    except Exception as e:
        logging.error(f"Error validating channel {channel['url']}: {e}")
        channel['status'] = 'error'
        return channel, False


#Process channels in batches asynchronously
async def process_channels(channels, invalid_links):
   
    valid_channels = []
    dead_channels = []
    async with aiohttp.ClientSession() as session:
        for i in range(0, len(channels), BATCH_SIZE):
            batch = channels[i:i + BATCH_SIZE]
            tasks = [validate_channel(session, channel) for channel in batch if channel['url'] not in invalid_links]
            results = await asyncio.gather(*tasks)
            for channel, is_valid in results:
                if is_valid:
                    valid_channels.append(channel)
                else:
                    dead_channels.append(channel)
    return valid_channels, dead_channels




#Perform an initial scan to check if links exist and validate them.
async def initial_scan():
    try:
        logging.info("Starting initial scan...")
        channels = check_channels(M3U_URL)
        async with aiohttp.ClientSession() as session:
            tasks = [check_link_exists(session, ch['url']) for ch in channels]
            exists_results = await asyncio.gather(*tasks)
        invalid_links = [ch['url'] for ch, exists in zip(channels, exists_results) if not exists]
        valid_channels, dead_channels = await process_channels([ch for ch in channels if ch['url'] in exists_results], invalid_links)
        
        for file, data in zip(FILES.values(), [valid_channels, dead_channels, invalid_links]):
            with open(file, 'w') as f:
                json.dump(data, f, indent=4)


        logging.info(f"Initial scan complete: {len(valid_channels)} valid, {len(dead_channels)} dead.")
    except Exception as e:
        logging.error(f"Error during initial scan: {e}")




      
def sweep_channels():
    try:
        logging.info("Starting channel sweep...")
        channels = check_channels(M3U_URL)
        with open(FILES['invalid'], 'r') as f:
            invalid_links = json.load(f)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        valid_channels, dead_channels = loop.run_until_complete(process_channels(channels, invalid_links))
        for file, data in zip([FILES['streams'], FILES['dead']], [valid_channels, dead_channels]):
            with open(file, 'w') as f:
                json.dump(data, f, indent=4)
        logging.info(f"Channel sweep complete: {len(valid_channels)} valid, {len(dead_channels)} dead.")
    except Exception as e:
        logging.error(f"Error during channel sweep: {e}")
                      


def start_periodic_sweep():
    """Start periodic channel sweeps every 3 hours."""
    while True:
        sweep_channels()
        time.sleep(3 * 60 * 60)  # Sleep for 3 hours

@app.route('/')
def index():
    """Render the main TV guide page."""
    return render_template('index.html')

@app.route('/channels')
def get_channels():
    """Return a list of channels (15 at a time)."""
    try:
        with open(FILES['streams'], 'r') as f:
            channels = json.load(f)
            page, sort_by, group_by = int(request.args.get('page', 1)), request.args.get('sort_by', 'name'), request.args.get('group_by', 'group_title')
            channels.sort(key=lambda x: x[sort_by])
            grouped_channels = {ch[group_by]: [] for ch in channels}
            for ch in channels:
                grouped_channels[ch[group_by]].append(ch)
                paginated_channels = [ch for group in grouped_channels.values() for ch in group][(page - 1) * 15: page * 15]
                return jsonify(paginated_channels)
    except Exception as e:
        logging.error(f"Error loading channels: {e}")
        return jsonify([])

@app.route('/search')
def search_channels():
    """Search for channels by name."""
    try:
        query = request.args.get('query', '').lower()
        with open(FILES['streams'], 'r') as f:
            channels = json.load(f)
        return jsonify([ch for ch in channels if query in ch['name'].lower()])
    except Exception as e:
        logging.error(f"Error searching channels: {e}")
        return jsonify([])

if __name__ == '__main__':
    # Perform an initial scan at startup
    asyncio.run(initial_scan())

    # Start the periodic sweep in a separate thread
    sweep_thread = threading.Thread(target=start_periodic_sweep, daemon=True)
    sweep_thread.start()

    # Start the Flask web server
    app.run(host='127.0.0.1', port=40006) # i actully like this change

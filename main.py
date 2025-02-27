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

# Initialize Flask app
app = Flask(__name__, template_folder='webroot', static_folder='webroot')
CORS(app)  # Enable CORS for all routes

# Constants
M3U_URL = "https://iptv-org.github.io/iptv/index.m3u"
IPTV_STREAMS_FILE = "iptv_streams.json"
DEAD_STREAMS_FILE = "dead_streams.json"  # File to store dead streams
INVALID_LINKS_FILE = "invalid_links.json"  # File to store invalid links
BATCH_SIZE = 20  # Number of channels to process in each batch

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Ensure the webroot folder exists
if not os.path.exists("webroot"):
    os.makedirs("webroot")
if not os.path.exists("webroot/css"):
    os.makedirs("webroot/css")
if not os.path.exists("webroot/js"):
    os.makedirs("webroot/js")

# Ensure JSON files exist
if not os.path.exists(IPTV_STREAMS_FILE):
    with open(IPTV_STREAMS_FILE, 'w') as f:
        json.dump([], f)
if not os.path.exists(DEAD_STREAMS_FILE):
    with open(DEAD_STREAMS_FILE, 'w') as f:
        json.dump([], f)
if not os.path.exists(INVALID_LINKS_FILE):
    with open(INVALID_LINKS_FILE, 'w') as f:
        json.dump([], f)

async def check_link_exists(session, url):
    """Check if a link exists (does not return 404, 401, etc.)."""
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

async def validate_channel(session, channel):
    """Asynchronously validate a single channel."""
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

async def process_channels(channels, invalid_links):
    """Process channels in batches asynchronously."""
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

async def initial_scan():
    """Perform an initial scan to check if links exist and validate them."""
    try:
        logging.info("Starting initial scan...")
        channels = check_channels(M3U_URL)
        logging.info(f"Fetched {len(channels)} channels")

        # Check if links exist and validate them
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        invalid_links = []
        valid_channels = []
        dead_channels = []
        async with aiohttp.ClientSession() as session:
            tasks = [check_link_exists(session, channel['url']) for channel in channels]
            results = await asyncio.gather(*tasks)
            for channel, exists in zip(channels, results):
                if exists:
                    is_valid = await validate_stream(session, channel['url'])
                    if is_valid:
                        valid_channels.append(channel)
                    else:
                        dead_channels.append(channel)
                else:
                    invalid_links.append(channel['url'])

        # Write invalid links to file
        logging.info(f"Writing {len(invalid_links)} invalid links to {INVALID_LINKS_FILE}")
        with open(INVALID_LINKS_FILE, 'w') as f:
            json.dump(invalid_links, f, indent=4)

        # Write the JSON files
        logging.info(f"Writing {len(valid_channels)} valid channels to {IPTV_STREAMS_FILE}")
        with open(IPTV_STREAMS_FILE, 'w') as f:
            json.dump(valid_channels, f, indent=4)
        logging.info(f"Writing {len(dead_channels)} dead channels to {DEAD_STREAMS_FILE}")
        with open(DEAD_STREAMS_FILE, 'w') as f:
            json.dump(dead_channels, f, indent=4)

        logging.info(f"Initial scan complete. {len(valid_channels)} valid channels found, {len(dead_channels)} dead channels tracked.")
    except Exception as e:
        logging.error(f"Error during initial scan: {e}")

def sweep_channels():
    """Sweep through channels and update the JSON files."""
    try:
        logging.info("Starting channel sweep...")
        channels = check_channels(M3U_URL)
        logging.info(f"Fetched {len(channels)} channels")

        # Load invalid links
        with open(INVALID_LINKS_FILE, 'r') as f:
            invalid_links = json.load(f)

        # Process valid channels
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        valid_channels = [channel for channel in channels if channel['url'] not in invalid_links]
        valid_channels, dead_channels = loop.run_until_complete(process_channels(valid_channels, invalid_links))

        # Write the JSON files
        logging.info(f"Writing {len(valid_channels)} valid channels to {IPTV_STREAMS_FILE}")
        with open(IPTV_STREAMS_FILE, 'w') as f:
            json.dump(valid_channels, f, indent=4)
        logging.info(f"Writing {len(dead_channels)} dead channels to {DEAD_STREAMS_FILE}")
        with open(DEAD_STREAMS_FILE, 'w') as f:
            json.dump(dead_channels, f, indent=4)

        logging.info(f"Channel sweep complete. {len(valid_channels)} valid channels found, {len(dead_channels)} dead channels tracked.")
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
        with open(IPTV_STREAMS_FILE, 'r') as f:
            channels = json.load(f)
        page = int(request.args.get('page', 1))
        sort_by = request.args.get('sort_by', 'name')
        group_by = request.args.get('group_by', 'group_title')
        
        # Sort channels
        channels.sort(key=lambda x: x[sort_by])
        
        # Group channels
        grouped_channels = {}
        for channel in channels:
            group = channel[group_by]
            if group not in grouped_channels:
                grouped_channels[group] = []
            grouped_channels[group].append(channel)
        
        start = (page - 1) * 15
        end = start + 15
        paginated_channels = []
        for group in grouped_channels:
            paginated_channels.extend(grouped_channels[group][start:end])
            if len(paginated_channels) >= 15:
                break
        
        logging.info(f"Serving channels {start} to {end}")
        logging.info(f"Channels: {paginated_channels}")
        return jsonify(paginated_channels)
    except Exception as e:
        logging.error(f"Error loading channels: {e}")
        return jsonify([])

@app.route('/search')
def search_channels():
    """Search for channels by name."""
    try:
        query = request.args.get('query', '').lower()
        with open(IPTV_STREAMS_FILE, 'r') as f:
            channels = json.load(f)
        results = [channel for channel in channels if query in channel['name'].lower()]
        logging.info(f"Found {len(results)} channels matching query '{query}'")
        return jsonify(results)
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
    app.run(host='0.0.0.0', port=40006)
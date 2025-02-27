import requests
import logging

def parse_m3u_playlist(content):
    """
    Parse the M3U playlist content and extract channel information.
    """
    channels = []
    lines = content.splitlines()
    for i in range(len(lines)):
        if lines[i].startswith("#EXTINF:"):
            # Extract metadata from the #EXTINF line
            metadata = lines[i].strip()
            logging.info(f"Parsing metadata: {metadata}")
            channel_name = metadata.split('tvg-name="')[1].split('"')[0] if 'tvg-name="' in metadata else "Unknown"
            tvg_id = metadata.split('tvg-id="')[1].split('"')[0] if 'tvg-id="' in metadata else ""
            tvg_logo = metadata.split('tvg-logo="')[1].split('"')[0] if 'tvg-logo="' in metadata else ""
            group_title = metadata.split('group-title="')[1].split('"')[0] if 'group-title="' in metadata else "Ungrouped"

            # Extract the stream URL (next line after #EXTINF)
            if i + 1 < len(lines) and not lines[i + 1].startswith("#"):
                stream_url = lines[i + 1].strip()
                channel = {
                    "name": channel_name,
                    "url": stream_url,
                    "tvg_id": tvg_id,
                    "tvg_logo": tvg_logo,
                    "group_title": group_title,
                    "playing_now": "Not available",
                    "status": "unknown"
                }
                channels.append(channel)
    return channels

def check_channels(m3u_url):
    """
    Fetch and parse the M3U playlist from the given URL.
    """
    try:
        response = requests.get(m3u_url)
        response.raise_for_status()
        logging.info("Successfully fetched M3U playlist")
        return parse_m3u_playlist(response.text)
    except Exception as e:
        logging.error(f"Error fetching M3U playlist: {e}")
        return []
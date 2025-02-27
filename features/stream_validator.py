import aiohttp
from m3u8 import M3U8
import time
import logging

async def validate_stream(session, url, timeout=15):
    """
    Validate if a stream is active, accessible, and stable.
    Returns True if the stream is stable, False otherwise.
    """
    try:
        # Check if the URL is accessible
        async with session.get(url, timeout=timeout) as response:
            if response.status != 200:
                logging.warning(f"Stream not accessible: {url}")
                return False

            # Parse the M3U8 playlist (if it's an HLS stream)
            if url.endswith('.m3u8'):
                try:
                    text = await response.text()
                    playlist = M3U8(text)
                    if not playlist.segments:
                        logging.warning(f"No segments found in playlist: {url}")
                        return False  # No segments found, stream is invalid

                    # Check the bitrate of the first segment
                    first_segment = playlist.segments[0]
                    if not first_segment.bitrate:
                        logging.warning(f"No bitrate information in first segment: {url}")
                        return False  # No bitrate information, stream may be unstable

                    # Check if the stream is playable by fetching the first segment
                    segment_url = first_segment.absolute_uri
                    async with session.get(segment_url, timeout=timeout) as segment_response:
                        if segment_response.status != 200:
                            logging.warning(f"First segment not accessible: {segment_url}")
                            return False  # First segment is not accessible

                        # Optional: Check for buffering by timing the download of a segment
                        start_time = time.time()
                        async for _ in segment_response.content.iter_chunked(1024):
                            break  # Download a small chunk to measure speed
                        download_time = time.time() - start_time
                        if download_time > 5:  # If it takes more than 5 seconds to download a chunk, the stream may be unstable
                            logging.warning(f"Segment download time too long: {url}")
                            return False

                    return True  # Stream is stable
                except Exception as e:
                    logging.error(f"Failed to parse playlist or fetch segments: {url}, Error: {e}")
                    return False  # Failed to parse the playlist or fetch segments

        # For non-HLS streams, assume they are stable if accessible
        return True
    except Exception as e:
        logging.error(f"Stream not accessible: {url}, Error: {e}")
        return False  # Stream is not accessible
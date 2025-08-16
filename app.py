#!/usr/bin/env python3
"""
YouTube to WAV Converter - Main Application

This is the main Flask application for the YouTube to WAV Converter.
"""
import os
import re
import time
import logging
from datetime import datetime

from flask import Flask, request, jsonify, send_from_directory, render_template
import yt_dlp
from pydub import AudioSegment

# Initialize logger
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')

# Configuration
TEMP_AUDIO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp_audio')
app.config['TEMP_AUDIO_FOLDER'] = TEMP_AUDIO_DIR
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size

# Ensure temp directory exists
os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)

# Import logging after app is created to avoid circular imports
from logging.handlers import RotatingFileHandler

# yt-dlp options for maximum audio quality
ydl_opts = {
    # Get all available formats to find the best one
    'format': 'bestaudio',
    
    # Explicit format selection for highest quality
    'format_sort': [
        'vcodec:none',           # Audio only
        'acodec:m4a',            # Prefer m4a (AAC) for best quality
        'acodec:opus',           # Then Opus
        'acodec:mp3',            # Then MP3 as fallback
        'filesize:>100M',        # Prefer larger files (better quality)
        'tbr:>256',              # Minimum bitrate of 256kbps
        'asr:>44100'             # Minimum sample rate of 44.1kHz
    ],
    'format_sort_force': 'U',    # Force user's sort order
    'extract_flat': False,       # Get full format information
    'force_generic_extractor': False,
    'ignore_no_formats_error': True,
    'no_warnings': False,        # Show all warnings
    'quiet': False,              # Show progress
    'verbose': True,             # Show detailed information
    
    # Output template with detailed naming
    'outtmpl': os.path.join(TEMP_AUDIO_DIR, 
                          '%(title).100s - %(uploader).50s - %(id)s.%(ext)s'),
    
    # Force specific format combinations for best quality
    'merge_output_format': 'wav',
    'audio_quality': '0',        # Best quality
    'audioformat': 'wav',        # Output format
    'postprocessor_args': ['-ar', '48000', '-ac', '2', '-sample_fmt', 's16'],  # 48kHz, Stereo, 16-bit
    
    # Optimize for best quality extraction
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'wav',
        'preferredquality': '0',  # Highest quality
        'nopostoverwrites': True,
    }],
    # FFmpeg options for WAV
    'postprocessor_args': {
        'key': 'FFmpegExtractAudio',
        'opts': [
            '-ar', '48000',    # Sample rate
            '-ac', '2',       # Channels (stereo)
            '-b:a', '320k',   # Audio bitrate
            '-acodec', 'pcm_s16le'  # High quality PCM codec
        ]
    },
    'outtmpl': os.path.join(TEMP_AUDIO_DIR, 'youtube_audio_%(id)s.%(ext)s'),
    'quiet': False,
    'no_warnings': False,
    'nocheckcertificate': True,  # Disable SSL verification
    'source_address': '0.0.0.0',
    'socket_timeout': 30,
    'retries': 3,
    'fragment_retries': 3,
    'skip_unavailable_fragments': True,
    'forceip': 4,  # Force IPv4
    'extractor_retries': 3,
    'ignoreerrors': 'only_download',
    'no_color': True,
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-us,en;q=0.5',
        'Sec-Fetch-Mode': 'navigate',
    },
    'ffmpeg_location': 'C:\\ProgramData\\chocolatey\\bin\\ffmpeg.exe',
    'keepvideo': False,
    'merge_output_format': 'wav'
}

def make_safe_filename(filename):
    """Create a safe filename from the given string."""
    # Remove any character that is not alphanumeric, space, dot, or dash
    safe = re.sub(r'[^\w\s.-]', '', filename)
    # Replace spaces with underscores
    safe = safe.replace(' ', '_')
    # Ensure the filename is not empty
    if not safe:
        safe = 'audio'
    return safe

@app.route('/')
def serve_index():
    """Serve the main page."""
    return render_template('index.html')

def extract_video_id(url):
    """Extract video ID from various YouTube URL formats."""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/v/|youtube\.com/watch/\?v=)([^&\n?#]*)',
        r'(?:youtube\.com/watch\?.*&v=([^&#]*))',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            return match.group(1)
    return None

def setup_logging():
    """Configure basic logging to console."""
    # Clear any existing handlers
    logger.handlers = []
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    logger.setLevel(logging.INFO)
    
    return logger

def log_error(message, error=None, exc_info=False):
    """Log error messages consistently."""
    logger = logging.getLogger(__name__)
    if error:
        logger.error(f"{message} - {str(error)}", exc_info=exc_info)
    else:
        logger.error(message)

@app.route('/download', methods=['POST'])
def download_audio():
    """Handle audio download and conversion with highest quality settings."""
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'No URL provided'}), 400
            
        url = data['url'].strip()
        logger.info(f"Processing URL: {url}")
        
        # First, get video info to find the best format
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Find the best audio format
            best_format = None
            max_abr = 0
            
            for fmt in info.get('formats', []):
                if fmt.get('vcodec') == 'none':  # Audio only
                    abr = fmt.get('abr')
                    # Only consider formats with a valid bitrate
                    if abr is not None and (best_format is None or abr > max_abr):
                        max_abr = abr
                        best_format = fmt
                        
            # Fallback to any audio format if no format with bitrate was found
            if best_format is None:
                for fmt in info.get('formats', []):
                    if fmt.get('vcodec') == 'none':
                        best_format = fmt
                        max_abr = fmt.get('abr', 0)
                        break
            
            if not best_format:
                return jsonify({'error': 'No suitable audio format found'}), 400
                
            # Create a clean filename
            title = re.sub(r'[^\w\s-]', '', info.get('title', 'audio')).strip()
            uploader = re.sub(r'[^\w\s-]', '', info.get('uploader', 'unknown')).strip()
            video_id = info.get('id', str(int(time.time())))
            
            filename = f"{title} - {uploader} - {video_id}.wav"
            output_path = os.path.join(TEMP_AUDIO_DIR, filename)
            
            # Configure yt-dlp for best quality
            ydl_opts.update({
                'format': f"{best_format['format_id']}/best",
                'outtmpl': output_path.replace('.wav', '.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'wav',
                    'preferredquality': '0',
                    'nopostoverwrites': False,
                }],
                'postprocessor_args': [
                    '-ar', '48000',
                    '-ac', '2',
                    '-sample_fmt', 's16',
                    '-b:a', '320k'
                ]
            })
            
            logger.info(f"Downloading with format: {best_format['format_id']} (bitrate: {max_abr}kbps)")
            
            # Download the audio
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
                # Find the downloaded file
                base_name = os.path.basename(output_path).replace('.wav', '')
                for f in os.listdir(TEMP_AUDIO_DIR):
                    if f.startswith(base_name):
                        output_path = os.path.join(TEMP_AUDIO_DIR, f)
                        break
                
                # Get file stats
                file_size = os.path.getsize(output_path) / (1024 * 1024)  # in MB
                duration = info.get('duration', 0)
                
                logger.info(f"Successfully downloaded: {os.path.basename(output_path)} "
                          f"({file_size:.2f}MB, {duration//60}:{duration%60:02d})")
                
                return jsonify({
                    'filename': os.path.basename(output_path),
                    'title': info.get('title', 'audio'),
                    'uploader': info.get('uploader', 'unknown'),
                    'duration': duration,
                    'quality': f"{max_abr}kbps" if max_abr > 0 else "unknown",
                    'size_mb': round(file_size, 2)
                })
                
    except yt_dlp.utils.DownloadError as e:
        error_msg = f"Download error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        if 'Private video' in str(e):
            return jsonify({'error': 'This video is private and cannot be downloaded'}), 403
        elif 'Video unavailable' in str(e):
            return jsonify({'error': 'This video is unavailable or restricted'}), 404
        elif 'Unsupported URL' in str(e):
            return jsonify({'error': 'Unsupported URL. Please provide a valid YouTube URL'}), 400
        else:
            return jsonify({'error': 'Error downloading video. Please try again later.'}), 500
            
    except Exception as e:
        error_msg = f"Unexpected error in download_audio: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return jsonify({'error': 'An unexpected error occurred. Please try again later.'}), 500

@app.route('/download/<path:filename>')
def download_file(filename):
    """Serve the downloaded file for download."""
    try:
        # Ensure the filename is safe
        if not os.path.isfile(os.path.join(TEMP_AUDIO_DIR, filename)):
            return "File not found", 404
            
        return send_from_directory(
            TEMP_AUDIO_DIR,
            filename,
            as_attachment=True,
            download_name=make_safe_filename(filename)
        )
    except Exception as e:
        log_error('Error serving file', e)
        return "Error serving file", 500

if __name__ == '__main__':
    print("Starting Flask application...")
    print(f"Debug mode: {app.debug}")
    print(f"Environment: {app.env}")
    print("Available routes:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.endpoint} - {rule.rule}")
    print("Running app...")
    app.run(host='0.0.0.0', port=5000, debug=True)

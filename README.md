# YouTube to WAV Converter

A simple and fast web application to download YouTube videos as high-quality WAV audio files. The application runs locally on your machine, ensuring your data stays private.

![Screenshot](screenshot.png)

## ✨ Features

- 🚀 Lightning-fast YouTube audio extraction
- 🎵 Converts to high-quality WAV format
- 🔒 Runs locally - your data never leaves your computer
- 🌙 Dark mode interface
- 📱 Responsive design works on all devices
- ⚡ No database required

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- FFmpeg (required for audio conversion)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/youtube-wav-converter.git
   cd youtube-wav-converter
   ```

2. **Set up a virtual environment (recommended)**
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install FFmpeg**
   - **Windows**: Download from [FFmpeg's official site](https://ffmpeg.org/download.html) and add to PATH
   - **macOS**: `brew install ffmpeg`
   - **Linux**: `sudo apt install ffmpeg` (Debian/Ubuntu) or `sudo dnf install ffmpeg` (Fedora)

### Running the Application

1. **Set the Flask app environment variable**
   ```bash
   # Windows
   set FLASK_APP=app.py
   set FLASK_ENV=development

   # macOS/Linux
   export FLASK_APP=app.py
   export FLASK_ENV=development
   ```

2. **Start the application**
   ```bash
   flask run
   ```

3. **Open your browser** to http://localhost:5000

## 🛠️ Project Structure

```
youtube_wav_converter/
├── app.py                  # Main Flask application
├── requirements.txt        # Python dependencies
├── README.md              # Project documentation
├── LICENSE                # MIT License
├── screenshot.png         # Application screenshot
├── .gitignore            # Git ignore file
├── templates/             # HTML templates
│   └── index.html        # Main web interface
└── temp_audio/           # Temporary storage for audio files (created on first run)
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Notes

- The application creates a `temp_audio` directory to store temporary files during conversion.
- Logs are stored in the `logs` directory.
- For production use, ensure proper security measures are in place.

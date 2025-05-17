from setuptools import setup, find_packages

setup(
    name="youtube-downloader",
    version="0.0.1",
    packages=find_packages(),
    scripts=["bin/youtube_downloader.py"],
    
    # Dependencies
    install_requires=[
        "yt-dlp",
        "python-dotenv",
        # Add your other dependencies here
    ],
    
    # Metadata
    author="Firdaussi",
    author_email="D600Active@gmail.com",
    description="YouTube playlist downloader with enhanced features",
    keywords="youtube, downloader, playlist",
    url="https://github.com/Firdaussi/youtube-downloader",
)
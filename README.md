## Requirements
* Must have VLC installed to play video and use the `python-vlc` library
* To install necessary libraries, do
```
pip install -r requirements.txt
```
* The repository should follow this structure (for now):
```
Adaptive_CA
└─── keys
│   │   .api_key                    # OpenAI's API key
│   │   stt-private-key.json        # Google Cloud's Speech-to-text API key
│   │   tts-private-key.json        # Google Cloud's Text-to-speech API key
└─── multimedia
└─── transcripts
│   │   lucky_shirt_base.xlsx
│   │   ...
└─── videos
│   │   01_episode.mp4
│   │   02_episode.mp4
│   │   ...
│   adaptive_ca.py
│   ...
```
* (Optional) If you don't want to see error message when a video is playing (shouldn't affect our program),
 go to where VLC is installed, run:
```
vlc-cache-gen plugins/
```
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
Depends on where you installed VLC, you might need root access to run the command above

## Demo
Everything should work with the default arguments if you followed the directory structure above. Run:
```
python adaptive_ca.py
```
# Lip sync and translation script

Inspired by this [repo](https://github.com/synchronicity-labs/translation-starter?tab=readme-ov-file), I decided to create a script that would take a video, extract the audio, translate the audio, and then lip sync the translated audio back to the video.

It uses the following APIs:

- Gladia for speech-to-text
- Eleven Labs for voice cloning and text-to-speech
- Sync Labs for synchronized lip movements
- Supabase for storage

Currently the weakest part, which is also the hardest, is the lip sync.

## How to use

1. Install the requirements using `pip install -r requirements.txt`
2. Create an account on Gladia, Eleven, Sync, and Supabase
3. On Supabase, create a bucket that will store the data (currently it needs to be public and called `translation`)
4. Create a `.env` file with the following variables:
```
GLADIA_API_KEY=your_gladia_api_key
ELEVEN_API_KEY=your_eleven_api_key
SYNC_API_KEY=your_sync_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```
1. Run the script using `python main.py`


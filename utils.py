from moviepy.editor import VideoFileClip
import os
import subprocess
import json
import time
import requests
from elevenlabs import generate, play
from elevenlabs import save
from supabase import create_client, Client
from datetime import datetime
from elevenlabs import set_api_key


supabase_url: str = os.environ.get('SUPABASE_URL')
supabase_key: str = os.environ.get('SUPABASE_KEY')
gladia_key : str = os.environ.get('GLADIA_KEY')
syncLabsApiKey : str = os.environ.get('SYNCLABS_API_KEY')
elevenApiKey : str = os.environ.get('ELEVENLABS_API_KEY')


set_api_key(elevenApiKey)


def split_audio_video(video_path: str, base_path: str, video_name: str) -> None:
    """
    Split the audio from the video and remove the audio from the video
    
    """

    # Load the video file
    video = VideoFileClip(video_path)

    # Extract the audio
    audio = video.audio

    # Path where you want to save the audio file (as .mp3)
    audio_path = base_path + f'{video_name}_audio.mp3'

    # Write the audio file
    audio.write_audiofile(audio_path)

    print(f'Audio has been successfully extracted to {audio_path}')


    # Remove the audio track from the video
    video_without_audio = video.without_audio()

    # Specify the path for the output video file
    output_video_path = base_path + f'{video_name}__without_audio.mp4'

    # Write the video file without audio
    video_without_audio.write_videofile(output_video_path)

    print(f'Video with no audio has been successfully extracted to {output_video_path}')

    return audio_path, output_video_path


def make_fetch_request(url, headers, method='GET', data=None):
    """
    Make a fetch request to the specified URL with the given headers and method
    """
    
    if method == 'POST':
        response = requests.post(url, headers=headers, json=data)
    else:
        response = requests.get(url, headers=headers)
    return response.json()

def stt_and_translate(audio_path: str, output_language: str) -> None:
    """
    Perform speech to text and translation using the Gladia API
    """

    # Define the curl command as a string
    curl_command = f"""
    curl --request POST \
    --url https://api.gladia.io/v2/upload \
    --header 'Content-Type: multipart/form-data' \
    --header 'x-gladia-key: {gladia_key}' \
    --form 'audio=@{audio_path}'
    """

    # Execute the curl command
    process = subprocess.run(curl_command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # Get the output and error (if any)
    output = process.stdout
    error = process.stderr

    # Check the results
    if process.returncode == 0:
        print("Command executed successfully!")
        print("Output:", output)
    else:
        print("Command failed with error:")
        print(error)

    audio_url = json.loads(output)["audio_url"]

    request_data = {
        "audio_url": audio_url,
        "translation": True,
        "translation_config":
        {
        "target_languages": [output_language],
        "model": "base" ## "enhanced" is slower but of better quality
        }
    }
    gladia_url = "https://api.gladia.io/v2/transcription/"

    headers = {
        "x-gladia-key": gladia_key,
        "Content-Type": "application/json"
    }

    print("- Sending initial request to Gladia API...")
    initial_response = make_fetch_request(
        gladia_url, headers, 'POST', request_data)

    print("Initial response with Transcription ID:", initial_response)
    result_url = initial_response.get("result_url")

    if result_url:
        while True:
            print("Polling for results...")
            poll_response = make_fetch_request(result_url, headers)

            if poll_response.get("status") == "done":
                print("- Transcription done: \n")
                translation = poll_response.get("result", {}).get(
                    "translation", {})
                print(translation)
                break
            else:
                print("Transcription status:", poll_response.get("status"))
            time.sleep(1)

    # Initialize an empty dictionary to store the results
    language_sentences = {}

    # Iterate through the results to extract language and corresponding full transcript
    for result in translation["results"]:
        language = result["languages"][0]  # Assuming each result has only one language
        transcript = result["full_transcript"]
        language_sentences[language] = transcript
    
    return language_sentences[output_language]


def tts(input_text: str, base_path: str, video_name: str, gender: str) -> None:
    """
    Generate audio from translated text using the ElevenLabs API
    """
    
    if gender == "M":
        voice = "Arnold"
    else:
        voice = "Rachel"


    audio = generate(
        text=input_text,
        model='eleven_multilingual_v1',
        voice=voice
    )
    output_path = base_path + f"{video_name}_translated_audio.mp3"
    save(audio, output_path)
    return output_path

def upload_files_to_supabase(video_path: str, translated_audio_path: str) -> None:
    """
    Upload the video without audio and the translated audio to Supabase
    """

    client = create_client(supabase_url, supabase_key)
    bucket_name = "translation"
    #bucket = client.storage.get_bucket(bucket_name)

    current_datetime = datetime.now()
    job_id = current_datetime.strftime('%Y%m%d%H%M%S')

    audio_path = f"audio_{job_id}.mp3"
    video_path = f"video_{job_id}.mp4"

    # upload: video without audio and translated audio
    with open(translated_audio_path, 'rb') as f:
        client.storage.from_(bucket_name).upload(file=f,path=audio_path, file_options={"content-type": "audio/mpeg"})

    with open(video_path, 'rb') as f:
        client.storage.from_(bucket_name).upload(file=f,path=video_path, file_options={"content-type": "video/mp4"})

    # retrieve public urls
    audio_url = client.storage.from_(bucket_name).get_public_url(audio_path)
    video_url = client.storage.from_(bucket_name).get_public_url(video_path)

    return audio_url, video_url, audio_path, video_path

def lip_sync(audio_url: str, video_url: str) -> None:
    """
    Perform lip sync using the SyncLabs API
    """


    API_URL = "https://api.synclabs.so/video"

    # Define the payload
    payload = {
        "audioUrl": audio_url,
        "videoUrl": video_url,
        "synergize": True,
    # "webhookUrl": "your_base_url_here/api/lip-sync/webhook",
        "model": "sync-1.5-beta"
    }

    # Define the headers
    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": syncLabsApiKey
    }

    # Log sending request
    print('Sending request to SyncLabs at', API_URL)

    # Make the POST request
    try:
        response = requests.post(API_URL, headers=headers, data=json.dumps(payload))

        # Log response received
        print('Response from SyncLabs received')

        # Check if the response is successful
        if response.status_code == 200:
            # Process the successful response
            data = response.json()
            print('Returning response from SyncLabs')
            print(data)  # Or handle it as needed
        elif response.status_code == 201:
            print('Request accepted, generation in progress...')
            data = response.json()
            text = response.text
        else:
            # Handle errors
            error_text = response.text
            print(f'Failed to lip sync video to audio: {response.status_code} {error_text}')
            # You might want to raise an exception or handle it according to your application's needs
    except Exception as error:
        # Handle unexpected errors
        print(f'Unexpected error occurred: {error}')
        # Similar to the JavaScript version, you might want to handle the exception according to your needs

    video_id = data["id"]

    # Check the status of the job
    status, download_link = check_job_status(video_id)

    while status != "COMPLETED":
        if status != "PENDING" and status != "PROCESSING":
            print(f'Error with Synclabs, status: {status}')
            break
        print('Video is being processed...')
        time.sleep(10)
        status, download_link = check_job_status(video_id)
        

    return download_link



def check_job_status(video_id: str) -> str:
    """
    Check the status of the job using the SyncLabs API
    """


    # Define the URL
    url = 'https://api.synclabs.so/video/' + video_id

    # Define the headers
    headers = {
        'accept': 'application/json',
        'x-api-key': syncLabsApiKey,
    }

    # Make the GET request
    response = requests.get(url, headers=headers)

    # Check if the request was successful
    if response.status_code == 200:
        # Process the successful response
        data = response.json()
    else:
        # Handle errors
        print(f'Failed to get video details: {response.status_code}')
        print(response.text)

    return data["status"], data["url"]


def delete_files_supabase(audio_path: str, video_path: str) -> None:
    """
    Delete files from Supabase
    """

    client = create_client(supabase_url, supabase_key)
    bucket_name = "translation"

    # delete files
    client.storage.from_(bucket_name).remove([audio_path, video_path])

    print("Files deleted from Supabase.")

def download_video(download_link: str, base_path: str, video_name: str) -> None:
    """
    Download the final video from the given URL
    """

    # Send a HTTP request to the URL of the video
    r = requests.get(download_link, stream = True)

    # Open the file in write and binary mode
    with open(base_path + f"{video_name}_final_video.mp4", 'wb') as f:

        # Write the contents of the response (r.content)
        # to a new file in binary mode.
        for chunk in r.iter_content(chunk_size = 1024*1024):
            if chunk:
                f.write(chunk)

    print("Video downloaded successfully.")

from utils import split_audio_video, stt_and_translate, tts, upload_files_to_supabase, lip_sync, download_video, delete_files_supabase

def main():
    # User input for base paths and inputs
    base_path = input("Enter the base path: ")
    video_name = input("Enter the video name with extension (e.g., video.mp4): ")
    output_language = input("Enter the target language for translation (e.g., 'es' for Spanish): ")
    gender = input("Enter the gender (M/F): ")

    # Processing inputs
    video_path = base_path + video_name
    video_name = video_name.split('.')[0]

    # Output the processed inputs
    print("Processed Video Name:", video_name)
    print("Video Path:", video_path)
    print("Output Language:", output_language)
    print("Gender:", gender)

    
    # Step 1: Split audio from video and remove audio from video
    print("Step 1: Splitting audio and video...")
    original_audio_path, silent_video_path = split_audio_video(video_path, base_path, video_name)
    
    # Step 2: Speech to text and translate
    print("Step 2: Performing speech to text and translation...")
    translated_text = stt_and_translate(original_audio_path, output_language)
    
    # Step 3: Generate audio from translated text
    print("Step 3: Generating audio from translated text...")
    translated_audio_path = tts(translated_text, base_path, video_name, gender)

    # Step 4: Upload files to Supabase
    print("Step 4: Uploading files to Supabase...")
    audio_url, video_url, supabase_audio_path, supabase_video_path = upload_files_to_supabase(silent_video_path, translated_audio_path)
    
    # Step 5: Perform lip sync using SyncLabs
    print("Step 5: Performing lip sync using SyncLabs...")
    download_link = lip_sync(audio_url, video_url)

    print("Step 6: Downloading the final video...")

    download_video(download_link, base_path, video_name)

    print("Step 7: Deleting files from supabase...")

    delete_files_supabase(supabase_audio_path, supabase_video_path)

    print("Pipeline completed. Download link:", download_link)

if __name__ == '__main__':
    main()
 
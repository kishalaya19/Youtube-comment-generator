import os
import re
from googleapiclient.discovery import build
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import openai
import gradio as gr
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get API keys from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

def extract_video_id(url):
    # Handle both mobile and desktop URLs
    if "youtu.be" in url:
        video_id = re.search(r"youtu\.be/([^&]+)", url).group(1)
    else:
        video_id = re.search(r"v=([^&]+)", url).group(1)
    return video_id

def get_youtube_comments(video_id):
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    comments = []
    try:
        # Request to get comments
        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=200
        )
        response = request.execute()
        
        # Extract comments
        for item in response['items']:
            comment_data = item['snippet']['topLevelComment']['snippet']
            comments.append({
                'text': comment_data['textOriginal'],
                'like_count': comment_data['likeCount']
            })
        
        while 'nextPageToken' in response and len(comments) < 1000:
            request = youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                pageToken=response['nextPageToken'],
                maxResults=100
            )
            response = request.execute()
            for item in response['items']:
                comment_data = item['snippet']['topLevelComment']['snippet']
                comments.append({
                    'text': comment_data['textOriginal'],
                    'like_count': comment_data['likeCount']
                })
                if len(comments) >= 1000:
                    break
    except Exception as e:
        print(f"An error occurred: {e}")
    
    # Sort comments by like count in descending order and take the top 20
    comments = sorted(comments, key=lambda x: x['like_count'], reverse=True)[:20]
    return [comment['text'] for comment in comments]

def generate_story(comments, temperature=0.7):
    words = []
    word_count = 0

    for comment in comments:
        comment_words = comment.split()
        if word_count + len(comment_words) > 1000:
            break
        words.extend(comment_words)
        word_count += len(comment_words)

    comments_text = " ".join(words)
    
    openai.api_key = OPENAI_API_KEY
    client = openai
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": f"""
        
                    Read all the comments, understand the emotions people are feeling and pick any random emotion 
                    and create a story in first person (the person can be randomly young or old and the story can be
                    based in past or future) based on that emotion picking a random character keep the words 
                    simple and a bit profound but overall simple words. Give more weight to the comments that 
                    come earlier in sequence. The comments are given here: {comments_text}"""},
                  {"role": "assistant", "content": """
                    ignore the comment which has lyrics of the song, 
                  ignore all comments similar to 'anyone in 2024', Keep the story randomly between 50-120 words. 
                  dont mention the emtion chosen just start the story. 
                  sometimes include bits where you tell how this song makes you feel. be very nostalgic about a feeling or a place this
                  takes you to. half the times end the story with a hopeful future or a dark end or humorous.. choose randomly. dont start the story with when you forst heard this song"""}]
    ,temperature=temperature)
    return completion.choices[0].message.content

# Main function to execute the process
def main(youtube_url, temperature):
    video_id = extract_video_id(youtube_url)
    comments = get_youtube_comments(video_id) 
    story = generate_story(comments, temperature)
    return story

# Create Gradio interface
youtube_url_input = gr.Textbox(label="YouTube URL")
temperature_input = gr.Slider(minimum=0.0, maximum=2.0, value=1.2, label="Temperature (creativity)")

iface = gr.Interface(
    fn=main, 
    inputs=[youtube_url_input, temperature_input], 
    outputs="text", 
    title="Let's hear a Story",
    description="Enter a YouTube video URL to read a story which will capture the emotions of thousands of people before you who have listened to this and left comments :). The stories are AI-generated but does that mean it has never happened before or never will? Maybe the reader finds their own story with AI"
)

# Launch the interface
iface.launch(share=True)

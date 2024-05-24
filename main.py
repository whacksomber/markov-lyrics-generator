import requests
import re
from fake_useragent import UserAgent # also needed to avoid ban from azlyrics
import random
from time import sleep
import markovify
from bs4 import BeautifulSoup
from tkinter import *
from tkinter import ttk
import threading
import musicbrainzngs
from musicbrainzngs import WebServiceError
from musicbrainzngs import NetworkError
import json
import lyricsgenius
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures

GENIUS_CLIENT_ID = '<REDACTED>'
GENIUS_CLIENT_SECRET = '<REDACTED>'
GENIUS_ACCESS_TOKEN = '<REDACTED>'

genius = lyricsgenius.Genius(GENIUS_ACCESS_TOKEN, timeout=10)
musicbrainzngs.set_useragent("Markov Lyrics Generator", "0.1")

NUM_LINES = 0
ARTIST_NAME = ""

ALL_SONGS = []

def clean_up_artist_name (name):
    if name.startswith('the '):
        name = name[4:]
    return name.strip().lower().replace(' ', '')

def enable_fields():
    for w in root.winfo_children():
        w['state'] = 'normal'
    artist_var.set('')
    num_var.set('')

def disable_fields():
    for w in root.winfo_children():
        w['state'] = 'disabled'

def get_artist_name ():
    try:
        artist = artist_var.get()
        if not artist:
            raise RuntimeError("Input field left empty! Try again.")
    except RuntimeError as e:
        raise RuntimeError(str(e))
    
    return artist

def get_num_lines():
    try:
        num_lines = num_var.get()
        num_lines = int(num_lines)
    except TclError:
        return None
    return num_lines

def get_user_input ():
    global NUM_LINES
    global ARTIST_NAME
    
    NUM_LINES = get_num_lines()
    
    try:
        ARTIST_NAME = get_artist_name()
    except RuntimeError as e:
        processing_label['text'] = str(e)
        enable_fields()
        raise RuntimeError(str(e))
    
    if not NUM_LINES or not ARTIST_NAME or NUM_LINES < 1:
        enable_fields()
        processing_label['text'] = "Invalid input. Try again"
        return
    
    disable_fields()

    processing_label['text'] = f"Generating {NUM_LINES} lines in the style of {ARTIST_NAME}..."

    threading.Thread(target=process_lyrics).start() # Start the lyrics generation in a new thread

def get_artist_info (artist_name):
    return musicbrainzngs.search_artists(artist=artist_name, strict=True)['artist-list'][0]

def get_artist_id (artist_name):
    return get_artist_info(artist_name)['id']

def get_album_list (artist_name):
    artist_id = get_artist_id(artist_name)
    return musicbrainzngs.get_artist_by_id(artist_id, includes=['release-groups'])['artist']['release-group-list']

def get_track_list (album_id):
    try:
        medium_list = musicbrainzngs.get_release_by_id(album_id, includes=['recordings'])['release']['medium-list']
        
        track_list = []
        
        for medium in medium_list:
            for track in medium['track-list']:
                track_list.append(track['recording']['title'])
        return track_list
    except IndexError:
        raise(RuntimeError("No tracks found ."))
    except NetworkError:
        raise(RuntimeError("Network error."))

# fetches info about the first/original release of a given album
@lru_cache(maxsize=None)
def get_album_info (album_id):
    release_list = musicbrainzngs.get_release_group_by_id(album_id, includes=['releases'], release_status='official')['release-group']['release-list']
    if release_list:
        return release_list[0]
    else:
        return None

def get_all_songs():
    global ALL_SONGS
    global ARTIST_NAME
    
    album_list = get_album_list(ARTIST_NAME)
    
    # Add the progress bar
    progress_bar = ttk.Progressbar(root, orient='horizontal', length=300, mode='determinate')
    progress_bar.grid(row=4, column=0, columnspan=2, pady=10)
    
    # add the label
    progress_label = Label(root, text='Getting album tracks...')
    progress_label.grid(row=5, column=0, columnspan=2)
    
    progress_label2 = Label(root)
    progress_label2.grid(row=4, column=2, columnspan=2, pady=10)

    progress_bar['maximum'] = len(album_list)
    progress_bar['value'] = 0

    for album in album_list:
        album_info = get_album_info(album['id'])
        if album_info is not None:
            try:
                ALL_SONGS += get_track_list(album_info['id'])
                
                progress_bar['value'] += 1  # Update the progress bar
                progress_label2['text'] = f'{progress_bar["value"]}/{progress_bar["maximum"]}'  # Update the label
                root.update_idletasks()  # Refresh the UI
            except NetworkError:
                print("Network error.")
    
    progress_label['text'] = 'Album tracks retrieved!'
    progress_bar.destroy()
    progress_label2.destroy()
    progress_label.destroy()
    
    clean_song_list()

def process_lyrics():
    get_all_songs()
    write_lyrics_file()
    generate_markov_lines(NUM_LINES)
    enable_fields()
    processing_label['text'] = "Lyrics generation complete."

def generate_markov_lines(num_lines, file_name = "lyrics.txt"):
    try:
        text_box = Text(root, height=20, width=50)
        text_box.grid(row=6, column=0, columnspan=2)
        with open(file_name, 'r', encoding='utf-8') as file:
            text = file.read()
            if not text:
                print('No lyrics found.')
                return
        
        markovifyTextModel = markovify.Text(text)
        
        for i in range(num_lines):
            line = markovifyTextModel.make_sentence()
            text_box.insert(END, f"{line}\n")        
    except FileNotFoundError:
        print('No lyrics file found.')

pattern = re.compile("\d+ Contributors|See .+ LiveGet tickets as low as \$\d+You might also like\n?|\d*Embed|.+ Lyrics\n?")
def clean_up_lyrics (lyrics_str):
    if not lyrics_str:
        return ""
    lyrics_str = re.sub(pattern, "", lyrics_str)
    return re.sub("\n+", "\n", lyrics_str)

def clean_song_list ():
    global ALL_SONGS
    
    ALL_SONGS.sort() # sort list alphabetically
    
    seen_names = set()
    new_list = []
    
    for item in ALL_SONGS:
        item_clean = re.sub("(\'|\W)", "", re.sub(r" [\(|\]].*[\)|\]]", "", item))
        
        if item_clean not in seen_names:
            new_list.append(item)
            seen_names.add(item_clean)
    
    ALL_SONGS = new_list

def fetch_lyrics(song):
    global ARTIST_NAME
    
    try:
        genius.verbose = False
        genius.remove_section_headers = True
        current = genius.search_song(song, ARTIST_NAME, get_full_info=False)
        if current is not None and current.artist.lower() == ARTIST_NAME.lower():
            return current.lyrics
        else:
            return ""
    except AttributeError:
        raise(RuntimeError("No lyrics found."))
    except requests.exceptions.Timeout:
        print("Whoops! Timeout occurred.\n")

def write_lyrics_file():
    global ARTIST_NAME
    global ALL_SONGS
    
    # Add the progress bar
    progress_bar = ttk.Progressbar(root, orient='horizontal', length=300, mode='determinate')
    progress_bar.grid(row=4, column=0, columnspan=2, pady=10)
    
    # add the label
    progress_label = Label(root, text='Downloading lyrics...')
    progress_label.grid(row=5, column=0, columnspan=2)
    progress_label2 = Label(root)
    progress_label2.grid(row=4, column=2, columnspan=2, pady=10)
    progress_bar['maximum'] = len(ALL_SONGS)
    progress_bar['value'] = 0
    
    lyrics_lines = []
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_song = {executor.submit(fetch_lyrics, song): song for song in ALL_SONGS}
        
        for future_lyrics in concurrent.futures.as_completed(future_to_song):
            try:
                lyrics_lines.append(future_lyrics.result())
            except AttributeError:
                raise(RuntimeError("No lyrics found."))
            
            progress_bar['value'] += 1  # Update the progress bar
            progress_label2['text'] = f'{progress_bar["value"]}/{progress_bar["maximum"]}'  # Update the label
            root.update_idletasks()  # Refresh the UI

    progress_label['text'] = 'Lyrics downloaded!'
    progress_bar.destroy()
    progress_label2['text'] = ""
    progress_label['text'] = ""
    
    # write lyrics_lines to a file
    with open('lyrics.txt', 'w', encoding='utf-8') as file:
        for line in lyrics_lines:
            file.write(clean_up_lyrics(line))

root = Tk()
root.title('Markov Lyrics Generator')

root.geometry('400x565')

artist_var = StringVar()
num_var = IntVar()

input_fields = [
    ('Artist Name: ', artist_var),
    ('Number of lines: ', num_var)
]

for i, (label, var) in enumerate(input_fields):
    Label(root, text=label).grid(row=i, column=0)
    Entry(root, textvariable=var).grid(row=i, column=1)

submit_button = Button(root, text='Generate Lyrics', command=get_user_input)
submit_button.grid(row=2, column=0, columnspan=2)

processing_label = Label(root)
processing_label.grid(row=3, column=0, columnspan=2)

root.mainloop()
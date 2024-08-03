import requests
import re
import markovify
from tkinter import *
from tkinter import ttk
import threading
import musicbrainzngs
from musicbrainzngs import NetworkError
import lyricsgenius
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
import os
import time

GENIUS_CLIENT_ID = '<REDACTED>'
GENIUS_CLIENT_SECRET = '<REDACTED>'
GENIUS_ACCESS_TOKEN = '<REDACTED>'

NUM_LINES = 0
ARTIST_NAME = ""

THREAD_COUNT = os.cpu_count() * 1

class progressBar:
    def __init__ (self, root, list_var, label_text):
        self.progress_bar = ttk.Progressbar(root, orient='horizontal', length=300, mode='determinate')
        self.progress_bar.grid(row=4, column=0, columnspan=2, pady=10)
    
        # add the text label (the one that goes underneath the progress bar)
        self.progress_text_label = Label(root, text=label_text)
        self.progress_text_label.grid(row=5, column=0, columnspan=2)

        # add the value label (the one that shows the progress as a fraction to the side of the progress bar)
        self.progress_value_label = Label(root)
        self.progress_value_label.grid(row=4, column=2, columnspan=2, pady=10)
        self.progress_bar['maximum'] = len(list_var)
        self.progress_bar['value'] = 0
    
    def set_progress_text (self, text):
        self.progress_text_label['text'] = text
    
    def increment_progress (self, increment_value=1):
        self.progress_bar['value'] += increment_value
        progress_percentage = (self.progress_bar['value'] / self.progress_bar['maximum']) * 100
        self.progress_value_label['text'] = f'{self.progress_bar["value"]}/{self.progress_bar["maximum"]} ({progress_percentage:.1f}%)'
        root.update_idletasks()
    
    def destroy (self):
        self.progress_bar.destroy()
        self.progress_value_label.destroy()
        self.progress_text_label.destroy()

class MusicBrainzHandler:
    def __init__(self, artist_name):
        musicbrainzngs.set_useragent("Markov Lyrics Generator", "0.1")
        self.artist_json = self.get_artist_info(artist_name)
        self.set_artist_name()
        self.artist_id = self.get_artist_id()
        self.album_list = []
        self.song_list = []
        
        self.get_all_songs()
    
    def set_artist_name (self):
        self.artist_name = self.artist_json['name']
    
    def get_artist_info (self, artist_name):
        return musicbrainzngs.search_artists(artist=artist_name, strict=True)['artist-list'][0]

    def get_artist_id (self):
        return self.artist_json['id']

    def get_album_list (self):
        return musicbrainzngs.get_artist_by_id(self.artist_id, includes=['release-groups'])['artist']['release-group-list']

    # fetches info about the first/original release of a given album
    @lru_cache(maxsize=None)
    def get_album_info (self, album_id):
        release_list = musicbrainzngs.get_release_group_by_id(album_id, includes=['releases'], release_status='official')['release-group']['release-list']
        if release_list:
            return release_list[0]
        else:
            return None
    
    def get_track_list (self, album_id):
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

    def get_all_songs(self):
        global ARTIST_NAME
        
        album_list = self.get_album_list()
        
        progress_bar = progressBar(root, album_list, "Getting album tracks...")

        with ThreadPoolExecutor(max_workers=THREAD_COUNT) as executor:
            future_to_album = {executor.submit(self.get_album_info, album['id']): album for album in album_list}
            
            for future_album in concurrent.futures.as_completed(future_to_album):                
                try:
                    album_info = future_album.result()
                    if album_info is not None:
                        self.song_list += self.get_track_list(album_info['id'])
                        progress_bar.increment_progress()
                except NetworkError:
                    print("Network error.")
        
        progress_bar.set_progress_text("Album tracks retrieved!")
        progress_bar.destroy()
        
        self.clean_song_list()
    
    def clean_song_list (self):
        self.song_list.sort() # sort list alphabetically
        
        seen_names = set()
        new_list = []
        
        for item in self.song_list:
            item_clean = re.sub("(\'|\W)", "", re.sub(r" [\(|\]].*[\)|\]]", "", item))
            
            if item_clean not in seen_names:
                new_list.append(item)
                seen_names.add(item_clean)
        
        self.song_list = new_list

class LyricsGeniusHandler:
    def __init__(self, song_list):
        self.genius = lyricsgenius.Genius(GENIUS_ACCESS_TOKEN, timeout=10)
        self.genius.verbose = False
        self.genius.remove_section_headers = True
        self.pattern = re.compile("\d+ Contributors|See .+ LiveGet tickets as low as \$\d+You might also like\n?|\d*Embed|.+ Lyrics\n?|You might also like")
        self.song_list = song_list
    
    def fetch_lyrics(self, song):
        global ARTIST_NAME
        
        try:
            current = self.genius.search_song(song, ARTIST_NAME, get_full_info=False)
            if current is not None and current.artist.lower() == ARTIST_NAME.lower():
                return current.lyrics
            else:
                return ""
        except AttributeError:
            raise(RuntimeError("No lyrics found."))
        except requests.exceptions.Timeout:
            print("Whoops! Timeout occurred.\n")
    
    def write_lyrics_file(self):
        global ARTIST_NAME
        
        progress_bar = progressBar(root, self.song_list, "Downloading lyrics...")
        
        lyrics_lines = []
        
        with ThreadPoolExecutor(max_workers=THREAD_COUNT) as executor:
            future_to_song = {executor.submit(self.fetch_lyrics, song): song for song in self.song_list}
            
            for future_lyrics in concurrent.futures.as_completed(future_to_song):
                try:
                    lyrics_lines.append(future_lyrics.result())
                except AttributeError:
                    raise(RuntimeError("No lyrics found."))
                
                progress_bar.increment_progress()

        progress_bar.set_progress_text("Lyrics downloaded!")
        progress_bar.destroy()
        
        # write lyrics_lines to a file
        with open('lyrics.txt', 'w', encoding='utf-8') as file:
            for line in lyrics_lines:
                file.write(self.clean_up_lyrics(line) + '\n')
    
    def clean_up_lyrics (self,lyrics_str):
        if not lyrics_str:
            return ""
        lyrics_str = re.sub(self.pattern, "", lyrics_str)
        return re.sub("\n+", "\n", lyrics_str)

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
        change_processing_label(str(e))
        enable_fields()
        raise RuntimeError(str(e))
    
    if not NUM_LINES or not ARTIST_NAME or NUM_LINES < 1:
        enable_fields()
        change_processing_label("Invalid input. Try again.")
        return
    
    disable_fields()

    change_processing_label(f"Generating {NUM_LINES} lines in the style of {ARTIST_NAME}...")

    threading.Thread(target=process_lyrics).start() # Start the lyrics generation in a new thread

def process_lyrics():
    all_songs = MusicBrainzHandler(ARTIST_NAME).song_list
    LyricsGeniusHandler(all_songs).write_lyrics_file()
    generate_markov_lines(NUM_LINES)
    enable_fields()
    change_processing_label("Lyrics generation complete.")

def generate_markov_lines(num_lines, file_name = "lyrics.txt"):
    try:
        text_box = Text(root, height=20, width=50)
        text_box.grid(row=6, column=0, columnspan=2)
        with open(file_name, 'r', encoding='utf-8') as file:
            text = file.read()
            if not text:
                print('No lyrics found.')
                return
        
        markovifyTextModel = markovify.NewlineText(text)
        
        for i in range(num_lines):
            attempts = 0
            line = markovifyTextModel.make_sentence()
            if line is not None:
                text_box.insert(END, f"{line}\n")        
    except FileNotFoundError:
        print('No lyrics file found.')

def setup_gui (root):
    global artist_var, num_var, processing_label
    
    root.title('Markov Lyrics Generator')
    root.geometry('400x515')
    root.resizable(0, 0)
    
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

def change_processing_label (text):
    processing_label['text'] = text

root = Tk()
setup_gui(root)
root.mainloop()
end_time = time.time()
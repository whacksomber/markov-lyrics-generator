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

URL_PREFIX = "https://www.azlyrics.com/"

ARTIST_URL = ""
NUM_LINES = 0

def get_html_str(url):
    try:
        r = requests.get(url, headers={'User-Agent': UserAgent().random})
        r.raise_for_status()
        return r.text
    except requests.exceptions.RequestException as e:
        error_message = {
            requests.exceptions.HTTPError: f"HTTP ERROR! {e}",
            requests.exceptions.ConnectionError: f"Error connecting to the URL: {e}",
            requests.exceptions.Timeout: f"Timeout occurred while fetching HTML: {e}",
        }.get(type(e), f"An error occurred while fetching HTML: {e}")
        
        raise RuntimeError(error_message)

def get_lyrics (url):
    try:
        html_str = get_html_str(url)
        soup = BeautifulSoup(html_str, 'lxml')
        lyrics = soup.find('div', class_="col-xs-12 col-lg-8 text-center").find(lambda tag: tag.name == 'div' and not tag.attrs)
        return re.sub(r'\[.*?\]', '', lyrics.text) if lyrics else None
    except RuntimeError as e:
        print(str(e))
        return None

def get_song_links(url):
    try:
        artist_html_str = get_html_str(url)
        soup = BeautifulSoup(artist_html_str, 'lxml')
        return [f"{URL_PREFIX}{link['href'][1:]}" for link in soup.find_all('a', href=True)if '/lyrics/' in link['href']]
    except RuntimeError as e:
        print(str(e))
        return None

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

def get_artist_url ():
    try:
        artist = clean_up_artist_name(artist_var.get())
        url = f"{URL_PREFIX}{artist[0]}/{artist}.html" # url of the artist page on azlyrics
        html_str = get_html_str(url)
    except IndexError:
        processing_label['text'] = "Input field left empty! Try again."
        enable_fields()
    except RuntimeError as e:
        raise RuntimeError(str(e))
    
    return url

def get_num_lines():
    try:
        num_lines = num_var.get()
        num_lines = int(num_lines)
    except TclError:
        return None
    return num_lines

def get_user_input ():
    global NUM_LINES
    global ARTIST_URL
    
    NUM_LINES = get_num_lines()
    
    try:
        ARTIST_URL = get_artist_url()
    except RuntimeError as e:
        processing_label['text'] = str(e)
        enable_fields()
        raise RuntimeError(str(e))
    
    if not NUM_LINES or not ARTIST_URL or NUM_LINES < 1:
        enable_fields()
        processing_label['text'] = "Invalid input. Try again"
        return
    
    disable_fields()

    processing_label['text'] = f"Generating {NUM_LINES} lines from {ARTIST_URL}..."

    # Start the lyrics generation in a new thread
    threading.Thread(target=process_lyrics).start()
    
def process_lyrics():
    write_lyrics_file(ARTIST_URL)
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

def write_lyrics_file(url, file_name = "lyrics.txt"):   
    song_links = get_song_links(url)
    
    # Add the progress bar
    progress_bar = ttk.Progressbar(root, orient='horizontal', length=300, mode='determinate')
    progress_bar.grid(row=4, column=0, columnspan=2, pady=10)
    
    # add the label
    progress_label = Label(root, text='Downloading lyrics...')
    progress_label.grid(row=5, column=0, columnspan=2)
    
    progress_label2 = Label(root)
    progress_label2.grid(row=4, column=2, columnspan=2, pady=10)

    progress_bar['maximum'] = len(song_links)
    progress_bar['value'] = 0

    if not song_links:
        print('No songs found')
        return

    with open('lyrics.txt', 'w', encoding='utf-8') as lyrics_original:
        for x in song_links:
            lyrics = get_lyrics(x)
            if not lyrics:
                continue
            progress_bar['value'] += 1  # Update the progress bar
            progress_label2['text'] = f'{progress_bar["value"]}/{progress_bar["maximum"]}'  # Update the label
            root.update_idletasks()  # Refresh the UI
            lyrics_original.write(lyrics)
            sleep (random.randint(2, 10)) # sleep for a random amount of time between 2 and 7 seconds to avoid ban from azlyrics

    progress_label['text'] = 'Lyrics downloaded!'
    progress_bar.destroy()
    progress_label2.destroy()

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
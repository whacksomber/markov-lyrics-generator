import requests
import re
from time import sleep # needed to avoid ban from alyrics
from fake_useragent import UserAgent # also needed to avoid ban from azlyrics
import random
import time
from alive_progress import alive_it
import markovify

DISCLAIMER = "Usage of azlyrics.com content by any third-party lyrics provider is prohibited by our licensing agreement. Sorry about that. -->"

def get_html_str (url):
    try:
        # get the html of the page, using a random user agent to avoid ban from azlyrics
        r = requests.get(url, headers={'User-Agent': UserAgent().random})
        return r.text
    except requests.exceptions.RequestException as e:
        print("Oops! An error occured: ", e)
        return None

def get_lyrics (url):
    html_str = get_html_str(url)

    if html_str == None:
        print('No lyrics page found for: ', url)
        return None

    split = html_str.split(DISCLAIMER,1)
    split_html = split[1] # get everything after the disclaimer
    split = split_html.split('</div>',1) # get everything before the end of the lyrics
    lyrics = split[0]
    lyrics = lyrics.replace('<br>', '\n')
    lyrics = lyrics.replace('\\', '')
    lyrics = lyrics.replace('\nn', '\n')
    lyrics = lyrics.replace('\r', '')
    lyrics = lyrics.replace('<i>', '')
    lyrics = lyrics.replace('</i>', '')
    lyrics = lyrics.replace('[Chorus]', '')
    
    return lyrics

def get_song_links(url):
    artist_html_str = get_html_str(url)

    if artist_html_str == None:
        print('No artist page found')
        return []

    # get all the links to the songs of the artist
    song_links = re.findall(r'href="([^"]*lyrics/[^"]*)"', artist_html_str)
    song_links = list(map(lambda x: "https://www.azlyrics.com" + x, song_links))
    return song_links

start_time = time.time() # start time of the program

url = "https://www.azlyrics.com/a/acidbath.html" # url of the artist page on azlyrics
lyrics_original = open('lyrics.txt', 'w', encoding='utf-8') # open a file to write the lyrics to
song_links = get_song_links(url)

if song_links == []:
    print('No songs found')
    exit()

print('Number of songs found: ', len(song_links))

for x in alive_it(song_links):
    lyrics = get_lyrics(x)
    if lyrics == None:
        continue
    lyrics_original.write(lyrics)
    sleep (random.randint(2, 10)) # sleep for a random amount of time between 2 and 10 seconds to avoid ban from azlyrics
lyrics_original.close()

file = open('lyrics.txt', 'r') # open the file with the lyrics in read mode

generatedlyrics = ()
text = file.read()

if text == '':
    print('No lyrics found.')
    exit()

file.close()

markovifyTextModel = markovify.Text(text)
generatedlyrics = markovifyTextModel.make_sentence()

print(generatedlyrics)

print("--- %s seconds ---" % round(time.time() - start_time, 2)) # print the time it took to run the program
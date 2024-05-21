import requests
import re
from time import sleep # needed to avoid ban from alyrics
from fake_useragent import UserAgent # also needed to avoid ban from azlyrics
import random
import time
from alive_progress import alive_it
import markovify
from bs4 import BeautifulSoup

URL_PREFIX = "https://www.azlyrics.com/"

def get_html_str (url):
    try:
        # get the html of the page, using a random user agent to avoid ban from azlyrics
        r = requests.get(url, headers={'User-Agent': UserAgent().random})
        r.raise_for_status()
        return r.text
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Error fetching HTML: {e}")

def get_lyrics (url):
    html_str = get_html_str(url)

    if not html_str:
        print(f'No lyrics page found for: {url}')
        return None

    soup = BeautifulSoup(html_str, 'lxml')
    lyrics = soup.find('div', class_="col-xs-12 col-lg-8 text-center").find(lambda tag: tag.name == 'div' and not tag.attrs)
    return re.sub(r'\[.*?\]', '', lyrics.text) if lyrics else None

def get_song_links(url):
    artist_html_str = get_html_str(url)

    if not artist_html_str:
        print('No artist page found')
        return []

    soup = BeautifulSoup(artist_html_str, 'lxml')
    song_links = [f"{URL_PREFIX}{link['href'][1:]}" for link in soup.find_all('a', href=True)if '/lyrics/' in link['href']]

    return song_links

def get_artist_url ():
    while True:
        artist = input('Enter the name of the artist: ').strip().lower() # ask for user input

        if artist.startswith('the '):
            artist = artist[4:]
        
        url = f"{URL_PREFIX}{artist[0]}/{artist.replace(' ', '')}.html" # url of the artist page on azlyrics
        
        try:
            html_str = get_html_str(url)
        except:
            print('No artist page found, try again\n')
            continue
        
        header = BeautifulSoup(html_str, 'lxml').find('h1')

        # all artists page have [artist name] Lyrics as the header, so we can use this to check if the artist page exists
        if not re.match(r'.+? Lyrics', header.text):
            print('No artist page found, try again\n')
        else:
            return url

def get_num_lines():
    while True:
        num_lines = input('Enter the number of lines of lyrics you want to generate: ')
        
        if not num_lines or not num_lines.isdigit():
            print('Invalid input. Try again. ')
        else:
            return int(num_lines)

def get_user_input ():
    return get_artist_url(), get_num_lines()

def generate_markov_lines(num_lines, file_name = "lyrics.txt"):
    with open(file_name, 'r', encoding='utf-8') as file:
        text = file.read()

        if not text:
            print('No lyrics found.')
            return

    markovifyTextModel = markovify.Text(text)

    for i in range(num_lines):
        line = markovifyTextModel.make_sentence()
        print(line)

def write_lyrics_file(url, file_name = "lyrics.txt"):
    song_links = get_song_links(url)

    if not song_links:
        print('No songs found')
        return

    print('Number of songs found: ', len(song_links))

    with open('lyrics.txt', 'w', encoding='utf-8') as lyrics_original:
        for x in alive_it(song_links, spinner=None):
            lyrics = get_lyrics(x)
            if not lyrics:
                continue
            lyrics_original.write(lyrics)
            sleep (random.randint(2, 10)) # sleep for a random amount of time between 2 and 7 seconds to avoid ban from azlyrics

start_time = time.time() # start time of the program

url, num_lines = get_user_input()
write_lyrics_file(url)
generate_markov_lines(num_lines)

print("--- %s seconds---" % round(time.time() - start_time, 2)) # print the time it took to run the program
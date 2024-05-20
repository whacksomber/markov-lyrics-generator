import requests
import re
from time import sleep # needed to avoid ban from alyrics
from fake_useragent import UserAgent # also needed to avoid ban from azlyrics
import random
import time
from alive_progress import alive_it
import markovify
from bs4 import BeautifulSoup

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

    if not html_str:
        print(f'No lyrics page found for: {url}')
        return None
    
    soup = BeautifulSoup(html_str, 'lxml')
    lyrics = soup.find('div', class_="col-xs-12 col-lg-8 text-center").find(lambda tag: tag.name == 'div' and not tag.attrs)
    return re.sub(r'\[.*?\]', '', lyrics.text)

def get_song_links(url):
    artist_html_str = get_html_str(url)

    if not artist_html_str:
        print('No artist page found')
        return []

    soup = BeautifulSoup(artist_html_str, 'lxml')
    
    song_links = [f"https://www.azlyrics.com{link['href']}" for link in soup.find_all('a', href=True)if '/lyrics/' in link['href']]

    return song_links

def get_user_input ():
    while True:
        artist = input('Enter the name of the artist: ').strip() # ask for user input

        # if artist starts with the, remove it
        if artist.lower().startswith('the '):
            artist = artist[4:]
        
        url = f"https://www.azlyrics.com/{artist[0].lower()}/{artist.lower().replace(' ', '')}.html" # url of the artist page on azlyrics

        header = BeautifulSoup(get_html_str(url), 'lxml').find('h1')

        # check if h2 = ... lyrics using regex
        if not re.match(r'.+? Lyrics', header.text):
            print('No artist page found, try again\n')
        else:
            return url

def generate_markov_lines(num_lines, file_name = "lyrics.txt"):
    with open(file_name, 'r') as file:
        text = file.read()

        if text == '':
            print('No lyrics found.')
            exit()

    markovifyTextModel = markovify.Text(text)

    for i in range(num_lines):
        line = markovifyTextModel.make_sentence()
        print(line)

def write_lyrics_file(url, file_name = "lyrics.txt"):
    with open('lyrics.txt', 'w', encoding='utf-8') as lyrics_original:
        song_links = get_song_links(url)

        if song_links == []:
            print('No songs found')
            exit()

        print('Number of songs found: ', len(song_links))

        for x in alive_it(song_links):
            lyrics = get_lyrics(x)
            if not lyrics:
                continue
            lyrics_original.write(lyrics)
            sleep (random.randint(2, 10)) # sleep for a random amount of time between 2 and 10 seconds to avoid ban from azlyrics

start_time = time.time() # start time of the program

url = get_user_input()
num_lines = int(input('Enter the number of lines of lyrics you want to generate: '))
write_lyrics_file(url)
generate_markov_lines(num_lines)

print("--- %s seconds ---" % round(time.time() - start_time, 2)) # print the time it took to run the program
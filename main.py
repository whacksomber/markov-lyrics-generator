import urllib.request
import urllib.error
import re
from time import sleep # needed to avoid ban from alyrics
from fake_useragent import UserAgent # also needed to avoid ban from azlyrics
import random
import time

disclaimer = "Usage of azlyrics.com content by any third-party lyrics provider is prohibited by our licensing agreement. Sorry about that. -->"

url = "https://www.azlyrics.com/c/cure.html" # url of the artist page on azlyrics

def get_html_str (url):
    try:
        # use a random user agent to avoid ban from azlyrics
        req = urllib.request.Request(url, headers={'User-Agent': UserAgent().random})
        html = urllib.request.urlopen(req)
        htmlstr = str(html.read())
        return htmlstr
    except urllib.error.HTTPError as e:
        print("ERROR: ", e.code)
        return None

def get_lyrics (url):
    html_str = get_html_str(url)

    # if none is returned, return None
    if html_str == None:
        return None

    split = html_str.split(disclaimer,1)
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

start_time = time.time() # start time of the program

lyrics_original = open('lyrics.txt', 'w') # open a file to write the lyrics to

artist_html_str = get_html_str(url)

if artist_html_str == None:
    exit()

# get all the links to the songs of the artist
song_links = re.findall('href="([^"]*lyrics/cure[^"]*)"', artist_html_str)
song_links = list(map(lambda x: "https://www.azlyrics.com" + x, song_links))

for i, x in enumerate(song_links):
    lyrics = get_lyrics(x)
    if lyrics == None:
        continue
    lyrics_original.write(lyrics)
    print(round(i / len(song_links) * 100, 2), "%", end='\r') # print the percentage of songs whose lyrics have been downloaded
    sleep (random.randint(2, 15)) # sleep for a random amount of time between 2 and 15 seconds to avoid ban from azlyrics

lyrics_original.close() # close the file

print("--- %s seconds ---" % round(time.time() - start_time, 2)) # print the time it took to run the program
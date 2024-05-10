import urllib.request
import re
from time import sleep # needed to avoid ban from alyrics
import random

lyrics_original = open('lyrics.txt', 'w')

url = "https://www.azlyrics.com/c/cure.html"

def get_html_str (url):
    html = urllib.request.urlopen(url)
    htmlstr = str(html.read())
    return htmlstr

artist_html_str = get_html_str(url)

links = re.findall('href="([^"]+)"', artist_html_str)

songLinks = []

for x in links:
    if "lyrics/cure" in x:
        x = "https://www.azlyrics.com" + x
        songLinks.append(x)

disclaimer = "Usage of azlyrics.com content by any third-party lyrics provider is prohibited by our licensing agreement. Sorry about that. -->"

i = 0

for x in songLinks:
    song_html_str = get_html_str(x)
    
    split = song_html_str.split(disclaimer,1)
    split_html = split[1] #get everything after the disclaimer
    split = split_html.split('</div>',1) #get everything before the end of the lyrics
    lyrics = split[0]
    lyrics = lyrics.replace('<br>', '\n')
    lyrics = lyrics.replace('\\', '')
    lyrics = lyrics.replace('\nn', '\n')
    lyrics = lyrics.replace('\r', '')
    lyrics = lyrics.replace('<i>', '')
    lyrics = lyrics.replace('</i>', '')
    lyrics = lyrics.replace('[Chorus]', '')
    lyrics_original.write(lyrics)
    i += 1
    print(round(i / len(songLinks) * 100, 2), "%", end='\r')
    sleep (random.randint(2, 15)) #sleep for a random amount of time between 2 and 10 seconds to avoid ban from azlyrics
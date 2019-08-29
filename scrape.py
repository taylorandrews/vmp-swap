import pandas as pd
import json
import sys
import os
from urllib.parse import *
import oauth2 as oauth
from pprint import pprint
import requests
from lxml import html
# from selenium import webdriver
import time


def define_variables(secrets):
    # define secrets
    consumer_key = secrets['consumer_key']
    consumer_secret = secrets['consumer_secret']
    authorize_url = secrets['authorize_url']
    request_token_url = secrets['request_token_url']
    access_token_url = secrets['access_token_url']
    user_agent = secrets['user_agent']
    oauth_access_token = secrets['oauth_access_token']
    oauth_access_token_secret = secrets['oauth_access_token_secret']
    # use secrets, establish connection
    consumer = oauth.Consumer(consumer_key, consumer_secret)
    client = oauth.Client(consumer)

    return consumer, client, authorize_url, request_token_url, access_token_url, user_agent, oauth_access_token, oauth_access_token_secret

def get_token(client, token_url, user_agent):
    resp, content = client.request(token_url, 'POST', headers={'User-Agent': user_agent})
    return resp, content

def access_token_run_once(consumer, authorize_url, request_token, access_token_url, user_agent):
    print('Go here and copy token: {0}?oauth_token={1}'.format(authorize_url, request_token['oauth_token']))
    oauth_verifier = input('Verification code > ')
    token = oauth.Token(request_token['oauth_token'], request_token['oauth_token_secret'])
    token.set_verifier(oauth_verifier)
    client = oauth.Client(consumer, token)
    access_resp, access_content = get_token(client, access_token_url, user_agent)
    access_token = dict(parse_qsl(access_content))
    access_token = {key.decode('utf-8'): value.decode('utf-8') for (key, value) in access_token.items()}

    # print(' == Access Token ==')
    # print('    * oauth_token        = {0}'.format(access_token['oauth_token']))
    # print('    * oauth_token_secret = {0}'.format(access_token['oauth_token_secret']))
    # print(' Authentication complete. Future requests must be signed with the above tokens.')

    return access_token

def get_ready(secrets):
    consumer, client, authorize_url, request_token_url, access_token_url, user_agent, oauth_access_token, oauth_access_token_secret = define_variables(secrets)

    # get response tokens
    request_resp, request_content = get_token(client, request_token_url, user_agent)
    if request_resp['status'] != '200':
        sys.exit('Invalid response {0}.'.format(request_resp['status']))
    request_token = dict(parse_qsl(request_content))
    request_token = {key.decode('utf-8'): value.decode('utf-8') for (key, value) in request_token.items()}

    # get access tokens - these are now pasted in secrets.json
    if oauth_access_token == '':
        access_token = access_token_run_once(consumer, authorize_url, request_token, access_token_url, user_agent)
    else:
        pass

    return consumer, request_token, oauth_access_token, oauth_access_token_secret, user_agent

def url_ready(words):
    words_mastered = words.lower().replace(' ', '+')
    return words_mastered

def get_release_id(album, artist, secrets):
    consumer, request_token, oauth_access_token, oauth_access_token_secret, user_agent = get_ready(secrets)
    token = oauth.Token(key=oauth_access_token, secret=oauth_access_token_secret)
    client = oauth.Client(consumer, token)
    album_mastered = url_ready(album)
    artist_mastered = url_ready(artist)

    # use to print discogs API call
    # print('https://api.discogs.com/database/search?release_title={}&artist={}'.format(album_mastered, artist_mastered))
    resp, content = client.request('https://api.discogs.com/database/search?release_title={}&artist={}'.format(album_mastered, artist_mastered), headers={'User-Agent': user_agent})

    releases = json.loads(content)
    vmp_copy = []
    for release in releases['results']:
        if any('Vinyl Me, Please' in label for label in release['label']):
            vmp_copy.append(release)
        elif 'series' in release.keys():
            if any('Vinyl Me, Please' in series for series in release['series']):
                vmp_copy.append(release)
    if len(vmp_copy) == 1:
        release_id = vmp_copy[0]['id']
        return release_id, 'vmp copy found'
    elif len(vmp_copy) == 0:
        print(f"vmp copy not found for '{album}' by '{artist}'")
        return 0, 'vmp copy not found'
    elif len(vmp_copy) > 1:
        print(f"multiple vmp copies found for '{album}' by '{artist}'")
        return 0, 'multiple vmp copies found'

def get_median_price(discogs_url):
    discogs_html = requests.get(discogs_url)
    tree = html.fromstring(discogs_html.content)
    median_html = tree.xpath('//*[@id="statistics"]/div/ul[2]/li[3]/text()')
    median = median_html[1].strip()[1:]

    return median

def find_prices(releases):
    records = {}
    secrets = json.load(open('secrets.json'))
    for album in releases:
        artist = releases[album]
        release_id, status = get_release_id(album, artist, secrets)
        if release_id == 0:
            pass
        else:
            discogs_url = 'http://www.discogs.com/{}-{}/release/{}'.format(artist.replace(' ', '-').lower(), album.replace(' ', '-').lower(), release_id)
            median_price = get_median_price(discogs_url)
            records[f'{album} by {artist} ({discogs_url})'] = median_price

    for record in sorted(records.items(), key=lambda x: x[1], reverse=True):
        print(f"${record[1]} -- {record[0]}")  #" -- {records[price]}")

    return records

def get_releases_lxml(vmp_url, tries=1):
    vmp_html = requests.get(vmp_url)
    tree = html.fromstring(vmp_html.content)
    print(tree)
    releases = {}
    for n in range(tries):
        artist_raw = tree.xpath(f'//*[@id="swaps"]/div[5]/div[{n + 1}]/div/div/div/div[2]/div/div[1]/div/div[3]/text()')
        print(artist_raw)
        # //*[@id="swaps"]/div[5]/div[1]/div/div/div/div[2]/div/div[1]/div/div[3] -- swap page atrist
        # //*[@id="swaps"]/div[5]/div[2]/div/div/div/div[2]/div/div[1]/div/div[3]
        # if not artist_raw:
        #     artist_raw = tree.xpath(f'//*[@id="archive"]/div[3]/div[2]/div/div[{n + 1}]/div[2]/div[3]/div[1]/text()')
        album_raw = tree.xpath(f'//*[@id="swaps"]/div[5]/div[{n + 1}]/div/div/div/div[2]/div/div[1]/div/div[2]/text()')
        # //*[@id="swaps"]/div[5]/div[1]/div/div/div/div[2]/div/div[1]/div/div[2] -- swap page album
        # //*[@id="swaps"]/div[5]/div[2]/div/div/div/div[2]/div/div[1]/div/div[2]
        # if not album_raw:
        #     album_raw = tree.xpath(f'//*[@id="archive"]/div[3]/div[2]/div/div[{n + 1}]/div[2]/div[3]/div[2]/div/text()')
        if artist_raw:
            artist_raw[0].strip()
        else:
            print("couldn't scrape vmp for at least one record")
        if artist_raw and album_raw:
            artist = artist_raw[0].strip()
            album = album_raw[0].strip()
            releases[album] = artist
        else:
            break

    return releases

def get_releases_selenium(vmp_url, tries=1):
    driver = webdriver.Chrome('/usr/local/bin/chromedriver')
    driver.get(vmp_url)
    time.sleep(5)
    return driver

def get_releases_raw():

    releases = {'Animated Violence Mild': 'BLANCK MASS',
    'Arthur Moon': 'ARTHUR MOON',
    'Day Camp for Dreamers': 'EMONIFELA',
    'Fist City': 'LORETTA LYNN',
    'forevher': 'SHURA',
    'KingMaker': 'JOEL ROSS',
    'Low Grade Buzz': 'HUNTLY',
    'Miami Memory': 'ALEX CAMERON',
    'Mulberry Violence': 'TREVOR POWERS',
    'NEON BROWN': 'VELVET NEGRONI'}

    releases = {'North Hills': 'DAWES',
    'Out There': 'ERIC DOLPHY',
    'Salt': 'MR. TWIN SISTER',
    'Silver Eater': 'GRACE LIGHTMAN',
    'Something Like A War': 'KINDNESS',
    'The Mind of Mannie Fresh': 'MANNIE FRESH',
    "We're Not Talking": 'THE GOON SAX',
    "While I'm Livin'": 'TANYA TUCKER',
    'Your Dog': 'ROSE DROLL'}

    # releases = {'A Curious Tale of Trials + Persons': 'LITTLE SIMZ',
    # 'África Brasil': 'JORGE BEN',
    # 'All Hail The Queen': 'QUEEN LATIFAH',
    # 'Aromanticism': 'MOSES SUMNEY',
    # 'Attica Blues': 'ARCHIE SHEPP',
    # 'Be The Cowboy': 'MITSKI',
    # 'Betty Davis': 'BETTY DAVIS',
    # 'Big Bill Broonzy Sings Folk Songs': 'BIG BILL BROONZY',
    # 'Call Me': 'AL GREEN',
    # 'City Music': 'KEVIN MORBY'}
    #
    # releases = {'Classic': 'LIVING LEGENDS',
    # "Coal Miner's Daughter": 'LORETTA LYNN',
    # 'Cosmogramma': 'FLYING LOTUS',
    # 'Doggystyle': 'SNOOP DOGG',
    # 'Energy Control Center': 'THE LIGHTMEN PLUS ONE',
    # 'Fancy Free': 'DONALD BYRD',
    # 'For The Sake of the Song': 'TOWNES VAN ZANDT',
    # 'Free Yourself': 'EXPERIENCE UNLIMITED',
    # 'Go For Your Guns': 'THE ISLEY BROTHERS',
    # 'Gospel Train': 'SISTER ROSETTA THARPE'}
    #
    # releases = {'Hasabe': 'AYALEW MESFIN',
    # 'Here To Stay': 'DARRELL BANKS',
    # 'How To Be A Human Being': 'GLASS ANIMALS',
    # 'I Got What It Takes': 'KOKO TAYLOR',
    # 'Journey In Satchidananda': 'ALICE COLTRANE FEAT. PHAROAH SAN...',
    # 'Jujus Alchemy of the Blues': 'SARAH WEBSTER FABIO',
    # 'King': 'T.I.',
    # 'Knock On Wood': 'EDDIE FLOYD',
    # 'Laugh To Keep From Crying': 'NAT TURNER REBELLION',
    # 'Let It Die': 'FEIST'}
    #
    # releases = {'Long Way Home': 'LåPSLEY',
    # 'Lord Willin': 'CLIPSE',
    # 'MASSEDUCTION': 'ST VINCENT',
    # 'Mavis Staples': 'MAVIS STAPLES',
    # 'Nasty': 'RICO NASTY',
    # 'Overgrown': 'IVY SOLE',
    # 'Return To Cookie Mountain': 'TV ON THE RADIO',
    # 'Silver Bullets': 'THE SILVERTONES',
    # 'Soul Makossa': 'LAFAYETTE AFRO ROCK BAND',
    # 'Soul of a Bell': 'WILLIAM BELL'}
    #
    # releases = {'Spaces': 'NILS FRAHM',
    # 'TA13OO': 'DENZEL CURRY',
    # 'Tha Carter III': 'LIL WAYNE',
    # "The Center Won't Hold": 'SLEATER-KINNEY',
    # 'The Lemon of Pink': 'THE BOOKS',
    # 'The Lost Paramount Tapes': 'JAMES BOOKER',
    # 'Unapologetic Art Rap': 'OPEN MIKE EAGLE'}
    #
    # releases = {'Uno Dos Tres 1•2•3': 'WILLIE BOBO',
    # 'Uptown Saturday Night': 'CAMP LO',
    # 'Veedon Fleece': 'VAN MORRISON',
    # 'Waiting For Little Milton': 'LITTLE MILTON',
    # 'Watch Out!': 'WELLS FARGO',
    # 'Wolfgang Amadeus Phoenix': 'PHOENIX',
    # 'Yours Conditionally': 'TENNIS'}

    return releases

if __name__ == '__main__':
    # vmp_url = 'https://app.vinylmeplease.com/records_of_the_month'
    vmp_url = 'https://app.vinylmeplease.com/profile/swaps/1869'
    tries = 8
    # releases = get_releases_selenium(vmp_url, tries)
    # releases = get_releases_lxml(vmp_url, tries)
    releases = get_releases_raw()

    records = find_prices(releases)

    # TODO: compare releases dict with number of tries to make sure nothing errors silently!
    #
    # Bug: `tries` maxes out at how many albums can load on the vmp page

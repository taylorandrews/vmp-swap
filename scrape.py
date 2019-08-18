import pandas as pd
import json
import sys
import os
from urllib.parse import *
import oauth2 as oauth
from pprint import pprint
import requests
from lxml import html
from selenium import webdriver
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
    words.replace(' ', '+')
    return words

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
        if any('Vinyl Me, Please' in lable for lable in release['label']):
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
    vmp_html =  requests.get(vmp_url)
    tree = html.fromstring(vmp_html.content)
    releases = {}
    for n in range(tries):
        artist_raw = tree.xpath(f'//*[@id="archive"]/div[3]/div[2]/div/div[{n + 1}]/div/div[3]/div[1]/text()')
        if not artist_raw:
            artist_raw = tree.xpath(f'//*[@id="archive"]/div[3]/div[2]/div/div[{n + 1}]/div[2]/div[3]/div[1]/text()')
        album_raw = tree.xpath(f'//*[@id="archive"]/div[3]/div[2]/div/div[{n + 1}]/div/div[3]/div[2]/a/text()')
        if not album_raw:
            album_raw = tree.xpath(f'//*[@id="archive"]/div[3]/div[2]/div/div[{n + 1}]/div[2]/div[3]/div[2]/div/text()')
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

if __name__ == '__main__':
    vmp_url = 'https://app.vinylmeplease.com/records_of_the_month'
    tries = 20
    releases = get_releases_selenium(vmp_url, tries)
    # records = find_prices(releases)

    # TODO: compare releases dict with number of tries to make sure nothing errors silently!
    #
    # Bug: `tries` maxes out at how many albums can load on the vmp page

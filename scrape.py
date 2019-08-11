import pandas as pd
import json
import sys
from urllib.parse import *
import oauth2 as oauth
from pprint import pprint


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

    # print(' == Request Token == ')
    # print('    * oauth_token        = {0}'.format(request_token['oauth_token']))
    # print('    * oauth_token_secret = {0}'.format(request_token['oauth_token_secret']))

    # get access tokens - these are now pasted in secrets.json
    if oauth_access_token == '':
        access_token = access_token_run_once(consumer, authorize_url, request_token, access_token_url, user_agent)
    else:
        # print(' == Access Token ==')
        # print('    * oauth_token        = {0}'.format(oauth_access_token))
        # print('    * oauth_token_secret = {0}'.format(oauth_access_token_secret))
        # print(' Authentication complete. Future requests must be signed with the above tokens.')
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

    resp, content = client.request('https://api.discogs.com/database/search?release_title={}&artist={}'.format(album_mastered, artist_mastered), headers={'User-Agent': user_agent})

    if resp['status'] != '200':
        sys.exit('Invalid API response {0}.'.format(resp['status']))

    releases = json.loads(content)
    vmp_copy = []
    for release in releases['results']:
        if any('Vinyl Me, Please' in lable for lable in release['label']):
            vmp_copy.append(release)
    if len(vmp_copy) == 1:
        release_id = vmp_copy[0]['id']
        return release_id, 'vmp copy found'
    elif len(vmp_copy) == 0:
        return None, 'vmp copy not found'
    elif len(vmp_copy) > 1:
        return None, 'multiple vmp copies found'


if __name__ == '__main__':
    album = 'Left My Blues In San Francisco'
    artist = 'Buddy Guy'
    secrets = json.load(open('secrets.json'))
    release_id, status = get_release_id(album, artist, secrets)
    if release_id:
        print(' {} here:\n discogs.com/{}-{}/release/{}'.format(status, artist.replace(' ', '-').lower(), album.replace(' ', '-').lower(), release_id))
    else:
        print(status)

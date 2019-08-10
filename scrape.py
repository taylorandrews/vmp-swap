import pandas as pd
import json
import sys
from urllib.parse import urlparse
import oauth2 as oauth
from pprint import pprint


def define_variables(secrets):
    # define secrets
    consumer_key = secrets['consumer_key']
    consumer_secret = secrets['consumer_secret']
    request_token_url = secrets['request_token_url']
    authorize_url = secrets['authorize_url']
    access_token_url = secrets['access_token_url']
    user_agent = secrets['user_agent']
    # use secrets, establish connection
    consumer = oauth.Consumer(consumer_key, consumer_secret)
    client = oauth.Client(consumer)
    resp, content = client.request(request_token_url, 'POST', headers={'User-Agent': user_agent})
    return consumer, client, resp, content

def simple_request(secrets):
    consumer, client, resp, content = define_variables(secrets)
    if resp['status'] != '200':
        sys.exit('Invalid response {0}.'.format(resp['status']))

    request_token = dict(urlparse(content))
    print(resp)

    print(' == Request Token == ')
    print('    * oauth_token        = {0}'.format(request_token['oauth_token']))
    print('    * oauth_token_secret = {0}'.format(request_token['oauth_token_secret']))

if __name__ == '__main__':
    secrets = json.load(open('secrets.json'))
    # consumer, client, resp, content = define_variables(secrets)
    simple_request(secrets)

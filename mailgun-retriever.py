import urllib.parse
import requests  
import datetime
import pprint
import json
import sys
import mailbox
import argparse
import getpass
import time
import pickle
import os

from colorama import Fore, Back, Style

class Mailgun(object):
    def __init__(self, domain, key):
        self.apitop = "https://api.mailgun.net/v3/{}/".format(domain)
        self.apikey = ("api", key)
        self.domain = domain

    def apiurl(self, api):
        return urllib.parse.urljoin(self.apitop, api)

    def messages(self, raw=False, begin=0):
        headers = {}
        if raw:
            headers['Accept'] = 'message/rfc2822'
        resp = requests.get(self.apiurl("events"), auth=self.apikey, params={
            'ascending': 'yes',
            'begin': begin,
            'event': 'stored'
        })
        done = set()
        if resp.status_code == 200:
            data = resp.json()
            while data['paging']['next'] != data['paging']['last']:
                for event in data['items']:
                    content = requests.get(event['storage']['url'], auth=self.apikey, headers=headers)
                    if resp.status_code == 200:
                        tmp = content.json()
                        if 'Message-Id' in tmp and tmp['Message-Id'] not in done:
                            done.add(tmp['Message-Id'])
                            yield {'event': event, 'message': tmp}
                resp = requests.get(data['paging']['next'])
                if resp.status_code != 200:
                    break
                data = resp.json()

def main(args):
    cachefile = os.path.join(args.maildir, '.mailcache')
    begintime = time.time()
    mailgun = Mailgun(args.domain, args.apikey)

    if os.path.isfile(cachefile):
        with open(cachefile, 'rb') as fp:
            seen = pickle.load(fp)
    else:
        seen = {'last': 0.0, 'messages': set()}

    mdir = mailbox.Maildir(args.maildir)
    print((Fore.WHITE + '[+] Retrieving messages for domain {}' + Style.RESET_ALL).format(args.domain))
    for idx, item in enumerate(mailgun.messages(raw=True, begin=seen['last'])):
        if item['event']['timestamp'] > seen['last']:
            seen['last'] = item['event']['timestamp']

        if args.limit != None and idx >= args.limit:
            print(Fore.WHITE + '[+] Message download limit reached, exiting' + Style.RESET_ALL)
            break

        if item['message']['Message-Id'] not in seen['messages']:
            print((Fore.CYAN + '> {}' + Style.RESET_ALL).format(item['message']['subject']))
            mdir.add(item['message']['body-mime'].encode('utf-8'))
            seen['messages'].add(item['message']['Message-Id'])
    print((Fore.WHITE + '[+] Download completed in {}s' + Style.RESET_ALL).format(time.time() - begintime))

    with open(cachefile, 'wb') as fp:
        pickle.dump(seen, fp)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Save stored mailgun messages to maildir')
    parser.add_argument('-m', '--maildir', metavar='DIRECTORY', required=True,
                        help='mail directory used to save messages to')
    parser.add_argument('-d', '--domain', metavar='DOMAIN', required=True,
                        help='mailgun domain to retrieve message from')
    parser.add_argument('-k', '--apikey', metavar='KEY', required=False,
                        help='mailgun api key used for authentication')
    parser.add_argument('-l', '--limit', metavar='COUNT', required=False, type=int,
                        help='limit the number of downloaded messages')

    args = parser.parse_args()

    if args.apikey == None:
        args.apikey = getpass.getpass((Fore.WHITE + '[+] Please enter the API key for domain {}:' + Style.RESET_ALL).format(args.domain))
    main(args)

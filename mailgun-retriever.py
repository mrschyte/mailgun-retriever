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

from colorama import Fore, Back, Style

class Mailgun(object):
    def __init__(self, domain, key):
        self.apitop = "https://api.mailgun.net/v2/{}/".format(domain)
        self.apikey = ("api", key)
        self.domain = domain

    def apiurl(self, api):
        return urllib.parse.urljoin(self.apitop, api)

    def events(self, raw=False):
        headers = {}
        if raw:
            headers['Accept'] = 'message/rfc2822'
        resp = requests.get(self.apiurl("events"), auth=self.apikey)
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
                            yield tmp
                resp = requests.get(data['paging']['next'])
                if resp.status_code != 200:
                    break
                data = resp.json()

def longest_common_substring(s1, s2):
    m = [[0] * (1 + len(s2)) for i in range(1 + len(s1))]
    longest, x_longest = 0, 0
    for x in range(1, 1 + len(s1)):
        for y in range(1, 1 + len(s2)):
            if s1[x - 1] == s2[y - 1]:
                m[x][y] = m[x - 1][y - 1] + 1
                if m[x][y] > longest:
                    longest = m[x][y]
                    x_longest = x
            else:
                m[x][y] = 0
    return s1[x_longest - longest: x_longest]

def unique_lines(text, fudge=0.3):
    output = ''
    count = 1

    lines = text.split('\n')
    lines.append('')
    lprev = lines[0]

    for line in lines[1:]:
        s = longest_common_substring(lprev, line)
        if abs(len(s) - len(line)) <= len(line) * fudge:
            count = count + 1
        else:
            output += (Fore.GREEN + '{0: <8}' + Style.RESET_ALL + '{1}\n').format(count, lprev)
            count = 1
        lprev = line
    return output

def main(args):
    m = Mailgun(args.domain, args.apikey)
    b = time.time()
    mdir = mailbox.Maildir(args.maildir)
    print((Fore.WHITE + '[+] Retrieving messages for domain {}' + Style.RESET_ALL).format(args.domain))
    for idx, event in enumerate(m.events(True)):
        if args.limit != None and idx >= args.limit:
            print(Fore.WHITE + '[+] Message download limit reached, exiting' + Style.RESET_ALL)
            break
        print((Fore.CYAN + '> {}' + Style.RESET_ALL).format(event['subject']))
        mdir.add(event['body-mime'].encode('utf-8'))
    print((Fore.WHITE + '[+] Download completed in {}s' + Style.RESET_ALL).format(time.time() - b))

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

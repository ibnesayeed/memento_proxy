"""
Croatian web archive proxy
"""


import re
import urllib
from memento_proxy import *
import requests


__author__="aalsum"
__date__ ="$Mar 6, 2013 12:07:59 PM$"

baseuri = "http://haw.nsk.hr/json.php?"


class CrHandler(MementoProxy):

    def __init__(self, env, start_response):
        MementoProxy.__init__(self)
        self._env = env
        self._start_response = start_response

    def fetch_changes(self, req_url, dt=None):
        # implement the changes list for this particular proxy

        parameters = {}
        parameters['q'] = req_url
        parameters['subject'] = 'url'

        uri = baseuri + urllib.urlencode(parameters)
        jsonobj = None
        try:
            jsonobj = requests.get(uri).json()
        except Exception as e:
            print e
            return None

        changes = []

        if int(jsonobj['availableHits']) == 0:
            return changes

        tmid = jsonobj['hits'][0]['ID']
        tmuri = "http://haw.nsk.hr/publikacija/"+tmid

        data = None
        try:
            data = requests.get(tmuri).content
        except:
            return None

        uriRegex =re.compile( r'<tr><td>[\d]*\.</td>.*</tr>')
        dtregex = re.compile('<td>\d\d\.\d\d\.\d\d\d\d[0-9\.:\s]*</td>')

        uris = re.findall(uriRegex, data)
        for u in uris:
            #print u
            d = u.index("title")
            loc = "http://haw.nsk.hr/"+u[45:d-2]

            result = dtregex.search( u)
            if result:
               dtstr = result.group(0)
            dtstr= dtstr[4:-5]

            dtstr=dtstr[6:10]+dtstr[3:5]+dtstr[0:2]+dtstr[11:19].replace(":", "") + " GMT"
            dtobj = dateparser.parse(dtstr)
            changes.append((dtobj, loc, {'last': dtobj, 'obs': 1}))

        return changes


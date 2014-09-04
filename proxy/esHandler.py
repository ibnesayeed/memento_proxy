"""
Memento proxy for Estonia Web Archive
TODO: rewrite regex html parsing(?) with lxml
"""
import re
import requests


from memento_proxy import *


__author__ = "aalsum"
__date__ = "$Dec 3, 2013 2:35:11 PM$"

BASEURI = "http://veebiarhiiv.digar.ee/a/*/"


class EsHandler(MementoProxy):

    def __init__(self, env, start_response):
        MementoProxy.__init__(self)
        self._env = env
        self._start_response = start_response

    def fetch_changes(self, req_url, dt=None):
        # implement the changes list for this particular proxy

        uri = BASEURI + req_url
        data = None
        try:
            resp = requests.get(uri)
            data = resp.content
        except:
            return
        regex = r'<a onclick="SetAnchorDate\(\'(.*)\'\);" href="(.*)">'
        uriRegex = re.compile(regex)

        changes = []
        uris = re.findall(uriRegex, data)
        for u in uris:
            dtstr = u[0]
            loc = u[1]
            dtstr += " GMT"
            dtobj = dateparser.parse(dtstr)
            changes.append((dtobj, loc, {'last': dtobj, 'obs': 1}))

        return changes

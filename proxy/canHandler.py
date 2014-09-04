"""
Canadian archive proxy.
"""

import urllib
import StringIO
from lxml import etree
from memento_proxy import *

__author__ = "Robert Sanderson"

baseuri = "http://www.collectionscanada.gc.ca/webarchives/*/"


class CanHandler(MementoProxy):

    def __init__(self, env, start_response):
        MementoProxy.__init__(self)
        self._env = env
        self._start_response = start_response

    def fetch_changes(self, req_url, dt=None):

        iauri = baseuri + req_url
        dom = self.get_xml(iauri, html=True)

        alist = dom.xpath('//div[@class="inner-content"]//a')
        if not alist:
            return

        changes = []
        for a in alist:
            if "name" in a.attrib:
                continue
            dtobj = dateparser.parse(a.text + " 00:00:00 GMT")
            loc = a.attrib['href']
            info = {'last': dtobj, 'obs': 1}
            changes.append((dtobj, loc, info))
        return changes

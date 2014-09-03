# Memento proxy for Portuguese Web Archive arquivo.pt

from lxml import etree
from memento_proxy import *


__author__="aalsum"
__date__ ="$Mar 6, 2013 9:03:14 PM$"

baseuri = "http://arquivo.pt/wayback/wayback/xmlquery?type=urlquery&url="


class PoHandler(MementoProxy):

    def __init__(self, env, start_response):
        MementoProxy.__init__(self)
        self._env = env
        self._start_response = start_response

    def fetch_changes(self, req_url, dt=None):
        # implement the changes list for this particular proxy
        param = {}
        param['url'] = req_url
        param['type'] = 'urlquery'

        uri = baseuri + req_url
        dom = None
        try:
            dom = self.get_xml(uri)
        except:
            return None

        changes = []

        rlist = dom.xpath('/wayback/results/result')
        for a in rlist:

            dtstr = a.xpath('./capturedate/text()')[0]
            url = a.xpath('./url/text()')[0]
            loc = "http://arquivo.pt/wayback/wayback/%s/%s" % (dtstr, url)

            dtstr += " GMT"
            dtobj = dateparser.parse(dtstr)
            changes.append((dtobj, loc, {'last': dtobj, 'obs' : 1}))

        return changes


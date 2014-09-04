from lxml import etree
from memento_proxy import *

__author__ = "Robert Sanderson"

baseuri = "http://www.screenshots.com/"


class SsHandler(MementoProxy):

    def __init__(self, env, start_response):
        MementoProxy.__init__(self)
        self._env = env
        self._start_response = start_response

    def fetch_changes(self, req_url, dt=None):
        # implement the changes list for this particular proxy

        if req_url.startswith('http://'):
            req_url = req_url[7:]
        elif req_url.startswith('https://'):
            req_url = req_url[8:]

        if req_url[-1] == '/':
            req_url = req_url[:-1]
        if req_url.find('/') > -1:
            return
        
        uri = baseuri + req_url + '/'
        dom = None
        print uri
        try:
            dom = self.get_xml(uri, html=True)
        except Exception as e:
            print req_url, e
            return

        changes = []
        rlist = dom.xpath('//img')
        for a in rlist:
            if a.attrib.has_key('class') and a.attrib['class'].startswith('sliderThumb'):
                dtstr = a.attrib['name']
                loc = a.attrib['longdesc']
                dtstr += " 12:00:00 GMT"
                dtobj = dateparser.parse(dtstr)
                changes.append((dtobj, loc, {'last' : dtobj, 'obs' : 1, 'type' : 'observed'}))

        changes.sort()
        return changes

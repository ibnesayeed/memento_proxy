import urllib
import lxml.html
from memento_proxy import *

__author__ = "Robert Sanderson"

#baseuri = "http://nara-wayback-001.us.archive.org/"
baseuri = "http://webharvest.gov/"
collections = ["congress111th","congress110th","congress109th","peth04"]


class NaraHandler(MementoProxy):

    def __init__(self, env, start_response):
        MementoProxy.__init__(self)
        self._env = env
        self._start_response = start_response

    def fetch_changes(self, requri, dt=None):
        # implement the changes list for this particular proxy
        changes = []

        for collection in collections:
            uri = baseuri + collection +"/*/"+ requri
            data = None
            dom = None
            try:
                dom = self.get_xml(uri, html=True)
            except:
                return

            if dom:
                rlist = dom.xpath('//*[@class="mainBody"]')
                for td in rlist:
                    if len(td.getchildren()) > 0:
                        for a in td:
                            if a.tag == 'a':
                                loc = a.get('href')
                                if not loc.startswith(baseuri):
                                    if loc.startswith("/"):
                                        loc = baseuri + loc[1:]
                                    else:
                                        loc = baseuri + loc
                                dtstr = a.get('onclick').split("'")[1] + " GMT"
                                dtobj = dateparser.parse(dtstr)

                                if changes and changes[-1][0] == changes[-1][2]['last']:
                                    changes[-1][2]['last'] = dtobj
                                
                                if a.tail:
                                    changes.append((dtobj, loc, {'last' : dtobj, 'obs' : 1, 'type' : 'observed'}))
                                else:
                                    changes[-1][-1]['last'] = dtobj
                                    changes[-1][-1]['obs'] += 1
            changes.sort()

        return changes


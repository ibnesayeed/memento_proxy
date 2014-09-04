"""
Wikipedia proxy. Uses the wikipedia api to get the memento.
"""

__author__ = "Harihar Shankar"


import re
import string
from datetime import timedelta
from dateutil import parser as dateparser
from memento_proxy import MementoProxy, now


class WikiHandler(MementoProxy):

    def __init__(self, env, start_response):
        MementoProxy.__init__(self)
        self._env = env
        self._start_response = start_response

    def fetch_memento(self, req_url, dt=None):
        changes = []
        valid = re.compile('^(http://|https://)(.+.wikipedia.org)')
        match = valid.match(req_url)
        default_protocol = "http://"

        dtfmstr = "%Y%m%d%H%M%S"

        if match is None:
            return

        if not dt:
            dt = dateparser.parse(now())

        dt_del = timedelta(seconds=1)
        dt_next = dt + dt_del
        dt_next = dt_next.strftime(dtfmstr)
        dt = dt.strftime(dtfmstr)

        title_index = string.find(req_url, '/wiki/')
        title = req_url[title_index + 6:]

        url_list = []

        # url for getting the memento, prev
        mem_prev = "%s%s/w/api.php?format=xml&action=query&prop=revisions&rvprop=timestamp|ids|user&rvlimit=2&redirects=1&titles=%s&rvdir=older&rvstart=%s" % \
                   (default_protocol, match.groups()[1], title, dt)
        url_list.append('mem_prev')

        # url for next
        if dt_next:
            next = "%s%s/w/api.php?format=xml&action=query&prop=revisions&rvprop=timestamp|ids|user&rvlimit=2&redirects=1&titles=%s&rvdir=newer&rvstart=%s" % \
                   (default_protocol, match.groups()[1], title, dt)
            url_list.append('next')

        # url for last
        last = "%s%s/w/api.php?format=xml&action=query&prop=revisions&rvprop=timestamp|ids|user&rvlimit=1&redirects=1&titles=%s" % \
               (default_protocol, match.groups()[1], title)
        url_list.append('last')

        # url for first
        first = "%s%s/w/api.php?format=xml&action=query&prop=revisions&rvprop=timestamp|ids|user&rvlimit=1&redirects=1&rvdir=newer&titles=%s" % \
                (default_protocol, match.groups()[1], title)
        url_list.append('first')

        base = "%s%s/w/index.php?title=%s&oldid=" % (default_protocol, match.groups()[1], title)

        for url in url_list:
            revs = []
            dom = self.get_xml(vars()[url])
            try:
                revs = dom.xpath('//rev')
            except Exception:
                return

            for r in revs:
                info = {}
                try:
                    info['dcterms:creator'] = '%s%s/wiki/User:%s' % \
                                              (default_protocol, match.groups()[1], r.attrib['user'])
                except Exception:
                    pass
                info['type'] = 'valid'
                dtobj = dateparser.parse(r.attrib['timestamp'])
                info['last'] = dtobj
                # unknown usage... but likely loads
                info['obs'] = 0
                changes.append((dtobj, base + r.attrib['revid'], info))                
            
        if changes:
            changes.sort()
            changes[-1][-1]['last'] = 'now'
        return changes

    def fetch_changes(self, req_url, dt=None):
        changes = []
        valid = re.compile('^(http://|https://)(.+.wikipedia.org)')
        match = valid.match(req_url)
        defaultProtocol = "http://"

        if match is None:
            return

        titleIndex = string.find(req_url, '/wiki/')
        title = req_url[titleIndex+6:]
        # with extra info
        url = "%s%s/w/api.php?format=xml&action=query&prop=revisions&meta=siteinfo&rvprop=timestamp|ids|user&rvlimit=5000&redirects=1&titles=" % (defaultProtocol, match.groups()[1])

        # basic info
        #url = "http://en.wikipedia.org/w/api.php?format=xml&action=query&prop=revisions&meta=siteinfo&rvprop=timestamp|ids&rvlimit=500&redirects=1&titles="

        
        base = "%s%s/w/index.php?title=%s&oldid=" % (defaultProtocol, match.groups()[1], title)
        dom = self.get_xml(url + title)
        dtobj = None
        while dom is not None:
            revs = dom.xpath('//rev')
            for r in revs:
                info = {}
                try:
                    info['dcterms:creator'] = '%s%s/wiki/User:%s' % (defaultProtocol, match.groups()[1], r.attrib['user'])
                except:
                    pass
                info['type'] = 'valid'
                info['last'] = dtobj
                dtobj = dateparser.parse(r.attrib['timestamp'])
                # unknown usage... but likely loads
                info['obs'] = 0
                changes.append((dtobj, base + r.attrib['revid'], info))
            cont = dom.xpath('/api/query-continue/revisions/@rvstartid')
            if cont:
                dom = self.get_xml(url + title + "&rvstartid=" + cont[0])
            else:
                dom = None
                
        if changes:
            changes.sort()
            changes[-1][-1]['last'] = 'now'
        return changes
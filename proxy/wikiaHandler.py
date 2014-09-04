from urlparse import urlparse
import time
from datetime import datetime
from datetime import timedelta
from dateutil import parser as dateparser
from memento_proxy import MementoProxy, now


__author__ = "Robert Sanderson, Harihar Shankar"


def iso_to_dt(date):

    utz = dateparser.parse('2009-01-01 12:00:00 GMT').tzinfo
    seq = (int(date[:4]), int(date[5:7]), int(date[8:10]), int(date[11:13]),
           int(date[14:16]), int(date[17:19]), 0, 1, -1)
    return datetime.fromtimestamp(time.mktime(time.struct_time(seq)), utz)


class WikiaHandler(MementoProxy):

    def __init__(self, env, start_response):
        MementoProxy.__init__(self)
        self._env = env
        self._start_response = start_response

        self.hosts = [
                    'www.wowwiki.com',
                    'en.memory-alpha.org',
                    'wiki.ffxiclopedia.org',
                    'www.jedipedia.de'
        ]

        #if os.path.exists('wikiahosts.txt'):
        #    fh = file('wikiahosts.txt')
        #    self.hosts = fh.readlines()
        #    fh.close()
        
    def fetch_wiki_list(self):
        # plus *.wikia.com

        baseuri = "http://www.wikia.com/api.php?format=xml&action=query&list=wkdomains&wkfrom=%s&wkto=%s"
        start = 1
        step = 5000
        domains = []
        hdrs = self.hdrs
        hdrs['Host'] = "www.wikia.com"
        while True:
            uri = baseuri % (start, start + step)
            start += step
            dom = self.get_xml(uri, headers=hdrs)
            if dom is not None:
                vars = dom.xpath('//variable')
            else:
                break
            if not vars:
                break
            else:
                for v in vars:
                    d = v.attrib['domain']
                    if d.find('wikia.com') == -1:
                        domains.append(d)
        return domains

    def fetch_memento(self, req_url, dt=None):
        p = urlparse(req_url)
        host = p[1]
        upath = p[2]

        if host.find('.wikia.com') == -1 and not host in self.hosts:
            return

        (pref, title) = upath.rsplit('/', 1)
        if pref:
            # look for /wiki
            pref = pref.replace('/wiki', '')
        
        changes = []
        defaultProtocol = "http://"

        dtfmstr = "%Y%m%d%H%M%S"

        dt_next = False
        if dt is None:
            nowd = now()    
            current = dateparser.parse(nowd)
            dt = current.strftime(dtfmstr)
        else:
            dt_del = timedelta(seconds=1)
            dt_next = dt + dt_del
            dt_next = dt_next.strftime(dtfmstr)
            dt = dt.strftime(dtfmstr)

        url_list = []

        # url for getting the memento, prev
        mem_prev = "%s%s/api.php?format=xml&action=query&prop=revisions&rvprop=timestamp|ids|user&rvlimit=2&redirects=1&titles=%s&rvdir=older&rvstart=%s" % (defaultProtocol, host, title, dt)
        url_list.append('mem_prev')

        # url for next
        if dt_next:
            next = "%s%s/api.php?format=xml&action=query&prop=revisions&rvprop=timestamp|ids|user&rvlimit=2&redirects=1&titles=%s&rvdir=newer&rvstart=%s" % (defaultProtocol, host, title, dt)
            url_list.append('next')

        # url for last
        last = "%s%s/api.php?format=xml&action=query&prop=revisions&rvprop=timestamp|ids|user&rvlimit=1&redirects=1&titles=%s" % (defaultProtocol, host, title)
        url_list.append('last')

        # url for first
        first = "%s%s/api.php?format=xml&action=query&prop=revisions&rvprop=timestamp|ids|user&rvlimit=1&redirects=1&rvdir=newer&titles=%s" % (defaultProtocol, host, title)
        url_list.append('first')


        #url = url % (title, dt)
        base = "%s%s%s/index.php?title=%s&oldid=" % \
               (defaultProtocol, host, pref, title)
        dtobj = None

        hdrs = self.hdrs
        hdrs['Host'] = host

        for url in url_list:
            
            dom = self.get_xml(vars()[url], headers=hdrs)
            revs = dom.xpath('//rev')
            for r in revs:
                info = {}
                try:
                    info['dcterms:creator'] = '%s%s%s/wiki/User:%s' %\
                                              (defaultProtocol, host,
                                               pref, r.attrib['user'])
                except:
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

        # http://www.wowwiki.com/Cloth_armor              --> /api.php
        # http://dragonage.wikia.com/wiki/Morrigan        --> /api.php
        # http://memory-alpha.org/en/wiki/Fraggle_Rock    --> /en/api.php

        p = urlparse(req_url)
        host = p[1]
        upath = p[2]

        if host.find('.wikia.com') == -1 and not host in self.hosts:
            return
        
        (pref, title) = upath.rsplit('/', 1)
        if pref:
            # look for /wiki
            pref = pref.replace('/wiki', '')
        
        url = "http://%s%s/api.php?format=xml&action=query&prop=revisions&meta=siteinfo&rvprop=timestamp|ids&rvlimit=500&redirects=1&titles=%s" % (host, pref, title)

        changes = []
        base = "http://%s%s/index.php?oldid=" % (host, pref)

        headers = self.hdrs
        headers['Host'] = host
        dom = self.get_xml(url, headers=headers)
        while dom is not None:
            revs = dom.xpath('//rev')
            for r in revs:
                i = iso_to_dt(r.attrib['timestamp'])
                changes.append((i, base + r.attrib['revid'], {}))                
            cont = dom.xpath('/api/query-continue/revisions/@rvstartid')
            if cont:
                dom = self.get_xml(url + "&rvstartid=" + cont[0], headers=headers)
            else:
                dom = None                
        changes.sort()
        return changes
"""
Wikipedia proxy. Uses the wikipedia api to get the memento.
"""


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

    """
    def handle_timegate(self, req_url, acc_dt):

        nowd = now()
        current = dateparser.parse(nowd)

        changes = self.fetch_memento(req_url, dt=acc_dt)

        # Setup response information: link headers
        if changes:
            first = changes[0]
            last = changes[-1]
        else:
            first = None
            last = None

        next = None
        prev = None
        loc = None

        links = ['<%s>;rel="original"' % req_url,
                 '<%s>;rel="timemap";type="application/link-format"' % self.timemap_url]

        headers = []
        # Process Error Conditions
        if type(changes) == str:
            # Redirect to better TimeGate
            headers.append(('Location', changes))
            headers.append(('Link', '<%s>;rel="original"' % req_url))
            return self.respond(code=302,
                                msg='Redirecting to better TimeGate: %s' % changes,
                                headers=headers)
        else:
            headers.append(('Vary', 'negotiate,accept-datetime'))

            # check VERB used for GET/HEAD
            if not changes:
                msg = 'Resource not in archive<br/><i><blockquote><ul><li>Resource: ' \
                      '<b>%s</b></li></ul></blockquote></i>' % req_url
                return self.respond(code=404, msg=msg)
            elif self._env.get("REQUEST_METHOD") not in ["GET", "HEAD"]:
                # 405
                headers.append(('Allow', "GET, HEAD"))
                headers.append(('Link', self.construct_link_header(links, first, last)))
                return self.respond(msg="Only GET and HEAD allowed",
                                    code=405,
                                    headers=headers)
            elif acc_dt is None:
                headers.append(('Link', self.construct_link_header(links, first, last)))

                # XXX Body must have list of resources
                msg = "Datetime format not correct<br/><i><blockquote>\
                Expected: %s</blockquote></i>" %\
                      (current.strftime(self.date_format))
                return self.respond(msg=msg, code=400)

        if acc_dt == current or len(changes) == 1:
            # return last (or only)
            loc = last
            next = None
            prev = None
        elif acc_dt < first[0]:
            loc = first
            next = changes[1]
        elif acc_dt > last[0]:
            loc = last
            prev = changes[-1]
        else:
            # Else find closest
            for c in range(1, len(changes)):
                this = changes[c]
                if acc_dt < this[0] or c == len(changes)-1:
                    llast = changes[c-1]
                    loc = llast
                    if (c-2 >= 0):
                        prev = changes[c-2]
                    next = this
                    break
                    
        headers.append(('Link', self.construct_link_header(links, first, last, loc, next, prev)))
        headers.append(('Location', loc[1]))
        return self.respond(code=302, headers=headers)
    """

    def fetch_memento(self, req_url, dt=None):
        changes = []
        valid = re.compile('^(http://|https://)(.+.wikipedia.org)')
        match = valid.match(req_url)
        default_protocol = "http://"

        dtfmstr = "%Y%m%d%H%M%S"

        if match is None:
            return changes

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
                return self.respond(code=500, msg="Response from %s unparsable." % req_url)

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
            return changes

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
                try: info['dcterms:creator'] = '%s%s/wiki/User:%s' % (defaultProtocol, match.groups()[1], r.attrib['user'])
                except: pass
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
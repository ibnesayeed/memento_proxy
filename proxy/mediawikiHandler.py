# Version 3:  Rewrite to use Wikimedia API, rather than HTML scraping

from datetime import timedelta
import urlparse
from dateutil import parser as dateparser
from memento_proxy import MementoProxy, now

__author__ = "Harihar Shankar"

class MediawikiHandler(MementoProxy):

    def __init__(self, env, start_response):
        MementoProxy.__init__(self)
        self._env = env
        self._start_response = start_response

    # Overrides the baseHandler function
    # does the work of a timegate

    def fetch_memento(self, req_url, dt=None):
        changes = []
        if req_url.startswith("//"):
            req_url = req_url.replace("//", "http://")

        #valid = re.compile('^(http://|https://)(.+)')
        #match = valid.match(requri)
        #defaultProtocol = "http://"

        dtfmstr = "%Y%m%d%H%M%S"

        parsed_url = urlparse.urlparse(req_url)

        headers = self.hdrs
        headers['Host'] = parsed_url[1]

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

        title = None
        api_base_url = None
        try:
            title = urlparse.parse_qs(parsed_url[4]).get('title')
        except:
            pass
        
        try:
            dom = self.get_xml(req_url, headers=headers, html=True)
        except Exception as e:
            return

        links = dom.xpath("//link")
        for link in links:
            if link.attrib['rel'].lower() == "edituri":
                api_base_url = link.attrib['href'].split("?")[0]
                if api_base_url.startswith("//"):
                    api_base_url = api_base_url.replace("//", "http://")

        if not title:
            url_parts = req_url.split("/")
            title = url_parts[len(url_parts) - 1].split("?")[0]

        url_list = []

        # url for getting the memento, prev
        mem_prev = "%s?format=xml&action=query&prop=revisions&rvprop=timestamp|ids|user&rvlimit=2&redirects=1&titles=%s&rvdir=older&rvstart=%s" % (api_base_url, title, dt)
        url_list.append('mem_prev')

        # url for next
        if dt_next:
            next = "%s?format=xml&action=query&prop=revisions&rvprop=timestamp|ids|user&rvlimit=2&redirects=1&titles=%s&rvdir=newer&rvstart=%s" % (api_base_url, title, dt)
            url_list.append('next')

        # url for last
        last = "%s?format=xml&action=query&prop=revisions&rvprop=timestamp|ids|user&rvlimit=1&redirects=1&titles=%s" % (api_base_url, title)
        url_list.append('last')

        # url for first
        first = "%s?format=xml&action=query&prop=revisions&rvprop=timestamp|ids|user&rvlimit=1&redirects=1&rvdir=newer&titles=%s" % (api_base_url, title)
        url_list.append('first')

        base = "%s?title=%s&oldid=" % (api_base_url.replace("api.php", "index.php"), title)
        dtobj = None

        for url in url_list:
            dom = None
            try:
                dom = self.get_xml(vars()[url])
            except Exception as e:
                pass
            if not dom:
                continue
            dom = dom.getroot()
            revs = dom.xpath('//rev')
            for r in revs:
                info = {}
                try:
                    info['dcterms:creator'] = '%s/wiki/User:%s' %\
                                              (api_base_url, r.attrib['user'])
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
        #self.fetch_memento( req, requri, dt )
        changes = []
        if req_url.startswith("//"):
            req_url = req_url.replace("//", "http://")

        #valid = re.compile('^(http://|https://)(.+)')
        #match = valid.match(requri)
        #defaultProtocol = "http://"

        dtfmstr = "%Y%m%d%H%M%S"

        parsed_url = urlparse.urlparse(req_url)

        headers = self.hdrs
        headers['Host'] = parsed_url[1]

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

        title = None
        api_base_url = None
        try:
            title = urlparse.parse_qs(parsed_url[4]).get('title')
        except:
            pass

        try:
            dom = self.get_xml(req_url, headers=headers, html=True)
        except Exception as e:
            return

        links = dom.xpath("//link")
        for link in links:
            if link.attrib['rel'].lower() == "edituri":
                api_base_url = link.attrib['href'].split("?")[0]
                if api_base_url.startswith("//"):
                    api_base_url = api_base_url.replace("//", "http://")

        if not title:
            url_parts = req_url.split("/")
            title = url_parts[len(url_parts) - 1].split("?")[0]

        # with extra info
        url = "%s?format=xml&action=query&prop=revisions&meta=siteinfo&rvprop=timestamp|ids|user&rvlimit=5000&redirects=1&titles=%s"\
              % (api_base_url, title)

        base = "%s?title=%s&oldid=" % (api_base_url.replace("api.php", "index.php"), title)
        dom = self.get_xml(url)
        dtobj = None
        while dom is not None:
            revs = dom.xpath('//rev')
            for r in revs:
                info = {}
                try:
                    info['dcterms:creator'] = '%s/wiki/User:%s' % \
                                              (api_base_url, r.attrib['user'])
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
                dom = self.get_xml(url + "&rvstartid=" + cont[0])
            else:
                dom = None
                
        if changes:
            changes.sort()
            changes[-1][-1]['last'] = 'now'
        return changes

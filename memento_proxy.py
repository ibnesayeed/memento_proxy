"""
The base class containing all common methods that the proxies inherit.
"""

import os
import time
from dateutil import parser as dateparser
from ConfigParser import ConfigParser, NoOptionError, NoSectionError
import requests
from lxml import etree
import StringIO

__author__ = "Harihar Shankar"


HTTP_STATUS_CODE = {
    200: "OK",
    204: "No Content",
    302: "Found",
    400: "Bad Request",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    406: "Not Acceptable",
    409: "Conflict",
    500: "Unexpected server error",
}


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class MementoProxy:
    """
    The base class.
    """

    def __init__(self):

        self._env = None
        self._start_response = None
        self.host_name = None
        self.path = None
        self.timegate_url_part = None
        self.timemap_url_part = None
        self.proxy_part = None
        self.timegate_url = None
        self.timemap_url = None
        self.proxies = {}
        self.load_config_params()

        self.date_format = "%a, %d %b %Y %H:%M:%S GMT"
        self.error_tmpl = """<html>
        <body><br/><center><table width='800px'>
        <tr><td>
        <div style='background-color: #e0e0e0; padding: 10px;'><br/>
        <center><b>Error: %s</b></center>%s<br/><br/>
        </div></td></tr></table></center>
        </body></html>
        """
        self.hdrs = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
            'Proxy-Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            'User-Agent': 'Mozilla/5.0 \
            (Macintosh; U; Intel Mac OS X 10.5; en-US; rv:1.9.1.2) Gecko/20090729 Firefox/3.5.2'
        }

    def load_config_params(self):
        """
        Reads config information from the file.
        :return: None
        """
        conf_file = []
        conf_file.append(os.path.join(os.path.dirname(__file__),
                                      "conf/proxy.conf"))
        conf = ConfigParser()
        conf.read(conf_file)
        if not conf:
            raise IOError("Unable to read config file.")
        try:
            self.host_name = conf.get("setup", "host_name")
            self.path = conf.get("setup", "path")
            self.timegate_url_part = conf.get("setup", "timegate_url_part")
            self.timemap_url_part = conf.get("setup", "timemap_url_part")
            self.timemap_link_url_part = conf.get("setup", "timemap_link_url_part")
            self.proxies = conf._sections.get("proxy")
        except (NoOptionError, NoSectionError):
            print("Required fields not available in the conf file.")
            raise

    def respond(self, code=200, msg="OK", headers=None, set_content_type=True):
        """
        Responds to requests with the appropriate http status code and
        the message body.
        :return: [http_response]
        """

        if not headers:
            headers = []

        if code >= 400:
            msg = self.error_tmpl % (code, msg)
            headers.append(("Content-Type", "text/html"))
        code = str(code) + " " + HTTP_STATUS_CODE[code]

        self._start_response(code, headers)
        return [msg]

    def get_xml(self, uri, headers=None, html=False):
        """
        Retrieves the resource using the url, parses it as XML or HTML
        and returns the parsed dom object.
        :param uri: [str] The uri to retrieve
        :param headers: [dict(header_name: value)] optional http headers to send in the request
        :param html: [bool] optional flag to parse the response as HTML
        :return: [lxml_obj] parsed dom.
        """

        if not headers:
            headers = self.hdrs

        page = requests.get(uri, headers=headers)
        page_data = page.content
        try:
            parser = None
            if not html:
                parser = etree.XMLParser(recover=True)
            else:
                parser = etree.HTMLParser(recover=True)
            return etree.parse(StringIO.StringIO(page_data), parser)
        except Exception as e:
            print e
            return self.respond(code=404, msg="Couldn't retrieve data from %s" % uri)

    def fetch_changes(self, requri, dt=None):
        """
        This is what to implement per proxy.
        It should fetch the mementos for the respective implementation.
        It should return a list of 2-tuples,
        :param requri: [str] the requested url, URI-R
        :param dt: [date_obj] accept datetime.
        :return: [list[(mem_dt, mem_url)]] list of 2-tuple. the first element of each being a datetime,
        the second a memento URI.
        """
        raise NotImplementedError()

    def fetch_memento(self, requri, dt=None):
        """
        Similar to fetch_changes but fetches only the required
        info to build the memento headers.
        A special case for wikipedia like systems that have
        many revisions and may not be feasible to retrieve
        all of them at once.
        :param requri: [str] the requested url, URI-R
        :param dt: [date_obj] accept datetime.
        :return: [list[(mem_dt, mem_url)]] list of 2-tuple. the first element of each being a datetime,
        the second a memento URI.
        """
        raise NotImplementedError()

    def handle_timemap(self, req_url):
        """
        Constructs the timemap in link header format. Uses fetch_changes
        to retrieve the mementos first.
        :param req_url: the request url.
        :return: [http_response] the timemap in application/link-format.
        """

        changes = self.fetch_changes(req_url)

        # If timegate redirects, we don't have a timemap of our own
        if type(changes) == dict:
            return None

        if not changes or type(changes) == str:
            return self.respond(code=404,
                                msg='Resource not in archive<br/>'
                                '<blockquote>Resource: %s</blockquote>' %
                                req_url)
        
        links = []
        links.append('<%s>;rel="self";type="application/link-format"' % self.timemap_url)
        links.append('<%s>;rel="timegate"' % self.timegate_url)
        links.append('<%s>;rel="original"' % req_url)
            
        if len(changes) == 1:
            links.append('<%s>;rel="first last memento";datetime="%s"' %
                         (changes[0][1], changes[0][0].strftime(self.date_format)))
        else:
            links.append('<%s>;rel="first memento";datetime="%s"' %
                         (changes[0][1], changes[0][0].strftime(self.date_format)))
            for ch in changes[1:-1]:
                links.append('<%s>;rel="memento";datetime="%s"' %
                             (ch[1], ch[0].strftime(self.date_format)))
            links.append('<%s>;rel="last memento";datetime="%s"' %
                         (changes[-1][1], changes[-1][0].strftime(self.date_format)))
        data = ',\n '.join(links)

        # Add link header with anchored timemap
        tg_link = '<%s>;rel="timemap";type="application/link-format";anchor="%s"'\
                  % (self.timemap_url, req_url)
        headers = []
        headers.append(('Link', tg_link))
        headers.append(("Content-Type", 'application/link-format'))
        return self.respond(code=200, msg=data, headers=headers, set_content_type=False)

    def handle_timegate(self, req_url, acc_dt, wiki=False):
        """
        Constructs the memento response for a timegate request.
        Uses the fetch_memento for wiki like systems or the fetch_changes
        to get the mementos.
        :param req_url: [str] the requested url, URI-R
        :param acc_dt: [date obj] accept datetime
        :param wiki: [bool] if the request is for a wiki like proxy.
        :return: [http_response] the memento timegate http headers with a 302.
        """
        nowd = now()
        current = dateparser.parse(nowd)

        # Database Access via overridden fetch_changes
        if wiki:
            changes = self.fetch_memento(req_url, dt=acc_dt)
        else:
            changes = self.fetch_changes(req_url, dt=acc_dt)

        # Setup response information: link headers
        if changes and type(changes) == list:
            first = changes[0]
            last = changes[-1]
        else:
            first = None
            last = None

        next = None
        prev = None
        headers = []
        loc = []

        links = ['<%s>;rel="original"' % req_url,
                 '<%s>;rel="timemap";type="application/link-format"' % self.timemap_url]

        # Process Error Conditions
        headers.append(('Vary', 'negotiate,accept-datetime'))

        if type(changes) == dict:
            #  XXX Should never occur?
            return None
        elif type(changes) == str:
            # Redirect to better TimeGate
            headers.append(('Location', changes))
            headers.append(('Link', '<%s>;rel="original"' % req_url))
            return self.respond(code=302,
                                msg='Redirecting to better TimeGate: %s' % changes)
        else:
            # check VERB used for GET/HEAD
            if not changes:
                return self.respond(code=404,
                                    msg='Resource not in archive<br/><i><blockquote>'
                                        '<ul><li>Resource: %s</li></ul></blockquote></i>'
                                        % req_url)
            elif self._env.get("REQUEST_METHOD") not in ["GET", "HEAD"]:
                # 405
                headers.append(('Allow', "GET, HEAD"))
                headers.append(('Link', self.construct_link_header(links, first, last)))
                return self.respond(msg="Only GET and HEAD allowed",
                                    code=405,
                                    headers=headers)
            elif acc_dt is None:
                headers.append(('Link', self.construct_link_header(links, first, last)))
                return self.respond(code=400,
                                    msg="Datetime format not correct<br/><i><blockquote>"
                                        "Expected: %s</blockquote></i>" %
                                        (current.strftime(self.date_format)))

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
            tdiff = lambda y, x: float(abs((y-x).days * 86400) + abs((y-x).seconds))
            for c in range(1, len(changes)):
                this = changes[c]
                if acc_dt < this[0] or c == len(changes)-1:
                    llast = changes[c-1]
                    if wiki:
                        # the closest back in time is the best memento
                        loc = llast
                        if c-2 >= 0:
                            prev = changes[c-2]
                        next = this
                    else:
                        # Else find closest delta
                        tdelta1 = tdiff(llast[0], acc_dt)
                        tdelta2 = tdiff(this[0], acc_dt)

                        if tdelta1 < tdelta2:
                            # Closest Memento to request is previous
                            loc = llast
                            if c-2 >= 0:
                                prev = changes[c-2]
                            next = this
                        else:
                            loc = this
                            prev = llast
                            if c < len(changes)-1:
                                next = changes[c+1]
                    break
                    
        headers.append(('Link', self.construct_link_header(links, first, last, loc, next, prev)))
        headers.append(('Location', loc[1]))
        return self.respond(msg='', code=302, headers=headers)

    def construct_link_header(self, links, first, last, curr=None, next=None, prev=None):
        """
        Constructs the memento link header with the appropriate
        rel types.
        :param links: [list[str]] Any existing link header entries like orginal, tg, tm
        :param first: [tuple(mem_dt, mem_uri)] the first memento
        :param last: [tuple(mem_dt, mem_uri)] the lastmemento
        :param curr: [tuple(mem_dt, mem_uri)] the memento
        :param next: [tuple(mem_dt, mem_uri)] the next memento
        :param prev: [tuple(mem_dt, mem_uri)] the prev memento
        :return: [str] the memento link header.
        """

        mylinks = []
        # Do first Memento
        dt = first[0].strftime(self.date_format)
        uri = first[1]
        rel = "first"
        if last and last[1] == uri:
            rel += " last"
            last = None
        if prev and prev[1] == uri:
            rel += " prev"
            prev = None
        elif curr and curr[1] == uri:
            curr = None
        rel += " memento"
        mylinks.append((uri, rel, dt))

        # If last != first:
        if last:
            dt = last[0].strftime(self.date_format)
            uri = last[1]
            rel = "last"
            if curr and curr[1] == uri:
                curr = None
            elif next and next[1] == uri:
                rel += " next"
                next = None
            rel += " memento"
            mylinks.append((uri, rel, dt))

        if prev:
            mylinks.append((prev[1], 'prev memento', prev[0].strftime(self.date_format)))
        if next:
            mylinks.append((next[1], 'next memento', next[0].strftime(self.date_format)))
        if curr:
            mylinks.append((curr[1], 'memento', curr[0].strftime(self.date_format)))

        # lh = ['<%s>;rel="%s";datetime="%s"' % x for x in mylinks]
        lh = ['<%s>;datetime="%s";rel="%s"' % (x[0], x[2], x[1]) for x in mylinks]

        links.extend(lh)
        return ','.join(links)

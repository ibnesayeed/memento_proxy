"""
WebCitation proxy
"""

import StringIO
import urllib2
import cookielib

from lxml import etree

from memento_proxy import *

__author__ = "Robert Sanderson"


class WebHandler(MementoProxy):

    def __init__(self, env, start_response):
        MementoProxy.__init__(self)
        self._env = env
        self._start_response = start_response

    def fetch_changes(self, requri, dt=None):

        cj = cookielib.LWPCookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        urllib2.install_opener(opener)

        if requri == 'http://lanlsource.lanl.gov/hello':
            wcurl = 'http://webcitation.org/5jq247bmx'
        elif requri == 'http://lanlsource.lanl.gov/pics/picoftheday.png':
            wcurl = 'http://webcitation.org/5jq24MRo3'
        elif requri == 'http://odusource.cs.odu.edu/pics/picoftheday.png':
            wcurl = 'http://webcitation.org/5k9j4oXPw'
        elif not requri.endswith('html') and not requri.endswith('htm'):
            # It's always framed :(
            return
        else:
            wcurl = 'http://webcitation.org/query.php?url=' + requri

        txheaders = {'User-Agent': 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'}

        req = urllib2.Request(wcurl, None, txheaders)
        fh = urllib2.urlopen(req)
        fh.close()

        req = urllib2.Request('http://webcitation.org/topframe.php')
        fh = urllib2.urlopen(req)
        data = fh.read()
        fh.close()

        changes = []

        try:
            parser = etree.HTMLParser()
            dom = etree.parse(StringIO.StringIO(data), parser)
        except:
            return

        opts = dom.xpath('//select[@name="id"]/option')
        for o in opts:
            fid = o.attrib['value']
            date = o.text
            if date.find('(failed)') > -1:
                continue
            dtobj = dateparser.parse(date)
            info = {'last' : dtobj, 'obs': 1}
            changes.append((dtobj, 'http://webcitation.org/query?id=' + fid, info))
        changes.sort()

        return changes

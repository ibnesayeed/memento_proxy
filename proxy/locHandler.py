import re
import urllib
import StringIO
import cPickle
import bsddb as bdb
from lxml import etree
from memento_proxy import *


class LocHandler(MementoProxy):

    def __init__(self, env, start_response):
        MementoProxy.__init__(self)
        self._env = env
        self._start_response = start_response

    def fetch_changes(self, requri, dt=None):

        cxn = bdb.db.DB()
        cxn.open('locHash.bdb')
        c = cxn.cursor()

        # set cursor from top of domain
        
        try:
            x = requri.index('/', 7)
            curi = requri[:x+1]
        except:
            curi = requri

        (key, val) = c.set_range(curi)

        if not key.startswith(curi) and not requri.startswith(key):
            # try looking without www
            if curi.startswith('http://www.'):
                curi = 'http://' + curi[11:]
                (key, val) = c.set_range(curi)
                if not key.startswith(curi) and not requri.startswith(key):
                    return []


        collections = {}
        lval = cPickle.loads(val)
        for l in lval:
            collections[l] = 1
        
        (key, val) = c.next()
        while (key.startswith(curi) or requri.startswith(key)):
            lval = cPickle.loads(val)
            for l in lval:
                collections[l] = 1
            (key, val) = c.next()

        c.close()
        cxn.close()

        colls = collections.keys()
        colls.sort()
        changes = []

        datere = re.compile('http://webarchive.loc.gov/[a-zA-Z0-9]+/([0-9]+)/.+')

        for c in colls:
            iauri = "http://webarchives.loc.gov/%s/*/%s" % (c, requri)

            try:
                fh = urllib.urlopen(iauri)
            except:
                continue
            data = fh.read()
            fh.close()

            try:
                parser = etree.HTMLParser(recover=True)
                dom = etree.parse(StringIO.StringIO(data), parser)
            except:
                continue

            alist = dom.xpath('//a')

            for a in alist:
                loc = a.attrib.get('href', '')
                if loc.startswith('http://webarchive.loc.gov/%s/' % c):

                    # extract time from link
                    m = datere.match(loc)
                    if m:
                        date = m.groups()[0]
                    else:
                        continue

                    try:
                        dtobj = dateparser.parse(date + " GMT")
                    except:
                        dtobj = dateparser.parse(date)
                    info = {'last' : dtobj, 'obs' : 1}
                    if a.tail:
                        changes.append((dtobj, loc, info))
                    else:
                        changes[-1][-1]['last'] = dtobj
                        changes[-1][-1]['obs'] += 1

        changes.sort()
        return changes

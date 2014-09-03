
# Memento Cache Proxy for Google search engine.
# Author: Ahmed AlSum aalsum@cs.odu.edu
# Date: July 21, 2010

import re
from dateutil import parser as dateparser
from memento_proxy import *
import requests

end_point = 'http://webcache.googleusercontent.com/search?q=cache:'


class GoogleHandler(MementoProxy):

    def __init__(self, env, start_response):
        MementoProxy.__init__(self)
        self._env = env
        self._start_response = start_response

    def fetch_changes(self, req_url, dt=None):

        final_url = end_point + req_url
        page = requests.get(final_url, headers=self.hdrs).content
        changes = None

        # @type page str
        # This step is required to make sure we have a google cached page.
        if page.find('This is Google&#39;s cache of') > -1:
            dateExpression = re.compile(r"((Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{1,2}, (19|20)\d\d \d\d:\d\d:\d\d)")
            result = dateExpression.search( page )
            if result:
                dtstr = result.group(0)
                dtstr += " GMT"
                dtobj = dateparser.parse(dtstr)
                loc = final_url
                changes = []
                changes.append((dtobj, loc, {'last': dtobj, 'obs': 1, 'type': 'observed'}))

        return changes


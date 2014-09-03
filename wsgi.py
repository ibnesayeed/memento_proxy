"""
Wsgi entry point for all the proxies.
"""

__author__ = 'Harihar Shankar'

import importlib
from dateutil import parser as dateparser
from memento_proxy import MementoProxy, now


def process_req_url(req_url, mem_proxy):
    if req_url.startswith('http/'):
        req_url = req_url.replace('http/', 'http://')
    if not req_url.startswith('http'):
        req_url = "http://" + req_url

    mem_proxy.timegate_url = "%s%s%s/%s/%s" % \
                             (mem_proxy.host_name, mem_proxy.path,
                              mem_proxy.proxy_part, mem_proxy.timegate_url_part, req_url)
    mem_proxy.timemap_url = "%s%s%s/%s/%s/%s" % \
                            (mem_proxy.host_name, mem_proxy.path,
                             mem_proxy.proxy_part, mem_proxy.timemap_url_part,
                             mem_proxy.timemap_link_url_part, req_url)
    return req_url


def application(env, start_response):
    """
    WSGI entry point.
    :param env: the environment variables from the http server.
    :param start_response: the function that will trigger the response.
    :return: the response.
    """

    req_path = env.get("REQUEST_URI", "/")
    req_datetime = env.get("HTTP_ACCEPT_DATETIME")
    accept_datetime = dateparser.parse(now())
    if req_datetime:
        try:
            accept_datetime = dateparser.parse(req_datetime)
            if accept_datetime.tzinfo is None or \
                            accept_datetime.tzinfo.utcoffset(accept_datetime) is None:
                # Naive date. Reparse with Timezone
                req_datetime += " GMT"
                accept_datetime = dateparser.parse(req_datetime)
        except Exception as e:
            accept_datetime = None

    if not req_path.startswith("/"):
        req_path = "/" + req_path

    mem_proxy = MementoProxy()
    if mem_proxy.path:
        req_path = req_path.replace(mem_proxy.path, "")

    req_proxy = req_path.split("/")[0]

    if req_proxy in mem_proxy.proxies:
        module_path = "proxy." + mem_proxy.proxies.get(req_proxy)
        module = importlib.import_module(module_path)
        class_str = mem_proxy.proxies.get(req_proxy)
        class_str = class_str[0].upper() + class_str[1:]
        proxy_class = getattr(module, class_str)

        proxy = proxy_class(env, start_response)
        proxy.proxy_part = req_proxy
        req_serv = req_path.replace(req_proxy + "/", "", 1)
        if req_serv.startswith(mem_proxy.timegate_url_part):
            req_url = req_serv.replace(mem_proxy.timegate_url_part, "", 1)[1:]
            req_url = process_req_url(req_url, proxy)
            if req_proxy.find("wiki") >= 0:
                return proxy.handle_timegate(req_url, accept_datetime, wiki=True)
            else:
                return proxy.handle_timegate(req_url, accept_datetime)
        elif req_serv.startswith(mem_proxy.timemap_url_part):
            req_url = req_serv.replace(mem_proxy.timemap_url_part, "", 1)[1:]
            req_url = req_url.replace(mem_proxy.timemap_link_url_part, "", 1)[1:]
            req_url = process_req_url(req_url, proxy)
            return proxy.handle_timemap(req_url)

    start_response("404 Not Found", [('Content-Type', 'text/html')])
    return ["Requested resource not found."]

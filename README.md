proxy
=====

The proxy uses uwsgi server (http://uwsgi-docs.readthedocs.org/en/latest/) to run as an application server. 

To start the server, run:

uwsgi --http :9000 --wsgi-file wsgi.py --master

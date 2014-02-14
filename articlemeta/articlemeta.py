import os
import urlparse
import json

from wsgiref.simple_server import make_server
import pyramid.httpexceptions as exc
from pyramid.config import Configurator
from pyramid.view import view_config
from pyramid.response import Response
import pymongo

import utils
import controller
from export import Export


@view_config(route_name='index', request_method='GET')
def index(request):
    return Response('Articles Metadata API')


@view_config(route_name='collection',
             request_method='GET')
def collection(request):

    fmt = request.GET.get('format', 'json')

    collection = request.databroker.collection()

    return Response(json.dumps(collection), content_type="application/json")


@view_config(route_name='journal',
             request_method='GET')
def journal(request):

    fmt = request.GET.get('format', 'json')
    collection = request.GET.get('collection', None)
    issn = request.GET.get('issn', None)

    journal = request.databroker.journal(collection=collection, issn=issn)

    return Response(json.dumps(journal), content_type="application/json")


@view_config(route_name='identifiers_journal',
             request_method='GET')
def identifiers_journal(request):

    collection = request.GET.get('collection', None)
    issn = request.GET.get('issn', None)
    offset = request.GET.get('offset', 0)

    try:
        offset = int(offset)
    except ValueError:
        raise exc.HTTPBadRequest('offset must be integer')

    ids = request.databroker.identifiers_journal(collection=collection,
                                                 offset=offset)

    return Response(json.dumps(ids))


@view_config(route_name='add_journal',
             request_method='POST')
def add_journal(request):

    try:
        journal = request.databroker.add_journal(request.json_body)
    except ValueError:
        raise exc.HTTPBadRequest('The posted JSON data is not valid')

    return Response()


@view_config(route_name='delete_journal',
             request_method='DELETE')
def delete_journal(request):

    code = request.GET.get('code', None)
    admintoken = request.GET.get('admintoken', None)

    token = request.registry.settings.get('app', {}).get('admintoken', None)

    if admintoken != token:
        raise exc.HTTPUnauthorized(
            'Invalid admin token'
        )

    if not admintoken or not code:
        raise exc.HTTPBadRequest(
            'The attribute code and admintoken must be given'
        )

    request.databroker.delete_journal(code)

    return Response()


@view_config(route_name='identifiers_article',
             request_method='GET')
def identifiers_article(request):

    collection = request.GET.get('collection', None)
    issn = request.GET.get('issn', None)
    offset = request.GET.get('offset', 0)

    try:
        offset = int(offset)
    except ValueError:
        raise exc.HTTPBadRequest('offset must be integer')

    ids = request.databroker.identifiers_article(collection=collection,
                                                 issn=issn,
                                                 offset=offset)

    return Response(json.dumps(ids))


@view_config(route_name='exists_article',
             request_method='GET',
             request_param=['code'])
def exists_article(request):

    code = request.GET.get('code', None)

    article = request.databroker.exists_article(code)

    return Response(json.dumps(article))


@view_config(route_name='get_article',
             request_method='GET',
             request_param=['code'])
def get_article(request):

    code = request.GET.get('code', None)
    fmt = request.GET.get('format', 'json')

    article = request.databroker.get_article(code)

    if fmt == 'xmlwos':
        return Response(Export(article).xmlwos(), content_type="application/xml")

    return Response(json.dumps(article), content_type="application/json")


@view_config(route_name='add_article',
             request_method='POST')
def add_article(request):

    try:
        article = request.databroker.add_article(request.json_body)
    except ValueError:
        raise exc.HTTPBadRequest('The posted JSON data is not valid')

    return Response()


@view_config(route_name='delete_article',
             request_method='DELETE')
def delete_article(request):

    code = request.GET.get('code', None)
    admintoken = request.GET.get('admintoken', None)

    token = request.registry.settings.get('app', {}).get('admintoken', None)

    if admintoken != token:
        raise exc.HTTPUnauthorized(
            'Invalid admin token'
        )

    if not admintoken or not code:
        raise exc.HTTPBadRequest(
            'The attribute code and admintoken must be given'
        )

    request.databroker.delete_article(code)

    return Response()


def main(settings, *args, **xargs):
    config = Configurator(settings=settings)

    db_url = urlparse.urlparse(settings['app']['mongo_uri'])

    config.registry.db = pymongo.Connection(
        host=db_url.hostname,
        port=db_url.port
    )

    def add_database():
        db = config.registry.db[db_url.path[1:]]
        if db_url.username and db_url.password:
            db.authenticate(db_url.username, db_url.password)
        return db

    def add_databroker(request):
        return controller.DataBroker(add_database())

    config.add_route('index', '/')
    config.add_route('collection', '/api/v1/collection')
    config.add_route('journal', '/api/v1/journal')
    config.add_route('identifiers_journal', '/api/v1/journal/identifiers')
    config.add_route('add_journal', '/api/v1/journal/add')
    config.add_route('delete_journal', '/api/v1/journal/delete')
    config.add_route('get_article', '/api/v1/article')
    config.add_route('add_article', '/api/v1/article/add')
    config.add_route('delete_article', '/api/v1/article/delete')
    config.add_route('identifiers_article', '/api/v1/article/identifiers')
    config.add_route('exists_article', '/api/v1/article/exists')
    config.add_request_method(add_databroker, 'databroker', reify=True)
    config.scan()

    return config.make_wsgi_app()

config = utils.Configuration.from_file(os.environ.get('CONFIG_INI', os.path.dirname(__file__)+'/../config.ini'))

settings = dict(config.items())
app = main(settings)

if __name__ == '__main__':
    server = make_server(settings['http_server']['ip'],
                         int(settings['http_server']['port']),
                         app)
    server.serve_forever()
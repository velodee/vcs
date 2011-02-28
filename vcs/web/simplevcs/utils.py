import cgi
import logging
import traceback
import cStringIO

from mercurial.hgweb.request import wsgirequest, normalize
from mercurial.hgweb import hgweb

from django.http import HttpResponse
from django.utils.encoding import smart_str
from django.contrib.auth import authenticate
from django.core.exceptions import PermissionDenied
from django.utils.importlib import import_module

from vcs import get_repo
from vcs.utils.lazy import LazyProperty
from vcs.web.simplevcs.settings import BASIC_AUTH_REALM, \
    HG_EXTRA_MESSAGES_ENABLED
from vcs.web.simplevcs.models import Repository
from vcs.web.exceptions import RequestError
from vcs.web.simplevcs.signals import pre_clone, pre_push, post_clone, \
    post_push, retrieve_hg_post_push_messages

UNKNOWN = 'unknown'
CLONE = 'clone'
PUSH = 'push'

HG_ACTIONS = {
    'changegroup': CLONE,
    'changegroupsubset': PUSH,
    'unbundle': PUSH,
    'pushkey': PUSH,
}

DEFAULT_USERNAME = 'AnonymousUser'


class MercurialRequest(wsgirequest):
    """
    We need to override ``__init__``, ``respond`` and ``write`` methods in
    order to properly fake mercurial client request.  Those methods need to
    operate on Django's standard ``HttpResponse``.
    """

    def __init__(self, request, repo_path=None):
        """
        Initializes ``MercurialRequest`` and make necessary changes to the
        ``env`` attribute (which is ``META`` attribute of the given request).
        """
        self._already_responded = False
        self._response_written = False
        self.repo_path = repo_path
        self.request = request
        self.messages = []

        # Before we set environment for mercurial
        # we need to fix (if needed) it's PATH_INFO
        if not request.META['PATH_INFO'].endswith == '/':
            request.META['PATH_INFO'] += '/'
        self.env = request.META
        self.env['SCRIPT_NAME'] = request.path
        self.env['PATH_INFO'] = '/'
        if request.user:
            self.env['REMOTE_USER'] = request.user.username

        self.err = self.env['wsgi.errors']
        self.inp = self.env['wsgi.input']
        self.headers = []

        self.form = normalize(cgi.parse(self.inp, self.env,
            keep_blank_values=1))
        self._response = HttpResponse()

    def write(self, thing):
        """
        Writes to the constructed response object.
        """
        if hasattr(thing, "__iter__"):
            for part in thing:
                self.write(part)
        else:
            thing = str(thing)
            self._response.write(thing)

    def respond(self, status, type=None, filename=None, length=0):
        """
        Starts responding (once): sets status code and headers.
        """
        if not self._already_responded:
            self._response.status_code = status
            self._response['content-type'] = type

            for key, value in self.headers:
                self._response[key] = value

            self._already_responded = True

    def get_response(self, hgweb):
        """
        Returns ``HttpResponse`` object created by this request, using given
        ``hgweb``.
        """
        # Pre response signals for clones/pushes
        if self.is_push():
            pre_push.send(None, repo_path=self.repo_path, ip=self.ip,
                username=self.username)
        elif self.is_clone():
            pre_clone.send(None, repo_path=self.repo_path, ip=self.ip,
                username=self.username)

        if not self._response_written:
            self._response.write(''.join(
                (each for each in hgweb.run_wsgi(self))))
            self._response_written = True

        # Pre response signals for clones/pushes
        if self.is_push():
            post_push.send(None, repo_path=self.repo_path, ip=self.ip,
                username=self.username)
        elif self.is_clone():
            post_clone.send(None, repo_path=self.repo_path, ip=self.ip,
                username=self.username)

        # Collect and write extra messages
        if self.is_push() and HG_EXTRA_MESSAGES_ENABLED:
            repository = Repository.objects\
                .select_related('info')\
                .get(path=self.repo_path)
            retrieve_hg_post_push_messages.send(self,
                repository=repository)
            for msg in self.messages :
                self._response.write(msg + '\n')

        return self._response

    @LazyProperty
    def action(self):
        """
        Returns action type of mercurial request (unknown, clone, push).
        """
        QUERY_STRING = self.env.get('QUERY_STRING', None)
        if QUERY_STRING:
            for pair in QUERY_STRING.split('&'):
                key, value = pair.split('=')
                if key == 'cmd' and HG_ACTIONS.has_key(value):
                    return HG_ACTIONS[value]
        return UNKNOWN

    def is_push(self):
        return self.action == PUSH

    def is_clone(self):
        return self.action == CLONE

    @LazyProperty
    def ip(self):
        """
        Returns ip from the request.
        """
        return self.env.get('REMOTE_ADDR', '0.0.0.0')

    @LazyProperty
    def username(self):
        user = getattr(self.request, 'user')
        if user:
            return user.username
        return DEFAULT_USERNAME


class MercurialServer(object):
    """
    Mimics functionality of ``hgweb``.
    """
    def __init__(self, repo_path, **webinfo):
        self.repo_path = repo_path
        self._hgserve = hgweb(repo_path)
        self.setup_web(**webinfo)

    def ui_config(self, section, key, value):
        self._hgserve.repo.ui.setconfig(
            section, key, smart_str(value))

    def setup_web(self, **webinfo):
        for key, value in webinfo.items():
            if value is not None:
                self.ui_config('web', key, value)

    def get_response(self, request):
        mercurial_request = MercurialRequest(request, repo_path=self.repo_path)
        response = mercurial_request.get_response(self._hgserve)
        return response

def get_mercurial_response(request, repo_path, baseurl=None, name=None,
    push_ssl='false', description=None, contact=None, allow_push=None,
    username=None):
    """
    Returns ``HttpResponse`` object prepared basing on the given ``hgserve``
    instance.
    """
    repo_path = str(repo_path) # mercurial requires str, not unicode
    webinfo = dict(
        name=name,
        baseurl=baseurl,
        push_ssl=push_ssl,
        description=description,
        contact=contact,
        allow_push=allow_push,
    )
    mercurial_server = MercurialServer(repo_path, **webinfo)
    if username is not None:
        mercurial_server.ui_config('ui', 'username', smart_str(username))
    response = mercurial_server.get_response(request)
    return response

def is_mercurial(request):
    """
    Returns True if request's target is mercurial server - header
    ``HTTP_ACCEPT`` of such request would start with ``application/mercurial``.
    """
    http_accept = request.META.get('HTTP_ACCEPT')
    if http_accept and http_accept.startswith('application/mercurial'):
        return True
    return False

def basic_auth(request):
    """
    Returns ``django.contrib.auth.models.User`` object
    if authorization was successful and ``None`` otherwise.
    """
    http_authorization = request.META.get('HTTP_AUTHORIZATION')
    user = None
    if http_authorization and http_authorization.startswith('Basic '):
        base64_hash = http_authorization[len('Basic '):]
        credentials = base64_hash.decode('base64')
        username, password = credentials.split(':', 1)
        user = authenticate(username=username, password=password)
        if not user:
            # Raise exception instead of "letting things going" Normally it
            # would work perfectly fine but for users with Python 2.6.5 - they
            # would fall into endless recursion bug
            # (http://bugs.python.org/issue8797) and we just cannot allow that
            raise PermissionDenied
    return user

def ask_basic_auth(request, realm=BASIC_AUTH_REALM):
    """
    Returns HttpResponse with status code 401 (HTTP_AUTHORIZATION) to ask user
    to authorize.
    """
    response = HttpResponse()
    response.status_code = 401
    response['www-authenticate'] = 'Basic realm="%s"' % realm
    return response

def log_error(error):
    """
    Logs traceback and error itself.
    """
    assert(isinstance(error, Exception))
    f = cStringIO.StringIO()
    traceback.print_exc(file=f)
    msg = "Got exception: %s\n\n%s"\
        % (error, f.getvalue())
    logging.error(msg)

def get_repository(repository=None, path=None, alias=None):
    """
    Normalizes given parameters to a ``Repository`` object. May pass only
    ``repository`` or both ``path`` *AND* ``alias``.

    :param: repository: should be a backend ``Repository`` object
    :param: path: path to repository on local machine
    :param: alias: alias of backend specified at ``vcs.backends.BACKENDS`` dict
    """
    if repository and not isinstance(repository, Repository):
        raise RequestError("Given repository has to be instance of Repository "
            "model, not %s" % repository.__class__)
    elif repository and (path or alias):
        raise RequestError("Cannot pass both repository with path/alias")
    elif repository is None and not (path and alias):
        raise RequestError("Have to pass repository OR path/alias")
    if repository is None:
        repository = get_repo(path=path, alias=alias)
    return repository

def str2obj(text):
    """
    Returns object pointed by the string. For example::

        >>> from django.contrib.auth.models import User
        >>> point = 'django.contrib.auth.models.User'
        >>> obj = str2obj(point)
        >>> obj is User
        True

    """
    modpath, objname = text.rsplit('.', 1)
    mod = import_module(modpath)
    try:
        obj = getattr(mod, objname)
    except AttributeError:
        raise ImportError("Cannot retrieve object from location %s" % text)
    return obj


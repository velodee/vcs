import os
import vcs

from django.conf import settings
from django.http import HttpResponse
from django.template import RequestContext
from django.shortcuts import render_to_response
from vcs.utils.helpers import get_scm

abspath = lambda *p: os.path.abspath(os.path.join(*p))

def get_repo_for_request(request):
    alias, rel_path = get_scm(settings.CURDIR)
    repo_path = abspath(settings.CURDIR, rel_path)
    repo = vcs.get_repo(repo_path, alias)
    return repo

def repository_detail(request, path='', template_name='webvcs/repo.html'):
    repo = get_repo_for_request(request)

    context = {
        'repo': repo,
    }
    return render_to_response(template_name, context, RequestContext(request))

def changeset_detail(request, changeset_id, template_name='webvcs/cs.html'):
    repo = get_repo_for_request(request)

    changeset = repo.get_changeset(changeset_id)

    context = {
        'repo': repo,
        'changeset': changeset,
    }
    return render_to_response(template_name, context, RequestContext(request))

def node_detail(request, changeset_id, path, template_name='webvcs/node.html'):
    repo = get_repo_for_request(request)
    changeset = repo.get_changeset(changeset_id)
    node = changeset.get_node(path)

    context = {
        'repo': repo,
        'changeset': changeset,
        'node': node,
        'splitpath': node.path.split('/'),
    }
    return render_to_response(template_name, context, RequestContext(request))

def node_raw(request, changeset_id, path):
    repo = get_repo_for_request(request)
    changeset = repo.get_changeset(changeset_id)
    node = changeset.get_node(path)

    return HttpResponse(node.content, mimetype=node.mimetype)


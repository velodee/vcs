import os
from django.conf import settings
from django.template import RequestContext
from django.shortcuts import render_to_response
from vcs.web.simplevcs.models import Repository
from vcs.utils.helpers import get_scm

abspath = lambda *p: os.path.abspath(os.path.join(*p))

def repository_detail(request, path='', template_name='webvcs/repo.html'):
    alias, rel_path = get_scm(settings.CURDIR)
    repo_path = abspath(settings.CURDIR, rel_path)

    repo = Repository(path=repo_path, alias=alias)

    context = {
        'repo': repo,
    }
    return render_to_response(template_name, context, RequestContext(request))

def changeset_detail(request, changeset_id, template_name='webvcs/cs.html'):
    alias, rel_path = get_scm(settings.CURDIR)
    repo_path = abspath(settings.CURDIR, rel_path)

    repo = Repository(path=repo_path, alias=alias)
    changeset = repo.get_changeset(changeset_id)

    context = {
        'repo': repo,
        'changeset': changeset,
    }
    return render_to_response(template_name, context, RequestContext(request))


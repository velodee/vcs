#!/usr/bin/env python
# encoding: utf-8
#
# Copyright (c) 2010 Marcin Kuzminski,Lukasz Balcerzak.  All rights reserved.
#
"""
Created on Apr 8, 2010

:author: marcink,lukaszb
"""
import os
import re
import time
import urllib2
import datetime
import posixpath
import errno

from mercurial import ui
from mercurial.context import short
from mercurial.error import RepoError, RepoLookupError, Abort
from mercurial.localrepo import localrepository
from mercurial.node import hex
from mercurial.commands import clone, pull
from mercurial.context import memctx, memfilectx

from vcs.backends.base import BaseRepository, BaseChangeset
from vcs.exceptions import RepositoryError, ChangesetError
from vcs.nodes import FileNode, DirNode, NodeKind, RootNode, RemovedFileNode
from vcs.utils.lazy import LazyProperty
from vcs.utils.ordered_dict import OrderedDict
from vcs.utils.paths import abspath, get_dirs_for_path
from vcs.utils import safe_unicode

class MercurialRepository(BaseRepository):
    """
    Mercurial repository backend
    """

    def __init__(self, repo_path, create=False, baseui=None, clone_url=None):
        """
        Raises RepositoryError if repository could not be find at the given
        ``repo_path``.

        :param repo_path: local path of the repository
        :param create=False: if set to True, would try to craete repository if
           it does not exist rather than raising exception
        :param baseui=None: user data
        :param clone_url=None: would try to clone repository from given location
        """

        self.path = abspath(repo_path)
        self.baseui = baseui or ui.ui()
        # We've set path and ui, now we can set repo itself
        self._set_repo(create, clone_url)
        self.revisions = list(self.repo)
        self.changesets = {}

    @LazyProperty
    def name(self):
        return os.path.basename(self.path)

    @LazyProperty
    def branches(self):
        if not self.revisions:
            return {}
        sortkey = lambda ctx: ctx[1]._ctx.rev()
        s_branches = sorted([(name, self.get_changeset(short(head))) for
            name, head in self.repo.branchtags().items()], key=sortkey,
            reverse=True)
        return OrderedDict((name, cs.raw_id) for name, cs in s_branches)

    @LazyProperty
    def tags(self):
        if not self.revisions:
            return {}

        sortkey = lambda ctx: ctx[1]._ctx.rev()
        s_tags = sorted([(name, self.get_changeset(short(head))) for
            name, head in self.repo.tags().items()], key=sortkey, reverse=True)
        return OrderedDict((name, cs.raw_id) for name, cs in s_tags)

    def _set_repo(self, create, clone_url=None):
        """
        Function will check for mercurial repository in given path and return
        a localrepo object. If there is no repository in that path it will raise
        an exception unless ``create`` parameter is set to True - in that case
        repository would be created and returned.
        If ``clone_url`` is given, would try to clone repository from the
        location.
        """
        try:
            if clone_url:
                url = self._get_url(clone_url)
                try:
                    clone(self.baseui, url, self.path)
                except urllib2.URLError:
                    raise Abort("Got HTTP 404 error")
                # Don't try to create if we've already cloned repo
                create = False
            self.repo = localrepository(self.baseui, self.path, create=create)
        except (Abort, RepoError), err:
            if create:
                msg = "Cannot create repository at %s. Original error was %s"\
                    % (self.path, err)
            else:
                msg = "Not valid repository at %s. Original error was %s"\
                    % (self.path, err)
            raise RepositoryError(msg)

    @LazyProperty
    def description(self):
        undefined_description = 'unknown'
        return self.repo.ui.config('web', 'description',
                                   undefined_description, untrusted=True)
    @LazyProperty
    def contact(self):
        from mercurial.hgweb.common import get_contact
        undefined_contact = 'Unknown'
        return get_contact(self.repo.ui.config) or undefined_contact

    @LazyProperty
    def last_change(self):
        """
        Returns last change made on this repository
        """
        from vcs.utils import makedate
        return (self._get_mtime(), makedate()[1])

    def _get_mtime(self):
        try:
            return time.mktime(self.get_changeset().date.timetuple())
        except RepositoryError:
            #fallback to filesystem
            cl_path = os.path.join(self.path, '.hg', "00changelog.i")
            st_path = os.path.join(self.path, '.hg', "store")
            if os.path.exists(cl_path):
                return os.stat(cl_path).st_mtime
            else:
                return os.stat(st_path).st_mtime

    def _get_hidden(self):
        return self.repo.ui.configbool("web", "hidden", untrusted=True)

    def _get_revision(self, revision):
        if len(self.revisions) == 0:
            raise RepositoryError("There are no changesets yet")
        if revision in (None, 'tip', -1):
            revision = self.revisions[-1]
        if isinstance(revision, int) and revision not in self.revisions:
            raise RepositoryError("Revision %r does not exist for this "
                "repository %s" % (revision, self))
        elif isinstance(revision, (str, unicode)) and revision.isdigit() \
                                                    and len(revision) < 12:
            revision = int(revision)
        elif isinstance(revision, (str, unicode)):
            pattern = re.compile(r'^[[0-9a-fA-F]{12}|[0-9a-fA-F]{40}]$')
            if not pattern.match(revision):
                raise RepositoryError("Revision %r does not exist for this "
                    "repository %s" % (revision, self))
        return revision

    def _get_archives(self, archive_name='tip'):
        allowed = self.baseui.configlist("web", "allow_archive", untrusted=True)
        for i in [('zip', '.zip'), ('gz', '.tar.gz'), ('bz2', '.tar.bz2')]:
            if i[0] in allowed or self.repo.ui.configbool("web", "allow" + i[0],
                                                untrusted=True):
                yield {"type" : i[0], "extension": i[1], "node": archive_name}

    def _get_url(self, url):
        """
        Returns normalized url. If schema is not given, would fall to filesystem
        (``file://``) schema.
        """
        url = str(url)
        if url != 'default' and not '://' in url:
            url = '://'.join(('file', url))
        return url

    def get_changeset(self, revision=None):
        """
        Returns ``MercurialChangeset`` object representing repository's
        changeset at the given ``revision``.
        """
        revision = self._get_revision(revision)
        if not self.changesets.has_key(revision):
            changeset = MercurialChangeset(repository=self, revision=revision)
            self.changesets[changeset.revision] = changeset
            self.changesets[changeset._hex] = changeset
            self.changesets[changeset._short] = changeset
        return self.changesets[revision]

    def get_changesets(self, limit=10, offset=None):
        """
        Return last n number of ``MercurialChangeset`` specified by limit
        attribute if None is given whole list of revisions is returned

        @param limit: int limit or None
        @param offset: int offset
        """
        count = self.count()
        offset = offset or 0
        limit = limit or None
        i = 0
        while True:
            if limit and i == limit:
                break
            i += 1
            rev = count - offset - i
            if rev < 0:
                break
            yield self.get_changeset(rev)

    def pull(self, url):
        """
        Tries to pull changes from external location.
        """
        url = self._get_url(url)
        try:
            pull(self.baseui, self.repo, url)
        except Abort, err:
            # Propagate error but with vcs's type
            raise RepositoryError(str(err))

class MercurialChangeset(BaseChangeset):
    """
    Represents state of the repository at the single revision.
    """

    def __init__(self, repository, revision):
        self.repository = repository
        revision = repository._get_revision(revision)
        try:
            ctx = repository.repo[revision]
        except RepoLookupError:
            raise RepositoryError("Cannot find revision %s" % revision)
        self.revision = ctx.rev()
        self._ctx = ctx
        self._fctx = {}
        self.author = safe_unicode(ctx.user())
        self.message = safe_unicode(ctx.description())
        self.branch = ctx.branch()
        self.tags = ctx.tags()
        self.date = datetime.datetime.fromtimestamp(ctx.date()[0])
        self._file_paths = list(ctx)
        self._dir_paths = list(set(get_dirs_for_path(*self._file_paths)))
        self._dir_paths.insert(0, '') # Needed for root node
        self.nodes = {}
        self.added_ctx = None
        self.removed_ctx = None
        self.added_cache = {}
        self.removed_cache = {}
        
    @LazyProperty
    def _paths(self):
        return self._dir_paths + self._file_paths

    @LazyProperty
    def _hex(self):
        return self._ctx.hex()

    @LazyProperty
    def _short(self):
        return safe_unicode(short(self._ctx.node()))

    @LazyProperty
    def id(self):
        if self.last:
            return u'tip'
        return self._short

    @LazyProperty
    def raw_id(self):
        """
        Returns raw string identifing this changeset, useful for web
        representation.
        """
        return self._short

    @LazyProperty
    def parents(self):
        """
        Returns list of parents changesets.
        """
        return [self.repository.get_changeset(parent.rev())
                for parent in self._ctx.parents() if parent.rev() >= 0]

    def _fix_path(self, path):
        """
        Paths are stored without trailing slash so we need to get rid off it if
        needed.
        """
        if path.endswith('/'):
            path = path.rstrip('/')
        return path

    def _get_kind(self, path):
        path = self._fix_path(path)
        if path in self._file_paths:
            return NodeKind.FILE
        elif path in self._dir_paths:
            return NodeKind.DIR
        else:
            raise ChangesetError("Node does not exist at the given path %r"
                % (path))

    def _get_filectx(self, path):
        if self._get_kind(path) != NodeKind.FILE:
            raise ChangesetError("File does not exist for revision %r at "
                " %r" % (self.revision, path))
        if not path in self._fctx:
            self._fctx[path] = self._ctx[path]
        return self._fctx[path]

    def get_file_content(self, path):
        """
        Returns content of the file at given ``path``.
        """
        fctx = self._get_filectx(path)
        return fctx.data()

    def get_file_size(self, path):
        """
        Returns size of the file at given ``path``.
        """
        fctx = self._get_filectx(path)
        return fctx.size()

    def get_file_message(self, path):
        """
        Returns message of the last commit related to file at the given
        ``path``.
        """
        return safe_unicode(self.get_file_changeset(path).message)

    def get_file_revision(self, path):
        """
        Returns revision of the last commit related to file at the given
        ``path``.
        """
        fctx = self._get_filectx(path)
        return fctx.linkrev()

    def get_file_changeset(self, path):
        """
        Returns last commit of the file at the given ``path``.
        """
        fctx = self._get_filectx(path)
        changeset = self.repository.get_changeset(fctx.linkrev())
        return changeset

    def get_file_history(self, path):
        """
        Returns history of file as reversed list of ``Changeset`` objects for
        which file at given ``path`` has been modified.
        """
        fctx = self._get_filectx(path)
        nodes = [fctx.filectx(x).node() for x in fctx.filelog()]
        changesets = [self.repository.get_changeset(hex(node))
            for node in reversed(nodes)]
        return changesets

    def get_file_annotate(self, path):
        """
        Returns a list of three element tuples with lineno,changeset and line
        """
        fctx = self._get_filectx(path)
        annotate = []
        for ln_no, annotate_data in enumerate(fctx.annotate(), 1):
            annotate.append((ln_no, self.repository\
                             .get_changeset(hex(annotate_data[0].node())),
                             annotate_data[1],))

        return annotate

    def get_nodes(self, path):
        """
        Returns combined ``DirNode`` and ``FileNode`` objects list representing
        state of changeset at the given ``path``. If node at the given ``path``
        is not instance of ``DirNode``, ChangesetError would be raised.
        """

        if self._get_kind(path) != NodeKind.DIR:
            raise ChangesetError("Directory does not exist for revision %r at "
                " %r" % (self.revision, path))
        path = self._fix_path(path)
        filenodes = [FileNode(f, changeset=self) for f in self._file_paths
            if os.path.dirname(f) == path]
        dirs = path == '' and '' or [d for d in self._dir_paths
            if d and posixpath.dirname(d) == path]
        dirnodes = [DirNode(d, changeset=self) for d in dirs
            if os.path.dirname(d) == path]
        nodes = dirnodes + filenodes
        # cache nodes
        for node in nodes:
            self.nodes[node.path] = node
        nodes.sort()
        return nodes

    def get_node(self, path):
        """
        Returns ``Node`` object from the given ``path``. If there is no node at
        the given ``path``, ``ChangesetError`` would be raised.
        """

        path = self._fix_path(path)
        if not path in self.nodes:
            if path in self._file_paths:
                node = FileNode(path, changeset=self)
            elif path in self._dir_paths or path in self._dir_paths:
                if path == '':
                    node = RootNode(changeset=self)
                else:
                    node = DirNode(path, changeset=self)
            else:
                raise ChangesetError("There is no file nor directory "
                    "at the given path: %r at revision %r"
                    % (path, '%s:%s' % (self.revision, self.id)))
            # cache node
            self.nodes[path] = node
        return self.nodes[path]

    @LazyProperty
    def added(self):
        """
        Returns list of added ``FileNode`` objects.
        """
        paths = self._ctx.files()
        added_nodes = []
        for path in paths:
            try:
                last_node = self.repository.get_changeset(hex(
                                    self._get_filectx(path).filectx(0).node()))
                node = self.get_node(path)
                if last_node is self:
                    added_nodes.append(node)
            except ChangesetError:
                pass
        return added_nodes

    @LazyProperty
    def changed(self):
        """
        Returns list of modified ``FileNode`` objects.
        """
        paths = self._ctx.files()
        changed_nodes = []
        for path in paths:
            try:
                last_node = self.repository.get_changeset(hex(
                                    self._get_filectx(path).filectx(0).node()))
                node = self.get_node(path)
                if last_node is not self:
                    changed_nodes.append(node)
            except ChangesetError:
                pass
        return changed_nodes

    @LazyProperty
    def removed(self):
        """
        Returns list of removed ``FileNode`` objects.
        """
        paths = self._ctx.files()
        removed_nodes = []
        for path in paths:
            try:
                self.get_node(path)
            except ChangesetError:
                node = RemovedFileNode(path=path)
                removed_nodes.append(node)
        return removed_nodes



    def add(self, added, **kwargs):
        def filectxfn(repo, memctx, path):
            
            filenode = self.added_cache[path]
            return memfilectx(path=filenode.path,
                              data=filenode.content,
                              islink=False,
                              isexec=False,
                              copied=False)
        do_added = False
        if not isinstance(added, (list, tuple,)):
            added = list([added])
            
        for fn in added:
            
            if not isinstance(fn, (FileNode,)):
                raise Exception('You must give FileNode to added files list')
            self.added_cache[fn.path] = fn
            do_added = True        

        if do_added:
            user = kwargs.get('user') or self.repository.contact
             
            self.files_to_add = sorted([node.path for node in added])
            parent1 = self.repository.repo[self.raw_id].node()
            parent2 = None
            self.added_ctx = memctx(repo=self.repository.repo,
                                 parents=(parent1, parent2,),
                                 text='',
                                 files=self.files_to_add,
                                 filectxfn=filectxfn,
                                 user=user,
                                 date=kwargs.get('date', None),
                                 extra=kwargs)
    
    def remove(self, removed, **kwargs):
        def fileremovectxfn(repo, memctx, path):
            raise IOError(errno.ENOENT, '%s is deleted' % path)
    
        do_removed = False
        if not isinstance(removed, (list, tuple,)):
            removed = list([removed])
            
        for fn in removed:
            
            if not isinstance(fn, (FileNode,)):
                raise Exception('You must give FileNode to removed files list')
            self.removed_cache[fn.path] = fn
            do_removed = True        

        if do_removed:
            user = kwargs.get('user') or self.repository.contact
             
            self.files_to_add = sorted([node.path for node in removed])
            parent1 = self.repository.repo[self.raw_id].node()
            parent2 = None
            self.added_ctx = memctx(repo=self.repository.repo,
                                 parents=(parent1, parent2,),
                                 text='',
                                 files=self.files_to_add,
                                 filectxfn=fileremovectxfn,
                                 user=user,
                                 date=kwargs.get('date', None),
                                 extra=kwargs)
                
    def commit(self, message):
        self.added_ctx._text = message
        self.repository.repo.commitctx(self.added_ctx)
        

    def get_state(self):
        """gets current ctx state"""
        print '+', self.added_cache.values()
        print '-', self.removed_cache.values()
        
        
        
if __name__ == '__main__':
    repo = MercurialRepository('/tmp/wiki')
    r = repo.repo         
        
    tip = repo.get_changeset()
    
    tip.add(FileNode('wikifile.rst', content='a large file'))
    tip.add([FileNode('wikifile1.rst', content='file1'), FileNode('wikifile2.rst', content='file2'), ])
    
    tip.get_state()
    
    tip.commit('added wikipage')

#def commit(repo, message, added=[], removed=[], changed=[]):
#    do_added = False
#
#            
#        r.commitctx(ctx)
#    
#    
#    do_removed = False
#    for fn in removed:
#        if not isinstance(fn, (FileNode,)):
#            raise Exception('You must give FileNode to removed files list')        
#        do_removed = True

#    
#    if do_removed:
#        ctx = context.memctx(repo=repo,
#                         parents=(repo['tip'].node(), None,),
#                         text=message,
#                         files=[node.path for node in removed],
#                         filectxfn=fileremovectxfn,
#                         user='marcink',
#                         date=None,
#                         extra=None)
#        
#        r.commitctx(ctx)
#        
#    do_changed = False
#    
#    for fn in changed:
#        if not isinstance(fn, (FileNode,)):
#            raise Exception('You must give FileNode to changed files list')        
#        do_changed = True
#        def filectxfn(repo, memctx, path):
#            return context.memfilectx(path=path,
#                              data=fn.content,
#                              islink=False,
#                              isexec=False,
#                              copied=False)
#    if do_changed:
#        ctx = context.memctx(repo=repo,
#                         parents=(repo['tip'].node(), None,),
#                         text=message,
#                         files=[node.path for node in changed],
#                         filectxfn=filectxfn,
#                         user='marcink',
#                         date=None,
#                         extra=None)
#        
#        r.commitctx(ctx)                
#
#f0 = FileNode(path='wikipage0.rst', content='Hello wiki !!!!')
#f1 = FileNode(path='section/wikipage1.rst', content='Hello wiki !!!!')
#f2 = FileNode(path='wikipage1.rst', content='Hello wiki !!!!')
#f3 = FileNode(path='section/subsection/wikipage1.rst', content='Hello wiki !!!!')
#
#
#commit(r, 'Added wikipage', added=[f0, f1, f2, f3])
##commit(r, 'Removed newfile', removed=['wikipage.rst'],)
##commit(r, 'updated file', changed=[FileNode(path='wikipage1.rst', content='Same hej hej !')],)

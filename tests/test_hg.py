import unittest

from vcs.backends.hg import MercurialRepository
from vcs.exceptions import ChangesetError, RepositoryError
from vcs.nodes import NodeKind

TEST_HG_REPO = '/tmp/vcs'

class MercurialRepositoryTest(unittest.TestCase):

    def setUp(self):
        self.repo = MercurialRepository(TEST_HG_REPO)

    def test_repo_create(self):
        wrong_repo_path = '/tmp/errorrepo'
        self.assertRaises(RepositoryError, MercurialRepository, wrong_repo_path)

    def test_revisions(self):
        # there are 21 revisions at bitbucket now
        # so we can assume they would be available from now on
        subset = set(range(0, 22))
        self.assertTrue(subset.issubset(set(self.repo.revisions)))

    def test_branches(self):
        # now there are 44 revisions and branches stated below
        branches44 = ['default', 'web']
        set44 = set(branches44)
        self.assertTrue(set44.issubset(set(self.repo.branches)))

    def test_tags(self):
        # now there are 44 revisions and tags stated below
        tags44 = ['tip']
        set44 = set(tags44)
        self.assertTrue(set44.issubset(set(self.repo.tags)))

    def _test_single_changeset_cache(self, revision):
        chset = self.repo.get_changeset(revision)
        self.assertTrue(self.repo.changesets.has_key(revision))
        self.assertEqual(chset, self.repo.changesets[revision])

    def test_changesets_cache(self):
        for revision in xrange(0, 11):
            self._test_single_changeset_cache(revision)

    def _test_request(self, path, revision):
        chset = self.repo.get_changeset(revision)
        self.assertEqual(chset.get_node(path),
            self.repo.request(path, revision))

    def test_request(self):
        """ Tests if repo.request changeset.get_node would return same """
        nodes_info = (
            ('', 'tip'),
            ('README.rst', 19),
            ('vcs', 20),
            ('vcs/backends', 21),
            ('vcs/backends/hg.py', 25),
        )
        for path, revision in nodes_info:
            self._test_request(path, revision)

    def test_initial_changeset(self):

        init_chset = self.repo.get_changeset(0)
        self.assertEqual(init_chset.message, 'initial import')
        self.assertEqual(init_chset.author,
            'Marcin Kuzminski <marcin@python-blog.com>')
        self.assertEqual(sorted(init_chset._file_paths),
            sorted([
                'vcs/__init__.py',
                'vcs/backends/BaseRepository.py',
                'vcs/backends/__init__.py',
            ])
        )
        self.assertEqual(sorted(init_chset._dir_paths),
            sorted(['vcs/backends', 'vcs']))

        self.assertRaises(ChangesetError, init_chset.get_node, path='foobar')

        node = init_chset.get_node('vcs/')
        self.assertTrue(hasattr(node, 'kind'))
        self.assertEqual(node.kind, NodeKind.DIR)

        node = init_chset.get_node('vcs')
        self.assertTrue(hasattr(node, 'kind'))
        self.assertEqual(node.kind, NodeKind.DIR)

        node = init_chset.get_node('vcs/__init__.py')
        self.assertTrue(hasattr(node, 'kind'))
        self.assertEqual(node.kind, NodeKind.FILE)

    def test_not_existing_changeset(self):
        self.assertRaises(RepositoryError, self.repo.get_changeset,
            self.repo.revisions[-1] + 1)

        # Small chance we ever get to this one
        revision = pow(2, 100)
        self.assertRaises(RepositoryError, self.repo.get_changeset, revision)

    def test_changeset10(self):

        chset10 = self.repo.get_changeset(10)
        README = """===
VCS
===

Various Version Control System management abstraction layer for Python.

Introduction
------------

TODO: To be written...

"""
        node = chset10.get_node('README.rst')
        self.assertEqual(node.kind, NodeKind.FILE)
        self.assertEqual(node.content, README)

class MercurialChangesetTest(unittest.TestCase):

    def setUp(self):
        self.repo = MercurialRepository(TEST_HG_REPO)

    def _test_equality(self, changeset):
        revision = changeset.revision
        self.assertEqual(changeset, self.repo[revision])
        self.assertEqual(changeset, self.repo.changesets[revision])
        self.assertEqual(changeset, self.repo.get_changeset(revision))

    def test_equality(self):
        changesets = [self.repo[0], self.repo[10], self.repo[20]]
        for changeset in changesets:
            self._test_equality(changeset)

    def test_default_changeset(self):
        tip = self.repo['tip']
        self.assertEqual(tip, self.repo[None])
        self.assertEqual(tip, self.repo.get_changeset())
        # Mercurial backend converts all given revision parameters
        # so it cannot pass following two (commented) test
        # self.assertEqual(tip, self.repo.changesets[None])
        # self.assertEqual(tip, self.repo.changesets['tip'])
        self.assertEqual(tip, self.repo.get_changeset(revision=None))
        self.assertEqual(tip, list(self.repo.get_changesets(limit=1))[0])

    def test_root_node(self):
        tip = self.repo['tip']
        tip.get_root() is tip.get_node('')

    def _test_getitem(self, path):
        tip = self.repo['tip']
        tip[path] is tip.get_node(path)

    def test_getitem(self):
        paths = ['vcs', 'vcs/__init__.py', 'README.rst', 'MANIFEST.in',
            'setup.py', 'vcs/backends', 'vcs/backends/base.py']
        for path in paths:
            self._test_getitem(path)

    def test_branch_and_tags(self):
        chset0 = self.repo[0]
        self.assertEqual(chset0.branch, 'default')
        self.assertEqual(chset0.tags, [])

        chset10 = self.repo[10]
        self.assertEqual(chset10.branch, 'default')
        self.assertEqual(chset10.tags, [])

        chset44 = self.repo[44]
        self.assertEqual(chset44.branch, 'web')

        tip = self.repo['tip']
        self.assertTrue('tip' in tip.tags)


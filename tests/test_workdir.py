"""
Tests so called "in memory changesets" commit API of vcs.
"""
import os
import vcs
import time
import unittest2

from conf import SCM_TESTS, get_new_dir

from vcs.nodes import FileNode


class WorkdirTestMixin(object):
    """
    This is a backend independent test case class which should be created
    with ``type`` method.

    It is required to set following attributes at subclass:

    - ``backend_alias``: alias of used backend (see ``vcs.BACKENDS``)
    - ``repo_path``: path to the repository which would be created for set of
      tests
    """

    def get_backend(self):
        return vcs.get_backend(self.backend_alias)

    def setUp(self):
        """
        Ensure that each test is run with new, clean repository.
        """
        Backend = self.get_backend()
        self.repo_path = get_new_dir(str(time.time()))
        self.repo = Backend(self.repo_path, create=True)
        self.nodes = [
            FileNode('foobar', content='Foo & bar'),
            FileNode('foobar2', content='Foo & bar, doubled!'),
            FileNode('foo bar with spaces', content=''),
            FileNode('foo/bar/baz', content='Inside'),
        ]

    def write_file(self, path, data, append=False, binary=False,
            createdirs=True):
        """
        Writes data into file at given ``path``. If ``append`` flag is set to
        True then file would be opened with 'a' mode rather than 'w'.
        """
        path = path.rstrip('/')
        dir = os.path.dirname(path)
        try:
            # Creates missing directories if necessary
            os.makedirs(dir)
        except OSError:
            pass
        f = open(path, append and 'a' or 'w')
        try:
            f.write(data)
        finally:
            f.close()

    def test_get_untracked_empty_repo(self):
        self.assertEqual(list(self.repo.workdir.get_untracked()), [],
            "It's new, clean and empty repository and no files should be "
            "listed as untracked as there are no files at all")

    def test_get_untracked(self):
        for node in self.nodes:
            node_abspath = os.path.join(self.repo.path, node.path)
            self.write_file(node_abspath, node.content)
        result_get_untracked = sorted((node.path for node in
            self.repo.workdir.get_untracked()))
        result_nodes = sorted((node.path for node in self.nodes))
        self.assertEqual(result_get_untracked, result_nodes)

    #def test_add(self):
        #rev_count = len(self.repo.revisions)
        ## Populate filesystem

        #to_add = [FileNode(node.path, content=node.content)
            #for node in self.nodes]
        #self.imc.add(*to_add)
        #message = 'Added newfile.txt and newfile2.txt'
        #author = str(self.__class__)
        #changeset = self.imc.commit(message=message, author=author)

        #newtip = self.repo.get_changeset()
        #self.assertEqual(changeset, newtip)
        #self.assertEqual(rev_count + 1, len(self.repo.revisions))
        #self.assertEqual(newtip.message, message)
        #self.assertEqual(newtip.author, author)
        #self.assertTrue(not any((self.imc.added, self.imc.changed,
            #self.imc.removed)))
        #for node in to_add:
            #self.assertEqual(newtip.get_node(node.path).content, node.content)


# For each backend create test case class
for alias in SCM_TESTS:
    attrs = {
        'backend_alias': alias,
    }
    cls_name = ''.join(('%s workdir test' % alias).title().split())
    bases = (WorkdirTestMixin, unittest2.TestCase)
    globals()[cls_name] = type(cls_name, bases, attrs)


if __name__ == '__main__':
    unittest2.main()


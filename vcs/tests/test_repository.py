from vcs.tests.base import BackendTestMixin
from vcs.tests.conf import SCM_TESTS
from vcs.tests.conf import TEST_USER_CONFIG_FILE
    def test_repo_equality(self):
        self.assertTrue(self.repo == self.repo)

    def test_repo_equality_broken_object(self):
        import copy
        _repo = copy.copy(self.repo)
        delattr(_repo, 'path')
        self.assertTrue(self.repo != _repo)

    def test_repo_equality_other_object(self):
        class dummy(object):
            path = self.repo.path
        self.assertTrue(self.repo != dummy())

index 0000000000000000000000000000000000000000..f6ea0495187600e7b2288c8ac19c5886383a4632
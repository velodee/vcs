from django.conf.urls.defaults import *


urlpatterns = patterns('webvcs.views',
    url(r'^$',
        view='repository.repository_detail',
        name='webvcs_repo_detail'),
    url(r'^changesets/(?P<changeset_id>[0-9a-zA-Z]+)/$',
        view='repository.changeset_detail',
        name='webvcs_changeset_detail'),
    url(r'^src/raw/(?P<changeset_id>[0-9a-zA-Z]+)/(?P<path>.*)$',
        view='repository.node_raw',
        name='webvcs_node_raw'),
    url(r'^src/(?P<changeset_id>[0-9a-zA-Z]+)/(?P<path>.*)$',
        view='repository.node_detail',
        name='webvcs_node_detail'),
)


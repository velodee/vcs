from django.conf.urls.defaults import *


urlpatterns = patterns('webvcs.views',
    url(r'^$', 'repository.repository_detail', name='repo-detail'),
    url(r'^(?P<changeset_id>.+)/$', 'repository.changeset_detail',
        name='changeset-detail'),
)


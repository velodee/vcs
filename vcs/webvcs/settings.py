import os

from django.conf import global_settings

abspath = lambda *p: os.path.abspath(os.path.join(*p))

DEBUG = True
TEMPLATE_DEBUG = DEBUG
PROJECTOR_HG_PUSH_SSL = False

PROJECT_ROOT = abspath(os.path.dirname(__file__))

TEST_RUNNER = 'django.test.simple.DjangoTestSuiteRunner'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': abspath(PROJECT_ROOT, '.hidden.db'),
        'TEST_NAME': ':memory:',
    },
}

# Make sqlite3 files relative to project's directory
for db, conf in DATABASES.items():
    if conf['ENGINE'] == 'sqlite3' and not conf['NAME'].startswith(':'):
        conf['NAME'] = abspath(PROJECT_ROOT, conf['NAME'])

INSTALLED_APPS = (
    'webvcs',
    'gunicorn',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    #'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    #'django.contrib.auth.middleware.AuthenticationMiddleware',
    #'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.transaction.TransactionMiddleware',
)

INTERNAL_IPS = ('127.0.0.1',)

MEDIA_ROOT = abspath(PROJECT_ROOT, 'media')
MEDIA_URL = '/media/'
ADMIN_MEDIA_PREFIX = '/admin-media/'

ROOT_URLCONF = 'webvcs.urls'

TEMPLATE_CONTEXT_PROCESSORS = global_settings.TEMPLATE_CONTEXT_PROCESSORS + (
    'django.core.context_processors.request',
)
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
    'django.template.loaders.eggs.load_template_source',
)

TEMPLATE_DIRS = (
    os.path.join(os.path.dirname(__file__), 'templates'),
)

SITE_ID = 1

USE_I18N = True
USE_L10N = True

CACHE_PREFIX = 'webcs'
#CACHE_TIMEOUT = 1 # For dev server

LOGIN_REDIRECT_URL = '/'
#AUTH_PROFILE_MODULE = 'projector.UserProfile'

AUTHENTICATION_BACKENDS = (
    #'django.contrib.auth.backends.ModelBackend', # this is default
    #'guardian.backends.ObjectPermissionBackend',
)
ANONYMOUS_USER_ID = -1

ACCOUNT_ACTIVATION_DAYS = 7
GRAVATAR_DEFAULT_IMAGE = 'mm'

try:
    from conf.local_settings import *
    try:
        for app in LOCAL_INSTALLED_APPS:
            if app not in INSTALLED_APPS:
                INSTALLED_APPS += (app,)
        for middleware in LOCAL_MIDDLEWARE_CLASSES:
            if middleware not in MIDDLEWARE_CLASSES:
                MIDDLEWARE_CLASSES += (middleware,)
    except NameError:
        pass
except ImportError:
    pass

print PROJECT_ROOT

CURDIR = os.getcwd()
print "CURDIR: %s" % CURDIR

#!/usr/bin/env python
import os
import sys
from django.core.management import execute_manager

abspath = lambda *p: os.path.abspath(os.path.join(*p))

PROJECT_ROOT = abspath(os.path.dirname(__file__), '..')
sys.path.append(PROJECT_ROOT)

os.environ['DJANGO_SETTINGS_MODULE'] = 'webvcs.settings'

try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

def main():
    #execute_manager(settings)
    from django.core.management import call_command
    #call_command('run_gunicorn')
    call_command('runserver')

if __name__ == "__main__":
    main()



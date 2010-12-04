#!/usr/bin/env python
import os
import sys
from django.core.management import execute_manager

PROJECT_ROOT = '/Users/lukaszb/develop/workspace/projector'
PROJECT_DIR = PROJECT_ROOT + '/example_project'
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, PROJECT_DIR)
os.environ['DJANGO_SETTINGS_MODULE'] = 'webvcs.settings'

try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

def main():
    execute_manager(settings)

if __name__ == "__main__":
    main()



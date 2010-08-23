import os

abspath = lambda *p: os.path.abspath(os.path.join(*p))

def get_dirs_for_path(*paths):
    """
    Returns list of directories, including intermediete.
    """
    for path in paths:
        head = path
        while head:
            head, tail = os.path.split(head)
            if head:
                yield head
            else:
                # We don't need to yield empty path
                break

def get_dir_size(path):
    root_path = path
    size = 0
    for path, dirs, files in os.walk(root_path):
        for f in files:
            try:
                size +=  os.path.getsize(os.path.join(path, f))
            except OSError:
                pass
    return size


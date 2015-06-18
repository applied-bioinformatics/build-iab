import os

import boto
from boto.s3.key import Key

def upload_s3_book(release, directory):
    conn = boto.connect_s3()
    bucket = conn.get_bucket('readiab.org')

    html = {'Content-type': 'text/html; charset=utf-8'}

    key_prefix = 'book/%s/' % release
    root_offset = None

    for root, dirs, files in os.walk(directory):
        if not root_offset:
            root_offset = root

        r = root.replace(root_offset, '').replace('/', '')
        for file in files:
            key = key_prefix
            if r:
                key += r + '/'

            key += file
            if file.startswith('index'):
                key += '.html'

            path = os.path.join(root, file)

            upload = Key(bucket)
            upload.key = key
            if '.zip' in path:
                upload.set_contents_from_filename(path)
            else:
                upload.set_contents_from_filename(path, headers=html)

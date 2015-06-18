import os

import boto
from boto.s3.key import Key

def upload_s3_book(release, directory):
    html = {
        'Content-type': 'text/html; charset=utf-8'
    }


    conn = boto.connect_s3()
    bucket = conn.get_bucket('readiab.org')

    key_prefix = 'book/%s/' % release
    root_offset = None

    for root, dirs, files in os.walk(directory):
        if not root_offset:
            root_offset = root

        r = root.lstrip(root_offset)
        for file in files:
            key = key_prefix
            if r:
                 key += r + '/'

            if not file.startswith('index') and not file.endswith('.zip'):
                key += file.split('.')[0]
            else:
                key += file

            path = os.path.join(root, file)

            upload = Key(bucket)
            upload.key = key
            if '.zip' not in file:
                upload.set_contents_from_filename(path, headers=html)
            else:
                upload.set_contents_from_filename(path)

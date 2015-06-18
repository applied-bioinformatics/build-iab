#!/usr/bin/env python

# ----------------------------------------------------------------------------
# Copyright (c) 2013--, IAB development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
# ----------------------------------------------------------------------------

from IPython.nbconvert import HTMLExporter
from IPython.config import Config
from io import StringIO
from sys import argv
import sys
from itertools import zip_longest
import os
import markdown2
import tempfile
import CommonMark as cm
import IPython
from six.moves.html_parser import HTMLParser
import yaml
import shutil
import csv

def md_to_html(input_fp, output_fp, ignore_badges=True):
    """ Convert a markdown file to HTML.

        This is useful for converting the README.md to an index.html.
    """
    md_lines = []
    for line in open(input_fp):
        line = line.strip('\n')
        if ignore_badges and line.startswith('[!'):
            continue
        md_lines.append(line)

    nb_s = ipymd.convert('\n'.join(md_lines),
                             from_='markdown', to='notebook')
    print(type(nb_s))
    html_exporter = HTMLExporter()

    html_out, _ = html_exporter.from_notebook_node(nb_s)
    #html = markdown2.markdown('\n'.join(md_lines))
    open(output_fp, 'w').write(html_out)

def hacky():
    sys.stdout = open(os.devnull, "w")
    import ipymd
    sys.stdout = sys.__stdout__
    return ipymd

ipymd = hacky()

class IDFinder(HTMLParser):
    def handle_starttag(self, tag, attrs):
        if tag == 'link':
            attrs = dict(attrs)
            if 'src' in attrs:
                self._ID = attrs['src']
                return
        raise Exception("Invalid ID for section")

    def get_id(self):
        return self._ID

class Node(object):

    def __init__(self):
        self.children = []
        self.parent = None
        self.content = []
        self.title = ''
        self.id = ''
        self.start = 1
        self.file = ''

    def __getitem__(self, key):
        return self.children[key]

    def __iter__(self):
        for node in self.traverse():
            yield node

    def traverse(self):
        traversal = [self]
        for child in self.children:
            traversal += child.traverse()
        return traversal

    def add_child(self, node):
        self.children.append(node)
        node.parent = self

    def has_parent(self):
        return self.parent is not None

    def depth(self):
        d = 0
        n = self
        while(n.has_parent()):
            d += 1
            n = n.parent
        return d

def expand_file(fp):
    if os.path.splitext(fp)[1] != '.md':
        raise ValueError("Not a markdown file: %r" % fp)

    with open(fp) as f:
        lines = f.readlines()
        ast = cm.DocParser().parse(''.join(lines))

    root = Node()
    root.file = fp
    current_node = root
    last_node = root

    current_level = 0

    for node in ast.children:
        if node.t == 'ATXHeader':
            diff = node.level - current_level

            if diff > 1:
                raise Exception("Stranded header: %r" % node.strings[0])

            if diff <= 0:
                while(diff < 1):
                    if not current_node.has_parent():
                        raise Exception("Overindented header: %r" % node.strings[0])
                    current_node = current_node.parent
                    current_level -= 1
                    diff += 1

            if diff == 1:
                new = Node()
                current_node.add_child(new)
                current_node = new
                current_level += 1


            parser = IDFinder()
            parser.feed(node.inline_content[-1].c.strip())
            parser.close()

            current_node.title = node.inline_content[0].c.strip()
            current_node.id = parser.get_id()
            current_node.start = node.start_line
            current_node.file = fp
            current_node.content = lines[node.start_line:]
            last_node.content = last_node.content[:node.start_line - last_node.start - 1]
            last_node = current_node

    return root.children[0]

def build_branch(rootdir):
    with open(os.path.join(rootdir, 'index.yaml')) as f:
        index = yaml.load(f.read())['contents']

    tree = expand_file(os.path.join(rootdir, 'index.md'))
    for elem in index:
        maybe_file = os.path.join(rootdir, elem + '.md')
        if os.path.isfile(maybe_file):
            tree.add_child(expand_file(maybe_file))
        else:
            tree.add_child(build_branch(os.path.join(rootdir, elem)))

    return tree

def make_link(node, from_=None, ext='', short_index=False):
    link = []
    path = node.path.split('.')
    from_path = from_.path.split('.')
    change_dir = False

    for i, (t, f) in enumerate(zip_longest(path, from_path), 0):
        if i < 1:
            if t != f:
                if t:
                    link.append(t + '/')
                elif not f:
                    link.append('/')
                if f:
                    change_dir = True
                    link.insert(0, '../')

        elif t and i == 1:
            if t != f or change_dir:
                link.append(t + ext)
        elif t and i == 2:
            link.append('#' + t)
        elif t and i > 2:
            link.append('.' + t)

    link = ''.join(link)
    if not short_index and link and link[-1] == '/':
        link += 'index' + ext

    return link

def build_path(tree, path):
    tree.path = path
    for i, child in enumerate(tree.children, 1):
        build_path(child, ".".join([path, str(i)]) if path else str(i))

def make_toc(node, ext, short_index):
    toc = ['**Table of Contents**\n']
    depth = node.depth()
    for n in node:
        if n is not node:
            link = make_link(n, from_=node, ext=ext, short_index=short_index)
            title = n.title
            indentation =  n.depth() - depth - 1
            toc.append(('    ' * indentation) + '0. [%s](%s)\n' % (title, link))
    toc.append('\n')
    if len(toc) == 2:
        return []
    return toc

def make_tree(directory):
    backup = os.getcwd()
    os.chdir(directory)
    tree = build_branch('')
    build_path(tree, '')
    os.chdir(backup)
    return tree

def build_md_main(directory, ext, repo, root, short_index, **settings):
    tree = make_tree(directory)

    id_map = []
    for node in tree:
        id_map.append((node.id, node))

    for n in tree:
        n.content = make_toc(n, ext, short_index) + n.content

    for n in tree:
        n.content.insert(0,
            " <a class='iab-edit' href='https://github.com/%s/edit/master"
            "/%s/%s#L%d' target='_blank'>[edit]</a>\n\n" % (repo, root, n.file, n.start))

    for n in tree:
        spath = n.path.split('.', 2)
        if len(spath) == 3:
            n.content.insert(0, "<a name='%s'></a>" % spath[-1])

    for node in tree:
        rel_depth = node.depth()
        if node.path:
            heading = "[%s](alias://%s)" % (node.path, node.id), node.title
        else:
            heading = '', node.title
        if rel_depth < 3:
            node.content.insert(0, ('# %s %s' % heading))
        else:
            node.content.insert(0, ('#' * (node.depth() - 2))+' %s %s' % heading)

    for node in tree:
        node.content = ''.join(node.content)
        for id, n in id_map:
            a, b = 'alias://%s' % id, make_link(n, from_=node, ext=ext, short_index=short_index)
            node.content = node.content.replace(a, b)

    out = []

    out.append(('', [tree.content]))
    for i, unit in enumerate(tree.children, 1):
        chapters = [unit.content]
        out.append((str(i), chapters))
        for chapter in unit.children:
            chapters.append(''.join([section.content for section in chapter]))

    return out




def get_output_fp(output_dir, path, ext):

    output_fn = path + ext
    output_fp = os.path.join(output_dir, output_fn)
    return output_fp


def build_iab_main(input_dir, output_dir, out_format, ext, css=None):
    """ Convert md sources to readable book content, maintaining dir structure.

        A few additional processing steps happen here:
         * Add Table of Contents to the top of each section.
         * Create links from sha1 aliases.

        Parameters
        ----------
        input_dir : str
            Root path for the markdown files.
        output_dir : str
            Root path for the output files.
        out_format : str
            The ipymd format that output files should be written in (for example,
            ``notebook``).
        ext : str
            The extension to use for output files.

    """
    # Walk the input root directory. We only care about root and files
    # inside this loop (nothing happens with dirs).
    for unit_number, (unit, chapters) in enumerate(input_dir):
        # Iterate over the files in the current root.
        if unit_number == 0:
            unit_path = ''
        else:
            unit_path = str(unit_number) + '/'
        for chapter_number, content_md in enumerate(chapters):
            if chapter_number == 0:
                chapter_path = 'index'
            else:
                chapter_path = str(chapter_number)
            path = '%s%s' % (unit_path, chapter_path)
            # Convert it from markdown
            output_s = ipymd.convert(content_md, from_='markdown', to='notebook')
            # define the output filepath
            output_fp = get_output_fp(output_dir, path, ext)
            try:
                os.makedirs(os.path.split(output_fp)[0])
            except OSError:
                pass

            # write the output ipynb
            IPython.nbformat.write(output_s, output_fp)

    if out_format == 'html' or out_format == 's3':
        c = Config()
        c.ExecutePreprocessor.timeout = 600
        html_exporter = HTMLExporter(preprocessors=['IPython.nbconvert.preprocessors.execute.ExecutePreprocessor'],
                                     config=c)

        for root, dirs, files in os.walk(output_dir):
            if css:
                shutil.copy(css, os.path.join(root, 'custom.css'))
            for f in files:
                html_out, _ = html_exporter.from_filename(os.path.join(root, f))
                output_fn = os.path.splitext(f)[0] + ext
                output_fp = os.path.join(root, output_fn)
                open(output_fp, 'w').write(html_out)



def biab_notebook(input_dir, output_dir, out_format, css=None):
    format_ext_map = {'notebook' : '.ipynb', 'html': '.html', 's3': ''}
    # Find the file extension that should be used for this format. If we get
    # a KeyError, this is an unknown output format.
    try:
        ext = format_ext_map[out_format]
    except KeyError:
        raise ValueError("Unknown output format: %s. Known formats are: "
                         "%s" % (out_format, ", ".join(list(format_ext_map.keys()))))

    with open(os.path.join(input_dir, 'config.yaml')) as f:
        settings = yaml.load(f.read())


    short_index = out_format == 'html' or out_format == 's3'
    built_md = build_md_main(input_dir, ext, short_index=short_index, **settings)
    build_iab_main(built_md, output_dir, out_format, ext, css=css)

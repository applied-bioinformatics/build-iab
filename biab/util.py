#!/usr/bin/env python

# ----------------------------------------------------------------------------
# Copyright (c) 2013--, IAB development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
# ----------------------------------------------------------------------------

from sys import argv
import os
import tempfile
import CommonMark as cm
import ipymd
import IPython
from six.moves.html_parser import HTMLParser
import yaml
import shutil
import csv


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
        self.line = 1
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
            current_node.line = node.start_line
            current_node.file = fp
            current_node.content = lines[node.start_line:]
            current_node.content.insert(0,
                "\n[Edit on GitHub](https://github.com/gregcaporaso/proto-iab/edit"
                "/master/book/%s#L%d)\n" % (current_node.file, current_node.line))
            last_node.content = last_node.content[:node.start_line - last_node.line]
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

def build_path(tree, path):
    tree.path = path
    for i, child in enumerate(tree.children, 1):
        build_path(child, ".".join([path, str(i)]) if path else str(i))

def build_md_main(directory):
    os.chdir(directory)
    tree = build_branch('')
    build_path(tree, '')
    for n in tree:
        spath = n.path.split('.', 2)
        if len(spath) == 3:
            n.content.insert(0, "<a name='%s'></a>" % spath[-1])

    for node in tree:
        rel_depth = node.depth()
        if rel_depth < 3:
            node.content.insert(0, ('# %s ' % node.title))
        else:
            node.content.insert(0, ('#' * (node.depth() - 2))+' %s ' % node.title)


    out = []

    out.append(('', [''.join(tree.content)]))
    for i, unit in enumerate(tree.children, 1):
        chapters = [''.join(unit.content)]
        out.append((str(i), chapters))
        for chapter in unit.children:
            chapters.append(''.join([''.join(section.content) for section in chapter]))

    build_map = []
    for node in tree:
        #HACK
        path = node.path
        path = path.replace('.', '/', 1).replace('.', '#', 1)
        build_map.append([node.id, path, node.title])

    return out, build_map

def _skipdir(dir):
    return '.ipynb_checkpoints' in dir

_format_ext_map = {'notebook' : 'ipynb'}

toc = """## Table of Contents

%s

"""

def parse_build_map(f):
    result = []
    for line in f:
        result.append(line.strip().split(','))
    return result

def build_link(unit=None, chapter=None, section=None, file_ext=None):
    if unit is None:
        return './'
    elif chapter is None:
        return './%s' % unit
    elif file_ext is None:
        link = './%s/%s' % (unit, chapter)
    else:
        link = './%s/%s%s%s' % (unit, chapter, os.path.extsep, file_ext)

    if section is None:
        return link
    else:
        return '%s#%s' % (link, section)

def link_from_path(path, file_ext):

    if '/' in path:
        unit, chapter_section = path.split('/')
    else:
        return build_link(path, chapter=None, section=None, file_ext=file_ext)

    if '#' in chapter_section:
        chapter, section = chapter_section.split('#')
    else:
        return build_link(unit, chapter=chapter_section, section=None, file_ext=file_ext)

    return build_link(unit, chapter, section, file_ext)

def build_toc_md(build_map, root_path=None, file_ext=None):
    """ Build a markdown table of contents of links

        Parameters
        ----------
        root_path : str, None
            The root path to start the table of contents from. If None, start
            at the book's root.
        file_ext : str
            The file extension to append to chapters, if the links that are
            generated need to include a filename extension.

        Returns
        -------
        str
            Markdown text that can be printed as a table of contents.

    """
    lines = []
    if root_path is None:
        search_prefix = ''
    else:
        search_prefix = root_path
    for sha, path, title in build_map:
        if path.startswith(search_prefix):
            indentation = path.count('/') + path.count('.')
            link = link_from_path(path, file_ext)
            lines.append(' ' * indentation + '* ' + '[%s](%s)' % (title, link))
    return '\n'.join(lines)

def resolve_md_links(build_map, md, path, link_ext):
    for sha, path, title in build_map:
        md.replace('alias://%s' % sha, link_from_path(path, file_ext=link_ext))
    return md

def add_toc_to_md(build_map, md, path, link_ext):
    lines = md.split('\n')
    lines = [lines[0]] + [toc % build_toc_md(build_map, root_path=path, file_ext=link_ext)] + lines[1:]
    return '\n'.join(lines)

def fp_to_path(fp):
    fields = fp.split(os.path.sep)[1:]
    if fields[-1] == 'index.md':
        fields = fields[:-1]
    else:
        fields[-1] = os.path.splitext(fields[-1])[0]
    return '/'.join(fields)

def get_output_fp(output_root, input_fp, output_ext):
    print input_fp, output_root
    input_dir, input_fn = os.path.split(input_fp)
    input_basename = os.path.splitext(input_fn)[0]
    input_dirs = input_dir.split(os.path.sep)

    output_fn = os.path.extsep.join([input_basename, output_ext])
    output_dir = os.path.sep.join([output_root] + input_dirs[1:])
    output_fp = os.path.join(output_dir, output_fn)
    return output_dir, output_fp


def build_iab_main(input_root, output_root, out_format, build_map,
                   dry_run=False, format_ext_map=_format_ext_map,
                   include_link_ext=True):
    """ Convert md sources to readable book content, maintaining dir structure.

        A few additional processing steps happen here:
         * Add Table of Contents to the top of each section.
         * Create links from sha1 aliases.

        Parameters
        ----------
        input_root : str
            Root path for the markdown files.
        output_root : str
            Root path for the output files.
        out_format : str
            The ipymd format that output files should be written in (for example,
            ``notebook``).
        dry_run : bool, optional
            If ``True``, don't actually create new directories or write files.
        format_ext_map : dict, optional
            Dict mapping ipymd format to file extension.
        include_link_ext : bool, optional
            If ``True``, when creating links include file extensions.

    """

    # Find the file extension that should be used for this format. If we get
    # a KeyError, this is an unknown output format.
    try:
        output_ext = format_ext_map[out_format]
    except KeyError:
        raise ValueError("Unknown output format: %s. Known formats are: "
                         "%s" % (out_format, ", ".join(format_ext_map.keys())))
    # If links should include the file extension, define that here. Otherwise,
    # it is set to None, and there will be no extension included in the links.
    if include_link_ext:
        link_ext = output_ext
    else:
        link_ext = None

    # Walk the input root directory. We only care about root and files
    # inside this loop (nothing happens with dirs).
    for root, dirs, files in os.walk(input_root):
        # Determine if current root is one that we want to skip (e.g., a hidden
        # directory). If so, move on...
        if _skipdir(root): continue
        print root, files
        # Iterate over the files in the current root.
        for input_fn in files:
            # Get the full path
            input_fp = os.path.join(root, input_fn)
            # read it into a string
            input_md = open(input_fp).read()
            # get the book path for this file
            path = fp_to_path(input_fp)
            # apply the processing steps
            input_md = resolve_md_links(build_map, input_md, path, link_ext)
            input_md = add_toc_to_md(build_map, input_md, path, link_ext)
            # Convert it from markdown
            output_s = ipymd.convert(input_md, from_='markdown', to=out_format)
            # define the output filepath
            output_dir, output_fp = get_output_fp(output_root, input_fp, output_ext)
            print output_dir, output_fp
            # write the output notebook
            #IPython.nbformat.write(output_s, output_fp)

def biab_notebook(input_dir, output_dir):
    built_md_dir, build_map = build_md_main(input_dir)
    print built_md_dir
    build_iab_main(built_md_dir, output_dir, 'notebook', build_map)

if __name__ == "__main__":
    input_dir = argv[1]
    output_dir = os.path.abspath(argv[2])
    biab_notebook(input_dir, output_dir)

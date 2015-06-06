#!/usr/bin/env python

import os
import fnmatch
import CommonMark as cm
from os.path import splitext
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
    if splitext(fp)[1] != '.md':
        raise ValueError("Not a markdown file: %r" % fp)

    with open(fp) as f:
        lines = f.readlines()
        ast = cm.DocParser().parse(''.join(lines))

    root = Node()
    root.file = fp
    current_node = root
    scribe_node = root

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

            # Be at the correct node:
            current_node.title = node.inline_content[0].c.strip()
            parser = IDFinder()
            parser.feed(node.inline_content[1].c.strip())
            parser.close()
            current_node.id = parser.get_id()
            current_node.line = node.start_line
            current_node.file = fp
            current_node.content = lines[node.start_line:]
            current_node.content.insert(0,
                "\n[Edit on GitHub](https://github.com/gregcaporaso/proto-iab/edit"
                "/master/book/%s#L%d)\n" % (current_node.file, current_node.line))
            scribe_node.content = lines[scribe_node.line:node.start_line-1]
            scribe_node.content.insert(0,
                "\n[Edit on GitHub](https://github.com/gregcaporaso/proto-iab/edit"
                "/master/book/%s#L%d)\n" % (scribe_node.file, scribe_node.line))
            scribe_node = current_node

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

def main(directory):
    os.chdir(directory)
    tree = build_branch('')
    build_path(tree, '')
    for n in tree:
        spath = n.path.split('.', 2)
        if len(spath) == 3:
            n.content.insert(0, "<a name='%s'></a>" % spath[2])

    for node in tree:
        rel_depth = node.depth()
        if rel_depth < 3:
            node.content.insert(0, ('# %s ' % node.title))
        else:
            node.content.insert(0, ('#' * (node.depth() - 2))+' %s ' % node.title)

    os.chdir('..')
    shutil.rmtree('built-md', ignore_errors=True)
    os.mkdir('built-md')
    os.chdir('built-md')

    with open('index.md', 'w') as f:
        f.write(''.join(tree.content))
    for i, unit in enumerate(tree.children, 1):
        folder = str(i)
        os.mkdir(folder)

        with open(os.path.join(folder, 'index.md'), 'w') as f:
            f.write(''.join(unit.content))
        for k, chapter in enumerate(unit.children, 1):
            with open(os.path.join(folder, str(k) + '.md'), 'w') as f:
                for section in chapter:
                    f.write(''.join(section.content))

    with open('map.csv', 'w') as f:
        writer = csv.writer(f)
        for node in tree:
            writer.writerow([node.id, node.path, node.title])


    return tree


if __name__ == "__main__":
    main("./book")

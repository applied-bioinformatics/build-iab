# proto-iab
Prototyping project structure for An Introduction to Applied Bioinformatics

# URLs

URLs will look like the following for the hosted notebooks:

http://readIAB.org/book/latest/2/3/#1.1.2

where:
* ``latest`` is version of book
* ``2`` is unit of book
* ``3`` is chapter of unit
* ``1.2.2`` is sub-sub-section of chapter

# Notes for build process

```bash
$ pwd
/Users/caporaso/code/proto-iab
$ ./build-md.py
$ ./build-iab built-md/ book-ipynb notebook built-md/map.csv
```

# Build workflow

* Traverse book recursively (``os.path.walk``)
 * Build tree of the book structure, where each tip is the most granular possible component (e.g., sub-sub-section sometimes, but other times maybe just section). Every node should in the tree has the following metadata.
    * Source file.
    * sha1 representing that node.
    * content as markdown
    * name (strip this from markdown, it will be added back later)
 * Ensure all sha1s are unique. Build the mapping of sha1 to URL.
 * For every section chapter and beneath:
  * Prepend the header, new line, anchor, new line, "Edit on GitHub" link, and new line.
 * Do depth-first pre-order traversal catting all content into chapter markdown files.
 * Do link replace: ``alias://<sha1>`` becomes actual links. This process will differ for notebooks that are being hosted and notebooks that are being zipped for local execution (since the local ones will need ``.ipynb``).
 * Generate ipython notebooks and execute them. ``nbconvert`` to HTML (for the hosted ipynbs) or zip (for the local execution notebooks).

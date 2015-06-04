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

# Notes for build process

## Convert the md to ipynb

```python
import ipymd
import IPython

s = ipymd.convert(open('my-markdown.md'), from_='markdown', to='notebook')
IPython.nbformat.write(s, 'getting-started.ipynb')
```

## One-liner to get sha1 tags

```bash
$ date | shasum | head -c 6 | awk '{print "<link src=\""$1"\"/>"}'
<link src="681472"/>
```

## Edit on GitHub links

All sections will have *Edit on GitHub* links just below the section's heading that will take users directly to the editable text on GitHub where they'll be able to submit a pull request. This, in combination with more granular text, will effectively allow us to crowd-source the copy editing (it's currently very difficult to get text edits from users due to the difficultly of diff'ing IPython Notebooks combined with the huge amount of content in each IPython Notebook).

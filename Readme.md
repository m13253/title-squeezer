Title-Squeezer
==============

This is a simple Python program that reads in an HTML page, parses it and try
to figure out the title and description of this page.

This program tries to read as less as possible and consume less CPU and memory
than other HTML parsers.


Usage
-----

```bash
curl -L -s --compressed https://www.yahoo.com/ | ./title_squeezer.py -v
```

Using `-v` will print out every HTML tag it successfully parses.


Programmable Interface
----------------------

```python
>>> import title_squeezer
# First construct a Squeezer instance
>>> squeezer = title_squeezer.Squeezer()
# Then feed in HTML data
>>> squeezer.feed(b'<html><head><title>Hello wo')
Title(
    enough=False,
    title='Hello wo',
    description=None,
    charset=None
)
# Feed more data
>>> squeezer.feed(b'rld!</title></head>')
Title(
    enough=True,
    title='Hello world!',
    description=None,
    charset=None
)
```


License
-------

The original author of this program, Title-Squeezer, is StarBrilliant.
This file is released under General Public License version 3.
You should have received a copy of General Public License text alongside with
this program. If not, you can obtain it at http://gnu.org/copyleft/gpl.html .
This program comes with no warranty, the author will not be resopnsible for
any damage or problems caused by this program.

#!/usr/bin/env python3

# The original author of this program, Title-Squeezer, is StarBrilliant.
# This file is released under General Public License version 3.
# You should have received a copy of General Public License text alongside with
# this program. If not, you can obtain it at http://gnu.org/copyleft/gpl.html .
# This program comes with no warranty, the author will not be resopnsible for
# any damage or problems caused by this program.

import enum
import sys


class Title:
    def __init__(self, enough: bool=False, title: str=None, description: str=None, charset: str='UTF-8'):
        self.enough = enough
        self.title = title
        self.description = description
        self.charset = charset

        if title is not None:
            self.title_decode = title.decode(charset, 'replace')
        else:
            self.title_decode = None
        if description is not None:
            self.description_decode = description.decode(charset, 'replace')
        else:
            self.description_decode = None

    def __repr__(self):
        return 'Title(enough=%r, title=%r, description=%r, charset=%r)' % (self.enough, self.title_decode, self.description_decode, self.charset)


class State(enum.Enum):

    content = 0

    #  <a href=# style="color: red">Content</a>
    #  0123    4 3     45          40       1620
    tag = 1
    tagname = 2
    attrname = 3
    attrvalue = 4
    attrquote = 5
    tagslash = 6

    #  <!-- Comment -->
    #                11
    #  01789         010
    tagbang = 7
    tagbangdash = 8
    comment = 9
    commentdash = 10
    commentdashdash = 11

    #  <script>alert("hi")</script>
    #          1           11111112
    #  012     2           345678900
    script = 12
    scripttag = 13
    scripttagslash = 14
    scripttagslashs = 15
    scripttagslashsc = 16
    scripttagslashscr = 17
    scripttagslashscri = 18
    scripttagslashscrip = 19
    scripttagslashscript = 20

    #  <style>p { color: red; }</style>
    #         2                 2222222
    #  012    1                 23456780
    style = 21
    styletag = 22
    styletagslash = 23
    styletagslashs = 24
    styletagslashst = 25
    styletagslashsty = 26
    styletagslashstyl = 27
    styletagslashstyle = 28


class Squeezer:
    def __init__(self):
        self.state = State.content
        self.lasttag = b''
        self.lastattr = b''
        self.lastvalue = None
        self.lastattrs = None

        self.inside_title = False
        self.title = None
        self.description = None
        self.charset = 'UTF-8'
        self.head_done = False

    def feed(self, data: bytes=b'') -> Title:
        for c in data:
            c = bytes((c,))

            if self.state == State.content:
                if c == b'<':
                    self.state = State.tag
                    self.lasttag = b''
                    self.lastattr = b''
                    self.lastvalue = None
                else:
                    self._dispatch_content(c)

            elif self.state == State.tag:
                if self._isspace(c):
                    self._dispatch_content(b'<' + c)
                    self.state = State.content
                elif c == b'<':
                    self._dispatch_content(b'<')
                elif c == b'>':
                    self._dispatch_content(b'<>')
                    self.state = State.content
                elif c == b'!':
                    self.state = State.tagbang
                elif c == b'/':
                    self.state = State.tagslash
                else:
                    self.lasttag = c
                    self.state = State.tagname

            elif self.state == State.tagname:
                if self._isspace(c):
                    self._start_tag(self.lasttag)
                    self.state = State.attrname
                elif c == b'<':
                    self.lasttag = b''
                    self.state = State.tag
                elif c == b'>':
                    self._start_tag(self.lasttag)
                    self._finish_tag(self.lasttag)
                    if self.lasttag.lower() == b'script':
                        self.state = State.script
                    elif self.lasttag.lower() == b'style':
                        self.state = State.style
                    else:
                        self.state = State.content
                else:
                    self.lasttag += c

            elif self.state == State.attrname:
                if self._isspace(c):
                    self._dispatch_attr(self.lasttag, self.lastattr)
                    self.lastattr = b''
                    self.lastvalue = None
                elif c == b'<':
                    self._dispatch_attr(self.lasttag, self.lastattr)
                    self.lasttag = b''
                    self.lastattr = b''
                    self.lastvalue = None
                    self.state = State.tag
                elif c == b'>':
                    self._dispatch_attr(self.lasttag, self.lastattr)
                    self._finish_tag(self.lasttag)
                    if self.lasttag.lower() == b'script':
                        self.state = State.script
                    elif self.lasttag.lower() == b'style':
                        self.state = State.style
                    else:
                        self.state = State.content
                elif c == b'=':
                    self.lastvalue = b''
                    self.state = State.attrvalue
                else:
                    self.lastattr += c

            elif self.state == State.attrvalue:
                if self._isspace(c):
                    self._dispatch_attr(self.lasttag, self.lastattr, self.lastvalue)
                    self.lastattr = b''
                    self.lastvalue = None
                    self.state = State.attrname
                elif c == b'<':
                    self._dispatch_attr(self.lasttag, self.lastattr, self.lastvalue)
                    self.lasttag = b''
                    self.lastattr = b''
                    self.lastvalue = None
                    self.state = State.tag
                elif c == b'>':
                    self._dispatch_attr(self.lasttag, self.lastattr, self.lastvalue)
                    self._finish_tag(self.lasttag)
                    if self.lasttag.lower() == b'script':
                        self.state = State.script
                    elif self.lasttag.lower() == b'style':
                        self.state = State.style
                    else:
                        self.state = State.content
                elif c == b'"':
                    self.state = State.attrquote
                else:
                    self.lastvalue += c

            elif self.state == State.attrquote:
                if c == b'"':
                    self.state = State.attrvalue
                else:
                    self.lastvalue += c

            elif self.state == State.tagslash:
                if self._isspace(c):
                    self.lasttag = b'/'
                    self._start_tag(self.lasttag)
                    self.state = State.attrname
                elif c == b'<':
                    self._dispatch_content(b'</')
                    self.state = State.tag
                elif c == b'>':
                    self.lasttag = b'/'
                    self._start_tag(self.lasttag)
                    self._finish_tag(self.lasttag)
                    self.state = State.content
                else:
                    self.lasttag = b'/' + c
                    self.state = State.tagname

            elif self.state == State.tagbang:
                if self._isspace(c):
                    self.lasttag = b'!'
                    self._start_tag(self.lasttag)
                    self.state = State.attrname
                elif c == b'<':
                    self._dispatch_content(b'<!')
                    self.state = State.tag
                elif c == b'>':
                    self.lasttag = b'!'
                    self._start_tag(self.lasttag)
                    self._finish_tag(self.lasttag)
                    self.state = State.content
                elif c == b'-':
                    self.state = State.tagbangdash
                else:
                    self.lasttag = b'!' + c
                    self.state = State.tagname

            elif self.state == State.tagbangdash:
                if self._isspace(c):
                    self.lasttag = b'!-'
                    self._start_tag(self.lasttag)
                    self.state = State.attrname
                elif c == b'<':
                    self._dispatch_content(b'<!-')
                    self.state = State.tag
                elif c == b'>':
                    self.lasttag = b'!-'
                    self._start_tag(self.lasttag)
                    self._finish_tag(self.lasttag)
                    self.state = State.content
                elif c == b'-':
                    self.state = State.comment
                else:
                    self.lasttag = b'!-' + c
                    self.state = State.tagname

            elif self.state == State.comment:
                if c == b'-':
                    self.state = State.commentdash
            elif self.state == State.commentdash:
                if c == b'-':
                    self.state = State.commentdashdash
                else:
                    self.state = State.comment
            elif self.state == State.commentdashdash:
                if c == b'>':
                    self.state = State.content
                else:
                    self.state = State.comment

            elif self.state == State.script:
                if c == b'<':
                    self.state = State.scripttag
            elif self.state == State.scripttag:
                if c == b'/':
                    self.state = State.scripttagslash
                else:
                    self.state = State.script
            elif self.state == State.scripttagslash:
                if c in (b'S', b's'):
                    self.state = State.scripttagslashs
                else:
                    self.state = State.script
            elif self.state == State.scripttagslashs:
                if c in (b'C', b'c'):
                    self.state = State.scripttagslashsc
                else:
                    self.state = State.script
            elif self.state == State.scripttagslashsc:
                if c in (b'R', b'r'):
                    self.state = State.scripttagslashscr
                else:
                    self.state = State.script
            elif self.state == State.scripttagslashscr:
                if c in (b'I', b'i'):
                    self.state = State.scripttagslashscri
                else:
                    self.state = State.script
            elif self.state == State.scripttagslashscri:
                if c in (b'P', b'p'):
                    self.state = State.scripttagslashscrip
                else:
                    self.state = State.script
            elif self.state == State.scripttagslashscrip:
                if c in (b'T', b't'):
                    self.state = State.scripttagslashscript
                else:
                    self.state = State.script
            elif self.state == State.scripttagslashscript:
                if c == b'>':
                    self.lasttag = b'/script'
                    self._start_tag(self.lasttag)
                    self._finish_tag(self.lasttag)
                    self.state = State.content
                else:
                    self.state = State.script

            elif self.state == State.style:
                if c == b'<':
                    self.state = State.styletag
            elif self.state == State.styletag:
                if c == b'/':
                    self.state = State.styletagslash
                else:
                    self.state = State.style
            elif self.state == State.styletagslash:
                if c in (b'S', b's'):
                    self.state = State.styletagslashs
                else:
                    self.state = State.style
            elif self.state == State.styletagslashs:
                if c in (b'T', b't'):
                    self.state = State.styletagslashst
                else:
                    self.state = State.style
            elif self.state == State.styletagslashst:
                if c in (b'Y', b'y'):
                    self.state = State.styletagslashsty
                else:
                    self.state = State.style
            elif self.state == State.styletagslashsty:
                if c in (b'L', b'l'):
                    self.state = State.styletagslashstyl
                else:
                    self.state = State.style
            elif self.state == State.styletagslashstyl:
                if c in (b'E', b'e'):
                    self.state = State.styletagslashstyle
                else:
                    self.state = State.style
            elif self.state == State.styletagslashstyle:
                if c == b'>':
                    self.lasttag = b'/style'
                    self._start_tag(self.lasttag)
                    self._finish_tag(self.lasttag)
                    self.state = State.content
                else:
                    self.state = State.style

        return Title(
            self.head_done,
            self.title,
            self.description,
            self.charset
        )

    @staticmethod
    def _isspace(c: bytes) -> bool:
        return c in (b'\x09', b'\x0a', b'\x0c', b'\x0d', b'\x20')

    def _dispatch_content(self, content: bytes):
        if self.inside_title:
            if self.title is None:
                self.title = content
            else:
                self.title += content

    def _start_tag(self, tag: bytes):
        if not tag:
            return
        self.lastattrs = {}
        sys.stderr.write('<%s' % tag.decode(self.charset, 'replace'))
        if tag.lower() == b'title':
            self.inside_title = True
        elif tag.lower() == b'/title':
            self.inside_title = False
        elif tag.lower() == b'/head':
            self.head_done = True
        elif tag.lower() == b'body':
            self.head_done = True

    def _dispatch_attr(self, tag: bytes, attr: bytes, value: [bytes, None]=None):
        if not attr:
            return
        assert tag == self.lasttag
        self.lastattrs[attr.lower()] = value
        if value is not None:
            sys.stderr.write('\n  %s="%s"' % (
                attr.decode(self.charset, 'replace'),
                value.decode(self.charset, 'replace')
            ))
        else:
            sys.stderr.write('\n  %s' % attr.decode(self.charset, 'replace'))

    def _finish_tag(self, tag: bytes):
        if not tag:
            return
        assert tag == self.lasttag
        assert self.lastattrs is not None
        if tag.lower() == b'meta':
            if b'charset' in self.lastattrs:
                self._set_charset(self.lastattrs[b'charset'])
            if b'http-equiv' in self.lastattrs:
                if self._lower(self.lastattrs[b'http-equiv']) == b'content-type':
                    content = self.lastattrs.get(b'content')
                    if content:
                        content_splitted = content.split(b';')
                        for content_item in content_splitted:
                            content_kv = content_item.split(b'=', 1)
                            if len(content_kv) == 2:
                                content_key = content_kv[0].strip()
                                content_value = content_kv[1].strip()
                                if content_key.lower() == b'charset':
                                    self._set_charset(content_value)
            if b'name' in self.lastattrs:
                if self._lower(self.lastattrs[b'name']) == b'description':
                    if b'content' in self.lastattrs:
                        self.description = self.lastattrs[b'content']
        self.lastattrs = None
        sys.stderr.write('>\n')

    def _set_charset(self, charset: bytes) -> bool:
        if not charset:
            return
        charset = charset.strip().decode('UTF-8', 'replace')
        try:
            b'A'.decode(charset, 'replace')
            self.charset = charset
        except LookupError:
            return False
        return True

    @staticmethod
    def _lower(s: [bytes, str, None]) -> [bytes, str, None]:
        if s is None:
            return None
        else:
            return s.lower()

def main():
    squeezer = Squeezer()
    while True:
        data = sys.stdin.buffer.read(2048)
        if not data:
            break
        result = squeezer.feed(data)
        if result.enough:
            print()
            print(result)
            break


if __name__ == '__main__':
    main()

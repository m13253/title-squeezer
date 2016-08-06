#!/usr/bin/env python3

# The original author of this program, Title-Squeezer, is StarBrilliant.
# This file is released under General Public License version 3.
# You should have received a copy of General Public License text alongside with
# this program. If not, you can obtain it at http://gnu.org/copyleft/gpl.html .
# This program comes with no warranty, the author will not be resopnsible for
# any damage or problems caused by this program.


import enum
import json
import sys


class Title:
    def __init__(self, enough: bool, title: str, description: str, charset: str, eff_charset: str):
        self.enough = enough
        self.title = title
        self.description = description
        self.charset = charset

        if title is not None:
            self.title_decode = title.decode(eff_charset, 'replace')
        else:
            self.title_decode = None
        if description is not None:
            self.description_decode = description.decode(eff_charset, 'replace')
        else:
            self.description_decode = None

    def __str__(self):
        return json.dumps({
            "enough": self.enough, "title": self.title_decode, "description": self.description_decode, "charset": self.charset
        }, ensure_ascii=False, indent=4)

    def __repr__(self):
        return 'Title(\n    enough=%r,\n    title=%r,\n    description=%r,\n    charset=%r\n)' % (
            self.enough, self.title_decode, self.description_decode, self.charset
        )


@enum.unique
class State(enum.Enum):

    content = 0

    #  <a href=# style="color: red">Content</a>
    #   222    2 2     22          2        222
    #  0024    6 4     67          60       0120
    #  <img src=photo.jpg />
    #   2   2   2         22
    #  00   2   4         240
    tag            = 20
    tagslash       = 21
    tagname        = 22
    tagnameslash   = 23
    attrname       = 24
    attrnameslash  = 25
    attrvalue      = 26
    attrquote      = 27
    attrvalueslash = 28

    #  <!-- Comment -->
    #   2444         44
    #  00012         340
    tagbang         = 40
    tagbangdash     = 41
    comment         = 42
    commentdash     = 43
    commentdashdash = 44

    #  <script>alert("hi")</script>
    #   22     6           66666666
    #  002     0           123456780
    script               = 60
    scripttag            = 61
    scripttagslash       = 62
    scripttagslashs      = 63
    scripttagslashsc     = 64
    scripttagslashscr    = 65
    scripttagslashscri   = 66
    scripttagslashscrip  = 67
    scripttagslashscript = 68

    #  <style>p { color: red; }</style>
    #   22    8                 8888888
    #  002    0                 12345670
    style              = 80
    styletag           = 81
    styletagslash      = 82
    styletagslashs     = 83
    styletagslashst    = 84
    styletagslashsty   = 85
    styletagslashstyl  = 86
    styletagslashstyle = 87


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
        self.charset = None
        self.eff_charset = 'UTF-8'
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
                    self._dispatch_content(b'&lt;' + c)
                    self.state = State.content
                elif c == b'<':
                    self._dispatch_content(b'&lt;')
                elif c == b'>':
                    self._dispatch_content(b'&lt;&gt;')
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
                    self._start_tag(self.lasttag)
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
                elif c == b'/':
                    self.state = State.tagnameslash
                else:
                    self.lasttag += c

            elif self.state == State.tagnameslash:
                if self._isspace(c):
                    self.lasttag += b'/'
                    self._start_tag(self.lasttag)
                    self.state = State.attrname
                elif c == b'<':
                    self._start_tag(self.lasttag)
                    self.lasttag = b''
                    self.state = State.tag
                elif c == b'>':
                    self._start_tag(self.lasttag)
                    self._finish_tag(self.lasttag)
                    self.state = State.content
                elif c == b'/':
                    self.lasttag += b'/'
                else:
                    self.lasttag += c
                    self.state = State.tagname

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
                elif c == b'/':
                    self.state = State.attrnameslash
                elif c == b'=':
                    self.lastvalue = b''
                    self.state = State.attrvalue
                else:
                    self.lastattr += c

            elif self.state == State.attrnameslash:
                if self._isspace(c):
                    self.lastattr += b'/'
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
                    self.state = State.content
                elif c == b'/':
                    self.lastattr += b'/'
                elif c == b'=':
                    self.lastvalue = b''
                    self.state = State.attrvalue
                else:
                    self.lastattr += c
                    self.state = State.attrname

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
                elif c == b'/':
                    self.state = State.attrvalueslash
                elif c == b'"':
                    self.state = State.attrquote
                else:
                    self.lastvalue += c

            elif self.state == State.attrquote:
                if c == b'"':
                    self.state = State.attrvalue
                else:
                    self.lastvalue += c

            elif self.state == State.attrvalueslash:
                if self._isspace(c):
                    self.lastvalue += b'/'
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
                elif c == b'/':
                    self.lastvalue += b'/'
                elif c == b'"':
                    self.state = State.attrquote
                else:
                    self.lastvalue += c
                    self.state = State.attrvalue

            elif self.state == State.tagslash:
                if self._isspace(c):
                    self.lasttag = b'/'
                    self._start_tag(self.lasttag)
                    self.state = State.attrname
                elif c == b'<':
                    self._dispatch_content(b'&lt;/')
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
                    self._dispatch_content(b'&lt;!')
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
                    self._dispatch_content(b'&lt;!-')
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
            self.charset,
            self.eff_charset
        )

    @staticmethod
    def _isspace(c: bytes) -> bool:
        return c in (b'\x09', b'\x0a', b'\x0c', b'\x0d', b'\x20')

    @staticmethod
    def _lower(s: [bytes, str, None]) -> [bytes, str, None]:
        if s is None:
            return None
        else:
            return s.lower()

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
        sys.stderr.write('<%s' % tag.decode(self.eff_charset, 'replace'))
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
                attr.decode(self.eff_charset, 'replace'),
                value.decode(self.eff_charset, 'replace')
            ))
        else:
            sys.stderr.write('\n  %s' % attr.decode(self.eff_charset, 'replace'))

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
        self.charset = charset
        try:
            b'A'.decode(charset, 'replace')
            self.eff_charset = charset
        except LookupError:
            return False
        return True

    def _is_enough(self) -> bool:
        return self.head_done or (self.title is not None and self.description is not None and self.charset is not None)


def main():
    squeezer = Squeezer()
    while True:
        data = sys.stdin.buffer.read(2048)
        if not data:
            print()
            print(squeezer.feed())
            break
        result = squeezer.feed(data)
        if result.enough:
            print()
            print(result)
            break


if __name__ == '__main__':
    main()

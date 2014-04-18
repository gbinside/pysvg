#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# 
# (c) Roberto Gambuzzi
# Creato:          17/04/2014 07:56:04
# Ultima Modifica: 17/04/2014 07:56:23
# 
# v 0.0.1.0
# 
# file: C:\dropbox\coding dojo\svg python parser\__init__.py
# auth: Roberto Gambuzzi <gambuzzi@gmail.com>
# desc: 
# 
# $Id: __init__.py 17/04/2014 07:56:23 Roberto $
# --------------

from HTMLParser import HTMLParser, HTMLParseError
from pprint import pprint

COMMENT = '__comment__'
DATA = '__data__'
DECL = '__decl__'
TAG = '__tag__'
PI = '__pi__'


class GenericParserException(HTMLParseError):
    pass


def _render_attrs(attrs, prefix=''):
    ret = []
    for k, v in attrs:
        ret.append('%s="%s"' % (k, v))
    return prefix + ' '.join(ret)


class GenericParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.dom = list()
        self._current = [self.dom]
        self._tag_tree = []

    def handle_decl(self, decl):
        self._current[-1].append((DECL, decl))

    def handle_pi(self, data):
        self._current[-1].append((PI, data))

    def handle_comment(self, data):
        self._current[-1].append((COMMENT, data))

    def handle_starttag(self, tag, attrs):
        self._tag_tree.append(tag)
        lista = list()
        self._current[-1].append((TAG, tag, list(attrs), lista))
        self._current.append(lista)

    def handle_endtag(self, tag):
        if tag == self._tag_tree[-1]:
            self._tag_tree.pop()
            self._current.pop()
        else:
            raise GenericParserException('x')

    def handle_data(self, data):
        self._current[-1].append((DATA, data))

    def __repr__(self):
        return repr(self.dom)

    def __str__(self):
        return str(self.dom)

    def to_svg(self, node=None):
        if node is None:
            node = self.dom
        ret = []
        for l in node:
            if l[0] == DECL:
                ret.append('<!' + l[1] + '>')
            elif l[0] == PI:
                ret.append('<?' + l[1] + '>')
            elif l[0] == COMMENT:
                ret.append('<!--' + l[1] + '-->')
            elif l[0] == DATA:
                ret.append(l[1])
            elif l[0] == TAG:
                content = self.to_svg(l[3])
                if content:
                    ret.append('<' + l[1] + _render_attrs(l[2], ' ') + '>' + content + '</' + l[1] + '>')
                else:
                    ret.append('<' + l[1] + _render_attrs(l[2], ' ') + '/>')
        return ''.join(ret)


def test1(parser):
    pprint(parser.dom)


def test2(parser):
    print parser.to_svg()


def test3(parser):
    pass


def test4(parser):
    assert parser.id['svg2'] in parser.dom
    assert parser.id['template'] in parser.id['layer1']
    print parser.to_svg()


def test(argv):
    parser = GenericParser()
    parser.feed(open('test/test.svg', 'rb').read())
    if ('test1' in argv) or not argv:
        test1(parser)
    if ('test2' in argv) or not argv:
        test2(parser)
    if ('test3' in argv) or not argv:
        test3(parser)
    if ('test4' in argv) or not argv:
        test4(parser)


if __name__ == "__main__":
    import sys

    test(sys.argv[1:])

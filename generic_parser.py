#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# (c) Roberto Gambuzzi
# Creato:          17/04/2014 07:56:04
# Ultima Modifica: 18/04/2014 19:57:03
#
# v 0.0.1.1
#
# file: C:\dropbox\coding dojo\svg python parser\generic_parser.py
# auth: Roberto Gambuzzi <gambuzzi@gmail.com>
# desc:
#
# $Id: generic_parser.py 18/04/2014 19:57:03 Roberto $
# --------------
__author__ = 'Roberto'

from HTMLParser import HTMLParser, HTMLParseError

ATTRS = 'attrs'
TAG_NAME = 'tag_name'
VALUE = 'value'
TYPE = 'type'
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
        self._current[-1].append({TYPE: DECL, VALUE: decl})

    def handle_pi(self, data):
        self._current[-1].append({TYPE: PI, VALUE: data})

    def handle_comment(self, data):
        self._current[-1].append({TYPE: COMMENT, VALUE: data})

    def handle_starttag(self, tag, attrs):
        self._tag_tree.append(tag)
        lista = list()
        self._current[-1].append({TYPE: TAG, TAG_NAME: tag, ATTRS: list(attrs), VALUE: lista})
        self._current.append(lista)

    def handle_endtag(self, tag):
        if tag == self._tag_tree[-1]:
            self._tag_tree.pop()
            self._current.pop()
        else:
            raise GenericParserException('x')

    def handle_data(self, data):
        self._current[-1].append({TYPE: DATA, VALUE: data})

    def __repr__(self):
        return repr(self.dom)

    def __str__(self):
        return self._to_string(self.dom)

    def _to_string(self, node):
        ret = []
        for l in node:
            if l[TYPE] == DECL:
                ret.append('<!' + l[VALUE] + '>')
            elif l[TYPE] == PI:
                ret.append('<?' + l[VALUE] + '>')
            elif l[TYPE] == COMMENT:
                ret.append('<!--' + l[VALUE] + '-->')
            elif l[TYPE] == DATA:
                ret.append(l[VALUE])
            elif l[TYPE] == TAG:
                content = self._to_string(l[VALUE])
                attributes = _render_attrs(l[ATTRS], ' ')
                tagname = l[TAG_NAME]
                if content:
                    ret.append('<%s%s>%s</%s>' % (tagname, attributes, content, tagname))
                else:
                    ret.append('<%s%s/>' % (tagname, attributes))
        return ''.join(ret)


def test1(parser):
    assert len(parser.dom) == 6


def test2(parser):
    assert str(parser).strip('\n\r ') == open('test/test_regen.svg', 'r').read().strip('\n\r ')


def main(argv):
    import inspect

    my_name = inspect.stack()[0][3]
    parser = GenericParser()
    parser.feed(open('test/test.svg', 'rb').read())
    for f in argv:
        globals()[f](parser)
    if not argv:
        fs = [globals()[x] for x in globals() if
              inspect.isfunction(globals()[x]) and x.startswith('test') and x != my_name]
        for f in fs:
            print f.__name__
            f(parser)


if __name__ == "__main__":
    import sys

    main(sys.argv[1:])
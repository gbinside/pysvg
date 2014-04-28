#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# 
# (c) Roberto Gambuzzi
# Creato:          17/04/2014 18:38:15
# Ultima Modifica: 28/04/2014 21:22:18
# 
# v 0.0.1.0
# 
# file: C:\Dropbox\coding dojo\svg python parser\node.py
# auth: Roberto Gambuzzi <gambuzzi@gmail.com>
# desc: 
# 
# $Id: node.py 28/04/2014 21:22:18 Roberto $
# --------------

__author__ = 'Roberto'

from generic_parser import GenericParser, TAG_NAME, TYPE, TAG, VALUE, ATTRS
import copy
import re


def traverse(lista):
    for x in lista:
        yield x
        try:
            if x[TYPE] == TAG:
                for y in traverse(x[VALUE]):
                    yield y
        except KeyError:
            pass


class EmptyException(Exception):
    pass


class Nodes(list):
    def __init__(self, iterable=None):
        if iterable:
            super(Nodes, self).__init__(iterable)

    def tag(self, *plist, **params):
        ret = Nodes()
        for elemento in self:
            for match in elemento.tag(*plist, **params):
                ret.append(match)
        return ret

    def id(self, *plist, **params):
        ret = Nodes()
        ret_s = list()
        for elemento in self:
            for match in elemento.id(*plist, **params):
                if str(match) not in ret_s:
                    ret.append(match)
                    ret_s.append(str(match))
        return ret

    def attr(self, name):
        for x in self:
            return x.attr(name)
        raise EmptyException

    def get_dom(self):
        for x in self:
            return x.get_dom()
        raise EmptyException

    def __str__(self):
        ret = ''
        if len(self) < 2:
            for e in self:
                ret = str(e)
        else:
            ret = []
            for e in self:
                ret.append(str(e))
            ret = '\n'.join(ret)
        return ret


class Node(object):
    def __init__(self, lista):
        self.dom = copy.deepcopy(lista)

    def tag(self, tag_name):
        ret = Nodes()
        for elemento in traverse(self.dom):
            try:
                if elemento[TYPE] == TAG:
                    if elemento[TAG_NAME] == tag_name:
                        ret.append(Node([elemento]))
            except KeyError:
                pass
            except TypeError:
                pass
        return ret

    def id(self, _id=None, startswith=None):
        ret = Nodes()
        for elemento in traverse(self.dom):
            try:
                if elemento[TYPE] == TAG:
                    if dict(elemento[ATTRS])['id'] == _id:
                        ret.append(Node([elemento]))
                    if dict(elemento[ATTRS])['id'].startswith(startswith):
                        ret.append(Node([elemento]))
            except KeyError:
                pass
            except TypeError:
                pass
        return ret

    def attr(self, name):
        for x in self.dom:
            return dict(x[ATTRS])[name]
        raise EmptyException

    def value(self):
        return self.get_dom()[VALUE]

    def get_dom(self):
        return self.dom[0]

    def __str__(self):
        return str(GenericParser(self.dom))


#  _____ ___ ___ _____
# |_   _| __/ __|_   _|
#   | | | _|\__ \ | |
#   |_| |___|___/ |_|

def test1(parser):
    node = Node(parser.dom)
    assert len(node.tag('g')) == 2


def test2(parser):
    node = Node(parser.dom)
    assert len(node.tag('rect')) == 2


def test3(parser):
    node = Node(parser.dom)
    assert len(node.tag('text')) == 2


def test4(parser):
    node = Node(parser.dom)
    assert len(node.id('template')) == 1
    assert str(node.id('template')).startswith('<g id="template" inkscape:label="#g4008">')


def test5(parser):
    node = Node(parser.dom)
    assert len(node.tag('g').id('template')) == 1
    assert str(node.tag('g').id('template')).startswith('<g id="template" inkscape:label="#g4008">')


def test6(parser):
    node = Node(parser.dom)
    assert node.id('spaziatura').get_dom() == {'tag_name': 'rect', 'type': '__tag__',
                                               'attrs': [('inkscape:label', '#rect4002'), ('y', '668.4176'),
                                                         ('x', '71.843056'), ('height', '295.33151'),
                                                         ('width', '210.96687'), ('id', 'spaziatura'), ('style',
                                                                                                        'fill:#ffffff;fill-opacity:1;stroke:#000000;stroke-width:0.9941119;stroke-opacity:1')],
                                               'value': []}
    assert node.id('spaziatura').attr('x') == '71.843056'


def test7(parser):
    original_dom = copy.deepcopy(parser.dom)
    node = Node(parser.dom)
    spaziatura = node.id('spaziatura').get_dom()
    width = float(dict(spaziatura[ATTRS])['width'])
    height = float(dict(spaziatura[ATTRS])['height'])
    for elem in node.id('template').get_dom()[VALUE]:
        for x in xrange(3):
            for y in xrange(3):
                if x == 0 and y == 0:
                    continue
                new_obj = copy.deepcopy(elem)
                try:
                    new_obj[ATTRS] = dict(new_obj[ATTRS])
                    new_obj[ATTRS]['inkscape:label'] = str(new_obj[ATTRS]['inkscape:label'] + str(x) + str(y))
                    new_obj[ATTRS]['id'] = str(new_obj[ATTRS]['id'] + str(x) + str(y))
                    try:
                        new_obj[ATTRS]['x'] = float(new_obj[ATTRS]['x']) + width * x
                        new_obj[ATTRS]['y'] = float(new_obj[ATTRS]['y']) - height * y
                    except KeyError:
                        pass
                    try:
                        transform = new_obj[ATTRS]['transform']
                        for pre, _x, mid, _y, post in re.findall(r'(.*?)([0-9.]+)(\D+)([0-9.]+)(\D+)', transform, re.I):
                            new_obj[ATTRS]['transform'] = "%s%s%s%s%s" % (
                                pre, float(_x) + width * x, mid, float(_y) - height * y, post)
                    except KeyError:
                        pass
                    new_obj[ATTRS] = list(new_obj[ATTRS].items())
                    parser.insert(new_obj, after=elem)
                except KeyError:
                    pass
    open('out.svg', 'wb').write(str(parser))
    node2 = Node(parser.dom)
    poker_values = (1, 2, 3, 5, 8, 13, 20, 40, 100)
    elems = node2.id(startswith='poker')
    elems = elems.tag('tspan')
    for i, elem in enumerate(elems):
        elem.value()[0][VALUE] = poker_values[i]
    open('out2.svg', 'wb').write(str(node2))
    parser.dom = original_dom


def main(argv):
    import inspect

    my_name = inspect.stack()[0][3]
    parser = GenericParser()
    parser.load('test/test.svg')
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
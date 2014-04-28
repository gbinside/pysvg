#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# 
# (c) Roberto Gambuzzi
# Creato:          24/04/2014 08:51:23
# Ultima Modifica: 28/04/2014 21:22:05
# 
# v 0.0.1.0
# 
# file: C:\Dropbox\coding dojo\svg python parser\db_parser.py
# auth: Roberto Gambuzzi <gambuzzi@gmail.com>
# desc: 
# 
# $Id: db_parser.py 28/04/2014 21:22:05 Roberto $
# --------------

__author__ = 'Roberto'

from HTMLParser import HTMLParser, HTMLParseError
import sqlite3 as sqlite
import re

#DATABASE = r'c:\temp\temp.sqlite'
DATABASE = r':memory:'
#element types
COMMENT = '__comment__'
DATA = '__data__'
DECL = '__decl__'
TAG = '__tag__'
PI = '__pi__'

SCHEMA = """
-- ---
-- Table 'elem'
--
-- ---

DROP TABLE IF EXISTS `elem`;
|||
CREATE TABLE `elem` (
  `id` INTEGER PRIMARY KEY,
  `type` VARCHAR DEFAULT NULL,
  `data` TEXT DEFAULT NULL,
  `parent_id` INTEGER DEFAULT NULL,
  `sort_order` INTEGER DEFAULT NULL,
  FOREIGN KEY(`parent_id`) REFERENCES elem(`id`)
);

|||

-- ---
-- Table 'attr'
--
-- ---

DROP TABLE IF EXISTS `attr`;
|||
CREATE TABLE `attr` (
  `id` INTEGER PRIMARY KEY,
  `k` VARCHAR DEFAULT NULL,
  `v` TEXT DEFAULT NULL,
  `elem_id` INTEGER DEFAULT NULL,
  FOREIGN KEY(`elem_id`) REFERENCES elem(`id`)
);
"""


class DbParserException(HTMLParseError):
    pass


def regexp(expr, item):
    reg = re.compile(expr)
    return reg.search(item) is not None


def render_attrs(attrs, prefix=''):
    ret = []
    for k, v in attrs:
        ret.append('%s="%s"' % (k, v))
    return prefix + ' '.join(ret)


def make_db_connection():
    out_conn = sqlite.connect(DATABASE, detect_types=sqlite.PARSE_DECLTYPES, check_same_thread=False)
    out_conn.text_factory = str
    out_conn.create_function("REGEXP", 2, regexp)
    for sql in SCHEMA.split('|||'):
        out_conn.execute(sql)
    out_conn.commit()
    return out_conn


class DbParser(HTMLParser):
    def __init__(self, html=None):
        self._conn = make_db_connection()
        self._sort_order = 0
        HTMLParser.__init__(self)
        self._tag_tree = []
        if html is not None:
            self.feed(html)

    def loads(self, data):
        self.feed(data)

    def load(self, filename):
        self.loads(open(filename, 'rb').read())

    def _shift_order(self):
        self._conn.execute('UPDATE elem SET sort_order = sort_order*10')
        self._conn.commit()

    def _insert_elem(self, elem_type, data, parent_id=0):
        self._sort_order += 1
        cursor = self._conn.cursor()
        cursor.execute('INSERT INTO elem (`type`,`data`,`parent_id`,`sort_order`) VALUES (?,?,?,?);',
                       (elem_type, data, parent_id, self._sort_order))
        self._conn.commit()
        cursor.execute('SELECT last_insert_rowid()')
        return cursor.fetchone()[0]

    def set_elem_value(self, _id, value):
        return self._update_elem(_id, data=value)

    def _update_elem(self, _id, **vals_to_update):
        cursor = self._conn.cursor()
        sql = []
        vals = []
        for k, v in vals_to_update.items():
            sql.append(k + '=?')
            vals.append(v)
        vals.append(_id)
        sql = ','.join(sql)
        cursor.execute('UPDATE elem SET ' + sql + '  WHERE id=?', vals)
        self._conn.commit()
        cursor.execute('SELECT last_insert_rowid()')
        return cursor.fetchone()[0]

    def _insert_attr(self, k, v, elem_id=0):
        cursor = self._conn.cursor()
        cursor.execute('INSERT INTO attr (`k`,`v`,`elem_id`) VALUES (?,?,?);', (k, v, elem_id))
        self._conn.commit()
        cursor.execute('SELECT last_insert_rowid()')
        return cursor.fetchone()[0]

    def handle_decl(self, decl):
        self._insert_elem(DECL, decl, self._tag_tree[-1]['id'] if self._tag_tree else 0)

    def handle_pi(self, data):
        self._insert_elem(PI, data, self._tag_tree[-1]['id'] if self._tag_tree else 0)

    def handle_comment(self, data):
        self._insert_elem(COMMENT, data, self._tag_tree[-1]['id'] if self._tag_tree else 0)

    def handle_data(self, data):
        self._insert_elem(DATA, data, self._tag_tree[-1]['id'] if self._tag_tree else 0)

    def handle_starttag(self, tag, attrs):
        last_id = self._insert_elem(TAG, tag, self._tag_tree[-1]['id'] if self._tag_tree else 0)
        self._tag_tree.append({'tag': tag, 'id': last_id})
        for k, v in attrs:
            self._insert_attr(k, v, last_id)

    def handle_endtag(self, tag):
        if tag == self._tag_tree[-1]['tag']:
            self._tag_tree.pop()
        else:
            raise DbParserException('x')

    def _select_elem(self, **where):
        if not where:
            where = {'parent_id': 0}
        cursor = self._conn.cursor()
        sql = []
        vals = []
        for k, v in where.items():
            sql.append(k + '=?')
            vals.append(v)
        sql = ' AND '.join(sql)
        if not where:
            sql = 'parent_id=?'
            vals = (0,)
        cursor.execute('SELECT * FROM elem WHERE ' + sql + ' ORDER BY sort_order;', vals)
        ret = cursor.fetchall()
        return ret

    def _select_attr(self, i=0):
        cursor = self._conn.cursor()
        cursor.execute('SELECT k,v FROM attr WHERE elem_id=?;', (i,))
        ret = cursor.fetchall()
        return ret

    def _update_attr(self, key, value, elem_id=0):
        self._conn.execute('UPDATE attr SET v=? WHERE elem_id=? AND k=?;', (value, elem_id, key))
        self._conn.commit()

    def set_attr(self, recs, **params):
        for rec in recs:
            attr = self._select_attr(rec[0])
            for k, v in params.items():
                if k in (x[0] for x in attr):
                    self._update_attr(k, v, rec[0])
                else:
                    self._insert_attr(k, v, rec[0])

    def get_attr(self, recs, wrapper=list):
        ret = []
        for rec in recs:
            ret.append(wrapper(self._select_attr(rec[0])))
        return ret

    def __str__(self):
        ret = self._select_elem()
        return self.to_string(ret)

    def __len__(self):
        cursor = self._conn.cursor()
        cursor.execute('SELECT count(*) FROM elem WHERE parent_id=0;')
        return cursor.fetchone()[0]

    def yield_childs(self, recs, t=None):
        for rec in recs:
            for child in (self._select_elem(parent_id=rec[0], type=t) if t else self._select_elem(parent_id=rec[0])):
                yield child
                for x in self.yield_childs((child,), t):
                    yield x

    def childs(self, recs, _type=None):
        return [x for x in self.yield_childs(recs) if not _type or x[1] == _type]

    def parent(self, recs):
        ret = []
        for rec in recs:
            for x in self._select_elem(id=rec[3]):
                ret.append(x)
        return ret

    def to_string(self, recs, before=None, after=None, html=None):
        ret = []
        for l in recs:
            if before:
                if l in before:
                    ret.append(html)
            if l[1] == DECL:
                ret.append('<!' + l[2] + '>')
            elif l[1] == PI:
                ret.append('<?' + l[2] + '>')
            elif l[1] == COMMENT:
                ret.append('<!--' + l[2] + '-->')
            elif l[1] == DATA:
                ret.append(l[2])
            elif l[1] == TAG:
                content = self.to_string(self._select_elem(parent_id=l[0]), after=after, html=html)
                attributes = render_attrs(self._select_attr(l[0]), ' ')
                tagname = l[2]
                if content:
                    ret.append('<%s%s>%s</%s>' % (tagname, attributes, content, tagname))
                else:
                    ret.append('<%s%s/>' % (tagname, attributes))
            if after:
                if l in after:
                    ret.append(html)
        return ''.join(ret)

    def tag(self, tag_name):
        cursor = self._conn.cursor()
        cursor.execute('SELECT * FROM elem WHERE `type`=? AND `data`=?;', (TAG, tag_name))
        ret = cursor.fetchall()
        return ret

    def id(self, _id):
        return self.attr(id=_id)

    def insert_html_after(self, recs, html):
        """
        Return a new parser instance
        """
        new_html = self.to_string(self._select_elem(), after=recs, html=html)
        ret = DbParser()
        ret.loads(new_html)
        return ret

    def attr(self, function='LIKE', **params):
        """
        example query

        select * from elem where id in
            (select a.elem_id from attr a
                join attr a2 on a.elem_id = a2.elem_id
                where a.k like 'x' and a.v like '85%'
                AND a2.k like 'y' and a2.v like '728%'
            )

        """
        values = []
        join = []
        where = []
        i = 0
        for k, v in params.items():
            i += 1
            values.append(k)
            values.append(v)
            where.append("a%i.k %s ? AND a%i.v %s ?" % (i, function, i, function))
            if i > 1:
                join.append('JOIN attr a%i ON a1.elem_id = a%i.elem_id' % (i, i))
        cursor = self._conn.cursor()
        cursor.execute("select * from elem where id in (SELECT a1.elem_id FROM attr a1 %s WHERE %s);" % (
            ' '.join(join), ' AND '.join(where)), values)
        ret = cursor.fetchall()
        return ret


#  _____ ___ ___ _____
# |_   _| __/ __|_   _|
#   | | | _|\__ \ | |
#   |_| |___|___/ |_|

def test1(parser):
    assert len(parser) == 6


def test2(parser):
    assert str(parser).strip('\n\r ') == open('test/test_regen.svg', 'r').read().strip('\n\r ')


def test3(parser):
    x = parser.id('template')
    assert len(x) == 1
    x = parser.tag('g')
    assert len(x) == 2
    x = parser.id('tspan%')
    assert len(x) == 3
    x = parser.attr(id='tspan%')
    assert len(x) == 3


def test4(parser):
    x = parser.attr(x='71%')
    assert len(x) == 2
    x = parser.attr(x='85%', y='728%')
    assert len(x) == 2
    assert x[0][2] == 'text'
    assert x[1][2] == 'tspan'
    assert x[0][1] == TAG
    assert x[1][1] == TAG


def test5(parser):
    x = parser.attr(x=r'\b191\b', function='REGEXP')
    assert len(x) == 3
    x = parser.attr(x=r'\b19\b', function='REGEXP')
    assert len(x) == 0
    x = parser.attr(id=r'tspan3902', function="=")
    assert parser.to_string(x) == '<tspan y="933.57239" x="191.48788" id="tspan3902" sodipodi:role="line">4</tspan>'


def test6(parser):
    x = parser.id('spaziatura')
    attrs = parser.get_attr(x, wrapper=dict)[0]
    assert attrs['height'] == '295.33151'
    assert attrs['width'] == '210.96687'


def test7(parser):
    template = parser.id('template')
    childs = parser.childs(template)
    assert len(childs) == 18


def test8(parser):
    poker_values = (1, 2, 3, 5, 8, 13, 20, 40, 100)
    ore_values = (1, 2, 3, 4, 6, 8, 'x2', 'x3', 'x5')

    x = parser.id('spaziatura')
    attrs = parser.get_attr(x, wrapper=dict)[0]
    height = float(attrs['height'])
    width = float(attrs['width'])

    template = parser.id('template')
    html = parser.to_string(template)

    parser2 = parser
    for i in xrange(8):
        this_id = 'template%i' % i
        parser2 = parser2.insert_html_after(template, html)
        template = parser2.id('template')[-1:]
        parser2.set_attr(template, id=this_id)

        for rec in parser2.yield_childs(parser2.id(this_id), TAG):
            attrs = parser2.get_attr((rec,), wrapper=dict)[0]
            try:
                new_x = float(attrs['x']) + width * ((i + 1) % 3)
                new_y = float(attrs['y']) - height * ((i + 1) / 3)
                parser2.set_attr((rec,), x=new_x, y=new_y)
            except KeyError:
                pass
            try:
                transform = attrs['transform']
                for pre, _x, mid, _y, post in re.findall(r'(.*?)([0-9.]+)(\D+)([0-9.]+)(\D+)', transform, re.I):
                    parser2.set_attr((rec,), transform="%s%s%s%s%s" % (
                        pre, float(_x) + width * ((i + 1) % 3), mid, float(_y) - height * ((i + 1) / 3), post))
            except KeyError:
                pass

    for j, rec in enumerate(parser2.childs(parser2.id('poker'), DATA)):
        parser2.set_elem_value(rec[0], poker_values[j])

    for j, rec in enumerate(parser2.childs(parser2.id('ore'), DATA)):
        parser2.set_elem_value(rec[0], ore_values[j])
        if len(str(ore_values[j])) > 1:
            delta = 8 * (len(str(ore_values[j])) - 1)  # the spartan way
            for parent in parser2.parent((rec,)):
                attrs = parser2.get_attr((parent,), wrapper=dict)[0]
                try:
                    new_x = float(attrs['x']) - delta
                    parser2.set_attr((parent,), x=new_x)
                except KeyError:
                    pass

    open('out3.svg', 'wb').write(str(parser2))


def test9(parser):
    template = parser.id('template')
    childs = parser.childs(template, _type=TAG)
    assert len(childs) == 9
    assert all((x[1] == TAG for x in childs))


def main(argv):
    import inspect

    my_name = inspect.stack()[0][3]
    for f in argv:
        parser = DbParser()
        parser.load('test/test.svg')
        globals()[f](parser)
    if not argv:
        fs = [globals()[x] for x in globals() if
              inspect.isfunction(globals()[x]) and x.startswith('test') and x != my_name]
        for f in fs:
            parser = DbParser()
            parser.load('test/test.svg')
            print f.__name__
            f(parser)


if __name__ == "__main__":
    import sys

    main(sys.argv[1:])
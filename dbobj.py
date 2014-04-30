#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# (c) Roberto Gambuzzi

import sqlite3 as sqlite
import __builtin__
import re

DATABASE = ':memory:'


def regexp(expr, item):
    reg = re.compile(expr)
    return reg.search(item) is not None


def record_factory(cursor, row):
    d = Record()
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def make_db_connection():
    out_conn = sqlite.connect(DATABASE, detect_types=sqlite.PARSE_DECLTYPES, check_same_thread=False)
    out_conn.text_factory = str
    out_conn.row_factory = record_factory
    out_conn.create_function("REGEXP", 2, regexp)
    return out_conn


def _generate_sql_where_condition(where):
    sql = []
    vals = []
    for k, v in where.items():
        sql.append('`' + k + '`=?')
        vals.append(v)
    sql = ' AND '.join(sql)
    return sql, vals


class Record(dict):
    def __init__(self, iterable=None, **kwargs):
        self._object = None
        self._object_pk = None
        if iterable:
            super(Record, self).__init__(iterable, **kwargs)
        else:
            super(Record, self).__init__(**kwargs)

    def set_object(self, obj, primary_key='id'):
        self._object = obj
        self._object_pk = primary_key

    def update(self, other=None, **kwargs):
        if self._object is not None:
            params = dict(self.items())
            params.update(kwargs)
            self._object.append(**params)
        if other:
            super(Record, self).update(other, **kwargs)
        else:
            super(Record, self).update(**kwargs)

    def __setitem__(self, key, value):
        if self._object is not None:
            params = dict(self.items())
            params[key] = value
            params[self._object_pk] = self[self._object_pk]
            self._object.append(**params)
        super(Record, self).__setitem__(key, value)

    def __delitem__(self, key):
        if key not in self:
            raise KeyError
        self[key] = None
        if self._object is not None:
            self._object.append(**self)
            #super(Record, self).__delitem__(key)


class Abstract(object):
    def __init__(self, db_connection):
        self._conn = db_connection
        for sql in self._schema:
            self._conn.execute(sql)

    def append(self, **params):
        fields = []
        vals = []
        for k, v in params.items():
            fields.append('`%s`' % k)
            vals.append(v)
        interrog = ','.join(['?'] * len(fields))
        fields = ','.join(fields)

        cursor = self._conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO `' + self._tablename + '` (' + fields + ') VALUES (' + interrog + ');',
                       vals)
        self._conn.commit()
        cursor.execute('SELECT last_insert_rowid() as last_insert_rowid')
        return cursor.fetchone()['last_insert_rowid']

    def delete_record(self, **where):
        cursor = self._conn.cursor()
        sql, vals = _generate_sql_where_condition(where)
        cursor.execute('DELETE FROM `' + self._tablename + '` WHERE ' + sql, vals)
        cursor.execute('SELECT changes() as changes')
        return cursor.fetchone()['changes']

    def select_record(self, **where):
        if not where:
            where = {'parent_id': 0}
        cursor = self._conn.cursor()
        sql, vals = _generate_sql_where_condition(where)
        order_by = ''
        if hasattr(self, '_order') and self._order:
            order_by = ' ORDER BY ' + self._order
        cursor.execute('SELECT * FROM `' + self._tablename + '` WHERE ' + sql + order_by + ';', vals)
        ret = cursor.fetchall()
        return ret

    def __setitem__(self, key, value):
        value['id'] = key
        self.append(**value)

    def __getitem__(self, item):
        for ret in self.select_record(id=item):
            ret.set_object(self)
            return ret
        raise KeyError

    def __delitem__(self, key):
        if self.delete_record(id=key):
            return
        raise KeyError


class AttrItem(dict):
    def __init__(self, elem_id, eav_model, **kwargs):
        self._eav_model = eav_model
        self._elem_id = elem_id
        if kwargs:
            self._eav_model.delete_record(elem_id=elem_id)
            for k, v in kwargs.items():
                self._eav_model.append(elem_id=elem_id, k=k, v=v, type=type(v).__name__)
        else:
            for x in self._eav_model.select_record(elem_id=elem_id):
                if x['type']:
                    self[x['k']] = getattr(__builtin__, x['type'])(x['v'])
                else:
                    self[x['k']] = x['v']
        super(AttrItem, self).__init__(**kwargs)

    def __setitem__(self, key, value):
        self._eav_model.append(elem_id=self._elem_id, k=key, v=value, type=type(value).__name__)
        return super(AttrItem, self).__setitem__(key, value)

    def __delitem__(self, key):
        self._eav_model.delete_record(elem_id=self._elem_id, k=key)
        super(AttrItem, self).__delitem__(key)


class Attr(dict):
    def __init__(self, eav_model, **kwargs):
        self._eav_model = eav_model
        super(Attr, self).__init__(**kwargs)

    def __setitem__(self, key, value):
        value = AttrItem(key, self._eav_model, **value)
        super(Attr, self).__setitem__(key, value)

    def __getitem__(self, item):
        ret = AttrItem(item, self._eav_model)
        return ret

    def __delitem__(self, key):
        if not self._eav_model.delete_record(elem_id=key):
            raise KeyError


class EavAttr(Abstract):
    _tablename = 'attr'
    _schema = \
        (
            "DROP TABLE IF EXISTS attr",
            """CREATE TABLE `attr` (
               `id` INTEGER PRIMARY KEY,
               `k` VARCHAR DEFAULT NULL,
               `v` TEXT DEFAULT NULL,
               `type` VARCHAR DEFAULT NULL,
               `elem_id` INTEGER DEFAULT NULL,
               FOREIGN KEY(`elem_id`) REFERENCES elem(`id`)
            );"""
        )


class Elem(Abstract):
    _tablename = 'elem'
    _schema = \
        (
            "DROP TABLE IF EXISTS elem",
            """CREATE TABLE `elem` (
               `id` INTEGER PRIMARY KEY,
               `type` VARCHAR DEFAULT NULL,
               `data` TEXT DEFAULT NULL,
               `parent_id` INTEGER DEFAULT NULL,
               `sort_order` INTEGER DEFAULT NULL,
               FOREIGN KEY(`parent_id`) REFERENCES elem(`id`)
            );"""
        )
    _order = 'sort_order'


#  _____ ___ ___ _____
# |_   _| __/ __|_   _|
#   | | | _|\__ \ | |
#   |_| |___|___/ |_|

def test1():
    e = Elem(make_db_connection())
    values = dict(type='__tag__', data='h1', parent_id=0, sort_order=1)
    idx = e.append(**values)
    assert idx == 1
    assert all(((x in e[idx].items()) for x in values.items()))
    del e[idx]
    try:
        e[idx]
        assert False
    except KeyError:
        assert True
    except:
        assert False


def test2():
    e = Elem(make_db_connection())
    idx = e.append(type='__tag__', data='h1', parent_id=0, sort_order=1)
    assert type(e[idx]) == Record
    assert e[idx]['data'] == 'h1'
    assert e[idx]['type'] == '__tag__'
    e[idx] = dict(type='__tag__', data='h3', parent_id=0, sort_order=1)
    assert e[idx]['data'] == 'h3'
    assert e[idx]['type'] == '__tag__'
    e[idx].update(data='h2')
    assert e[idx]['data'] == 'h2'
    assert e[idx]['type'] == '__tag__'
    e[idx]['data'] = 'h4'
    assert e[idx]['data'] == 'h4'
    assert e[idx]['type'] == '__tag__'
    del e[idx]['data']
    assert e[idx]['data'] is None
    assert e[idx]['type'] == '__tag__'
    assert e[idx] == {'data': None, 'sort_order': 1, 'type': '__tag__', 'id': 1, 'parent_id': 0}


def test3():
    e = EavAttr(make_db_connection())
    idx = e.append(k='name', v='no care[string]', elem_id=1)
    assert type(e[idx]) == Record
    assert e[idx]['k'] == 'name'
    assert e[idx]['v'] == 'no care[string]'
    assert e[idx]['elem_id'] == 1
    e[idx] = dict(k='name2', v='no2care[string]', elem_id=1)
    assert e[idx]['k'] == 'name2'
    assert e[idx]['v'] == 'no2care[string]'
    assert e[idx]['elem_id'] == 1
    e[idx].update(k='id')
    assert e[idx]['k'] == 'id'
    assert e[idx]['v'] == 'no2care[string]'
    assert e[idx]['elem_id'] == 1
    e[idx]['k'] = 'hhh'
    assert e[idx]['k'] == 'hhh'
    assert e[idx]['v'] == 'no2care[string]'
    assert e[idx]['elem_id'] == 1
    del e[idx]['k']
    assert e[idx]['k'] is None


def test4():
    e = Attr(EavAttr(make_db_connection()))
    e[12] = {'k12': 12, 'k2': 2, 'banana': 'good one', 'class': 'btn btn-primary btn-xs'}
    assert e[12]['k12'] == 12
    assert e[12]['k2'] == 2
    assert e[12]['class'] == 'btn btn-primary btn-xs'

    e[12]['k12'] = 'ciao'
    assert e[12]['k12'] == 'ciao'
    assert e[12]['k2'] == 2

    e[12]['banana'] = 'banana'
    assert e[12]['banana'] == 'banana'

    assert e[12] == {'k12': 'ciao', 'class': 'btn btn-primary btn-xs', 'banana': 'banana', 'k2': 2}

    del e[12]['k12']
    assert e[12] == {'class': 'btn btn-primary btn-xs', 'banana': 'banana', 'k2': 2}
    try:
        e[12]['k12']
        assert False
    except KeyError:
        assert True

    del e[12]
    assert e[12] == {}

def main(argv):
    import inspect

    my_name = inspect.stack()[0][3]
    for f in argv:
        globals()[f]()
    if not argv:
        fs = [globals()[x] for x in globals() if
              inspect.isfunction(globals()[x]) and x.startswith('test') and x != my_name]
        for f in fs:
            print f.__name__
            f()


if __name__ == "__main__":
    import sys

    main(sys.argv[1:])

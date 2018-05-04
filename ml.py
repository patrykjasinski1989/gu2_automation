# -*- coding: utf-8 -*-
import cx_Oracle
import config


def ml_connection():
    return cx_Oracle.connect(user=config.ml['user'], password=config.ml['password'], dsn=config.ml['server'])

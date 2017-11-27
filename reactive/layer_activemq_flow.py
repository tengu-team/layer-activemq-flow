#!/usr/bin/env python3
# Copyright (C) 2017  Qrama
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# pylint: disable=c0111,c0103,c0301,c0412
import os
import subprocess as sp
import json
from charms.reactive import when, when_not, set_state
from charmhelpers.core.templating import render
from charmhelpers.core import unitdata
from charmhelpers.core.hookenv import status_set, service_name

unitd = unitdata.kv()
FLOW_PATH = '/opt/dataflow'

@when('dataflow.available')
@when_not('activemq_dataflow.installed')
def install_activemq_dataflow(dataflow):
    set_state('activemq_dataflow.connected')
    unitd.set('nodes', ['node-red-node-mongodb', 'node-red-node-stomp'])
    status_set('blocked', 'Waiting for a relation with ActiveMQ and MongoDB')

################################################################################
# First Relation with Db then ActiveMQ
################################################################################
@when('db.available', 'activemq_dataflow.connected')
@when_not('activemq_dataflow.dbconnected')
def connect_to_db(db):
    unitd.set('mongo_uri', db.db_data()['uri'].split(':')[0])
    unitd.set('db', db.db_data()['db'])
    set_state('activemq_dataflow.dbconnected')

@when('topic.available', 'activemq_dataflow.connected')
@when_not('activemq_dataflow.topicconnected')
def connect_topic(topic):
    unitd.set('topic', topic.connection()['topic'])
    unitd.set('activemq', topic.connection()['host'])
    set_state('activemq_dataflow.topicconnected')

################################################################################
# Final deployment
################################################################################
@when('activemq_dataflow.topicconnected', 'activemq_dataflow.dbconnected')
@when_not('activemq_dataflow.installed')
def set_installed():
    if not os.path.exists(FLOW_PATH):
        os.makedirs(FLOW_PATH)
    context = {'flow': service_name(), 'topic': unitd.get('topic'), 'activemq': unitd.get('activemq'), 'db': unitd.get('db'), 'mongodb': unitd.get('mongo_uri')}
    render('flow.json', '{}/flow.json'.format(FLOW_PATH), context)
    set_state('activemq_dataflow.installed')

@when('activemq_dataflow.installed', 'dataflow.available')
@when_not('activemq_dataflow.deployed')
def send_flow(dataflow):
    with open('{}/flow.json'.format(FLOW_PATH)) as f:
        data = f.read()
        dataflow.configure(data, unitd.get('nodes'))
    status_set('active', 'ActiveMQ Dataflow deployed!')
    set_state('activemq_dataflow.deployed')

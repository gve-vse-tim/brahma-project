#!/usr/bin/python

from cobra.internal.codec.jsoncodec import (parseJSONError, fromJSONStr, toJSONStr)

from cobra.mit.access import MoDirectory
from cobra.mit.session import LoginSession
from cobra.mit.request import ClassQuery

import os
import re
import sys
import six
import json
import urllib3
import socket
import requests
import argparse
import shortuuid
import getpass

from configparser import ConfigParser
from .sync import apply_desired_state

BRAHMA_FQDN = os.getenv('BRAHMA_URL', 'brahma.cisco.com')
BRAHMA_PORT = os.getenv('BRAHMA_PORT', None)

BRAHMA_URL = 'http://' + BRAHMA_FQDN

if(BRAHMA_PORT != None):
  BRAHMA_URL += ':' + BRAHMA_PORT

SERVER_URL = BRAHMA_URL + '/api/fabric'

IP_ADDR = "^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]).){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$"
HOST_FQDN = "^(([a-zA-Z]|[a-zA-Z][a-zA-Z0-9-]*[a-zA-Z0-9]).)*([A-Za-z]|[A-Za-z][A-Za-z0-9-]*[A-Za-z0-9])$"

# Original Regex Strings
# IP_ADDR = "^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$"
# HOST_FQDN = "^(([a-zA-Z]|[a-zA-Z][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z]|[A-Za-z][A-Za-z0-9\-]*[A-Za-z0-9])$"

class FabricConnection():
  # Fabric Connection
    
  def __init__(self, sourcePort, destSwitch, destPort):
    self.sourcePort = sourcePort
    self.destSwitch = destSwitch
    self.destPort = destPort

class FabricNode():
  # Fabric Node
    
  def __init__(self, switchName, switchRn, switchRole, switchSerial, switchModel, switchID):
    self.name = switchName
    self.rn = switchRn
    self.role = switchRole
    self.serial = switchSerial
    self.model = switchModel
    self.id = switchID
    self.connections = []
      
  def add_connection(self, sourcePort, destPort, destSwitch):
    # Add Connection
    new_connection = FabricConnection(sourcePort, destPort, destSwitch)
    self.connections.append(new_connection)

class FabricTopology():
  # Fabric Topology

  def __init__(self):
    self.token = shortuuid.uuid()
    self.nodes = []
    self.state = {}

  def add_node(self, switchName, switchRn, switchRole, switchSerial, switchModel, switchID):
    new_node = FabricNode(switchName, switchRn, switchRole, switchSerial, switchModel, switchID)
    self.nodes.append(new_node)

  def get_nodes(self):
    node_list = []

    for node in self.nodes:
      node_list.append(node)

    return node_list

  def toJSON(self):
    return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

def main():
  urllib3.disable_warnings()

  args = parseArgs()

  if(args.new):
    newFabric()

  if(args.apply):
    applyConfig()

def parseArgs():
  arg_parser = argparse.ArgumentParser(prog='brahma', description='Brahma CLI Utility')
  arg_parser.version = '1.0'
  arg_parser.add_argument('-n', dest='new', action='store_true', help='New Fabric', required=False)
  arg_parser.add_argument('-a', dest='apply', action='store_true', help='Apply Config', required=False)
  arg_parser.add_argument('-v', action='version', help='Show Version')
  args = arg_parser.parse_args()

  return args

def aciLogin():
  print('')

  apic_addr = six.moves.input("APIC IP Address/FQDN: ")

  is_ip = re.match(IP_ADDR, apic_addr)
  is_host = re.match(HOST_FQDN, apic_addr)

  if (is_ip):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.5)

    try:
      s.connect((apic_addr,443)) 
    except:
      print("APIC IP Address unreachable!")
      sys.exit()

  if (is_host):
    try:
      socket.gethostbyname(apic_addr)
    except socket.gaierror:
      print("APIC FQDN unreachable!")
      sys.exit()

  if not is_ip and not is_host:
    print("Not a valid IP Address or FQDN!")
    sys.exit()

  apic_user = six.moves.input("APIC Username: ")
  apic_pass = getpass.getpass(prompt='APIC Password: ', stream=None) 

  apic_url = "https://" + apic_addr

  session = LoginSession(apic_url, apic_user, apic_pass)
  moDir = MoDirectory(session)

  try:
    moDir.login()
  except requests.exceptions.RequestException:
    print("Cannot connect to APIC!")
    sys.exit()

  return moDir

def applyConfig():
  moDir = aciLogin()

  fabric_token = six.moves.input("Fabric Token: ")

  apply_url = SERVER_URL + '/' + fabric_token

  print(apply_url)

  req = requests.get(url = apply_url)
  req_json = json.loads(req.content)

  state = req_json['state']

  # req_json = req.json()
  # parsed_json = (json.load(req_json['state']))
  # print(req)
  apply_desired_state(moDir, state)

def newFabric():
  moDir = aciLogin()

  cq = ClassQuery('fabricNode')

  nodes = moDir.query(cq)

  fNodes = FabricTopology()

  for node in nodes:
    if(node.role == 'spine' or node.role=='leaf' or node.role=='controller'):
      node_name = str(node.name)
      node_real = str(node.rn)
      node_role = str(node.role)
      node_serial = str(node.serial)
      node_model = str(node.model)
      node_id = str(node.id)
      fNodes.add_node(node_name, node_real, node_role, node_serial, node_model, node_id)

  # print('') 

  for fNode in fNodes.get_nodes():
    # print('{}({}) -> Role: {}'.format(fNode.name, fNode.serial, fNode.role))
    # print('-----')
    nodeDn = 'topology/pod-1/' + fNode.rn + '/sys'
    intfs = moDir.lookupByClass("l1PhysIf", parentDn=nodeDn) 
    for intf in intfs:
      if(intf.usage == 'fabric') and (intf.switchingSt == 'enabled'):
        int_id = str(intf.id)
        lldpDn = nodeDn + '/lldp/inst/if-[' + int_id + ']'
        lldpns = moDir.lookupByClass("lldpAdjEp", parentDn=lldpDn)

        for lldpn in lldpns:
          dest_name = lldpn.sysName
          port_desc = lldpn.portDesc
          dest_length = len(port_desc) - 1
          left_bracket = port_desc.find('[') - dest_length
          dest_port = port_desc[left_bracket:-1]
          fNode.add_connection(int_id, dest_name, dest_port)
          # print('{} -> {}({})'.format(int_id, dest_name, dest_port))
    # print('')

  # print('--------------------------')  
  # print('')

  node_json = fNodes.toJSON()

  # print(node_json)

  json_data = json.loads(node_json)

  req = requests.post(url = SERVER_URL, json = json_data)
  # print(req.status_code)

  resp_json = json.loads(req.text)
  # print(json.dumps(resp_json, indent=4, sort_keys=False))

  print('')
  print('Fabric Uploaded!')
  print('')
  print('Token: {}'.format(resp_json['token']))
  print('')
  print('Please navigate to {} and use the above token.'.format(BRAHMA_URL))
  print('')

if __name__ == '__main__':
  main()

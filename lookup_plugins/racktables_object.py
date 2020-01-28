from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = """
    lookup: racktables_object
    author: Chandler Willoughby
    version_added: "0.0"
    short_description: Lookup object network information by name in Racktables
    requirements:
      - PyMySql (python3 library)
    description:
      - Performs an object lookup in Racktables and returns IP/Network information
    options:
      _terms:
        description: object name as it exists in Racktables
        required: True
        type: string
"""

EXAMPLES = """
- name: lookup object network information
  debug: msg="{{lookup('racktables_object', ['testhost.lab1'])}}"
"""

RETURN = """
  _list:
    description:
      - List of addresses assigned to the object
    type: list
"""

HAVE_PYMYSQL = False
try:
    import pymysql.cursors
    import ipaddress
    import os
    HAVE_PYMYSQL = True
except ImportError:
    pass

from ansible.errors import AnsibleError
from ansible.module_utils._text import to_native
from ansible.plugins.lookup import LookupBase

class LookupModule(LookupBase):

    def run(self, terms, variables=None, **kwargs):
        if HAVE_PYMYSQL is False:
            raise AnsibleError("Can't LOOKUP(racktables_object): module PyMySQL is not installed")
        self.set_options(var_options=variables, direct=kwargs)
        rt_name=terms[0]
        rt_params=terms[1]
        result = []
        connection = pymysql.connect(host=rt_params['host'],user=rt_params['user'],password=rt_params['pass'],db=rt_params['database'])
        rt_object_sql="SELECT RTO.name, INET_NTOA(RTA.ip), RTA.name FROM Object RTO, IPv4Allocation RTA WHERE RTA.object_id=RTO.id AND RTO.name='{}'".format(rt_name)
        with connection.cursor() as cursor:
            cursor.execute(rt_object_sql)
            rtObjectAddresses = cursor.fetchall()
            for address in rtObjectAddresses:
              addressObject={"address":"","netmask":"","gateway":"","netname":"","ifname":"","vlan":""}
              addressObject["address"]=address[1]
              addressObject["ifname"]=address[2]
              cursor.execute("SELECT id,INET_NTOA(ip),mask,name from IPv4Network where (INET_ATON('{}') ^ `ip` & ~(POW(2,32-`mask`)-1))=0 ORDER BY mask DESC LIMIT 1".format(addressObject["address"]))
              network=cursor.fetchone()
              subnet=ipaddress.IPv4Network('{}/{}'.format(network[1],network[2]))
              addressObject["netmask"]=str(subnet.netmask)
              addressObject["gateway"]=str(subnet[1])
              addressObject["netname"]=network[3]
              cursor.execute("SELECT vlan_id FROM VLANIPv4 WHERE ipv4net_id='{}'".format(network[0]))
              networkVlan=cursor.fetchone()
              if not networkVlan:
                raise AnsibleError("The network {} does not have a VLAN assigned. Please correct this in Racktables".format(network[3]))
              else:
                addressObject["vlan"]=networkVlan[0]
              result.append(addressObject)
        return result
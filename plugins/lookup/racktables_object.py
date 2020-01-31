from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = """
    lookup: racktables_object
    author: Chandler Willoughby
    version_added: "0.0"
    short_description: Lookup an object in Racktables
    requirements:
      - PyMySql (python3 library)
    description:
      - Returns a single object from Racktables
    options:
        object:
            description: The name of the object to lookup
            required: true
            type: string
        rt_host:
            description: Hostname of the database server backing Racktables
            required: true
            type: string
        rt_port:
            description: Port for the database connection, defaults to 3306
            required: false
            type: integer
            default: 3306
        rt_username:
            description: Username that has administrative access to the racktables database
            required: true
            type: string
        rt_password:
            description: Password for the administrative user
            required: true
            type: string
        rt_database:
            description: Name of the database which backs Racktables
            required: true
            type: string
"""

EXAMPLES = """
- name: lookup object network information
  debug: msg="{{ lookup('racktables_object', rt_host='rackhost.local', rt_username='rackuser', rt_password='sup3r$3cur3', rt_database='rackdb', name='coolhost.local' }}"
"""

RETURN = """
  _object:
    description:
      - The object from racktables
    type: dict
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
        result = []
        try:
            connection = pymysql.connect(host=self.get_option('rt_host'),port=self.get_option('rt_port'),user=self.get_option('rt_username'),password=self.get_option('rt_password'),db=self.get_option('rt_database'))
        except Exception as e:
            raise AnsibleError("Encountered an issue while connecting to the database, this was the original exception: %s" % to_native(e))
        rt_object_sql="SELECT RTO.id, RTO.name, RTO.label, RTD.dict_value, RTO.asset_no, RTO.has_problems, RTO.comment FROM Object RTO, Dictionary RTD WHERE RTD.dict_key=RTO.objtype_id AND RTO.name=%s"
        rt_object_addresses_sql="SELECT INET_NTOA(ip), name, `type` FROM IPv4Allocation WHERE object_id=%s;"
        with connection.cursor() as cursor:
            cursor.execute(rt_object_sql, self.get_option('object'))
            rtObject = cursor.fetchone()
            if not rtObject:
                return result
            cursor.execute(rt_object_addresses_sql,rtObject[0])
            rtObjectAddresses = cursor.fetchall()
            resultObject = {}
            resultObject['name'] = rtObject[1]
            resultObject['label'] = rtObject[2]
            resultObject['type'] = rtObject[3]
            resultObject['asset_no'] = rtObject[4]
            resultObject['comment'] = rtObject[6]
            resultObject['addresses'] = []
            for address in rtObjectAddresses:
              addressObject={"address":"","netmask":"","gateway":"","netname":"","ifname":"","vlan":""}
              addressObject["address"]=address[0]
              addressObject["ifname"]=address[1]
              cursor.execute("SELECT id,INET_NTOA(ip),mask,name from IPv4Network where (INET_ATON(%s) ^ `ip` & ~(POW(2,32-`mask`)-1))=0 ORDER BY mask DESC LIMIT 1",addressObject["address"])
              network=cursor.fetchone()
              subnet=ipaddress.IPv4Network('{}/{}'.format(network[1],network[2]))
              addressObject["netmask"]=str(subnet.netmask)
              addressObject["gateway"]=str(subnet[1])
              addressObject["netname"]=network[3]
              cursor.execute("SELECT vlan_id FROM VLANIPv4 WHERE ipv4net_id=%s",network[0])
              networkVlan=cursor.fetchone()
              if not networkVlan:
                raise AnsibleError("The network {} does not have a VLAN assigned. Please correct this in Racktables".format(network[3]))
              else:
                addressObject["vlan"]=networkVlan[0]
              resultObject['addresses'].append(addressObject)
            result.append(resultObject)
        return result
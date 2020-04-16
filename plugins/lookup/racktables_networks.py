from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = """
    lookup: racktables_network
    author: Chandler Willoughby
    version_added: "0.0"
    short_description: Lookup networks in Racktables with the provided tags
    requirements:
      - PyMySql (python3 library)
    description:
      - Returns a list of networks matching the provided tags
    options:
        tags:
            description: A list containg the tags that the networks should have
            required: true
            type: list
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
  debug: msg="{{ lookup('racktables_networks', rt_host='rackhost.local', rt_username='rackuser', rt_password='sup3r$3cur3', rt_database='rackdb', tags=('Production')) }}"
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
            raise AnsibleError("Can't LOOKUP(racktables_networks): module PyMySQL is not installed")
        self.set_options(var_options=variables, direct=kwargs)
        result = []
        try:
            connection = pymysql.connect(host=self.get_option('rt_host'),port=self.get_option('rt_port'),user=self.get_option('rt_username'),password=self.get_option('rt_password'),db=self.get_option('rt_database'))
        except Exception as e:
            raise AnsibleError("Encountered an issue while connecting to the database, this was the original exception: %s" % to_native(e))
        rt_network_sql_start = "SELECT INET_NTOA(IPv4Network.ip),IPv4Network.mask,IPv4Network.name,VLANIPv4.vlan_id FROM IPv4Network,TagStorage,VLANIPv4 WHERE IPv4Network.id=TagStorage.entity_id AND TagStorage.entity_realm='ipv4net' AND TagStorage.tag_id in ( "
        rt_network_sql_tags = ""
        for tag in self.get_option('tags'):
            rt_network_sql_tags += "(SELECT id FROM TagTree WHERE tag='{}'),".format(tag)
        rt_network_sql_tags = rt_network_sql_tags[:-1]
        rt_network_sql_end = ") AND VLANIPv4.ipv4net_id = IPv4Network.id GROUP BY TagStorage.entity_id HAVING count(entity_id)>{}".format(len(self.get_option('tags'))-1)
        rt_network_sql = rt_network_sql_start + rt_network_sql_tags + rt_network_sql_end
        with connection.cursor() as cursor:
            cursor.execute(rt_network_sql)
            rtNetworks = cursor.fetchall()
            for network in rtNetworks:
              networkObject={"network":"","name":"","vlan":""}
              networkObject['network'] = ('{}/{}'.format(network[0],network[1]))
              networkObject['name']=network[2]
              networkObject['vlan']=network[3]
              result.append(networkObject)
        return result
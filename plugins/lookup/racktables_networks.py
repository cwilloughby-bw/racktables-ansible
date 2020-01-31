from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = """
    lookup: racktables_networks
    author: Chandler Willoughby
    version_added: "0.0"
    short_description: Lookup networks in Racktables
    requirements:
      - PyMySql (python3 library)
    description:
      - Returns a list of networks based on the provided tags
    options:
      _terms:
        region: The datacenter region the network is tagged in
        description: object name as it exists in Racktables
        required: True
        type: string
"""

EXAMPLES = """
- name: lookup object network information
  debug: msg="{{lookup('racktables_networks', ['testhost.lab1'])}}"
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
        rtnet_region=terms[0]
        rtnet_ipamzone=terms[1]
        rtnet_ipampurpose=terms[2]
        rt_params=terms[3]
        result = []
        connection = pymysql.connect(host=rt_params['host'],user=rt_params['user'],password=rt_params['pass'],db=rt_params['database'])
        rt_network_sql=("SELECT INET_NTOA(IPv4Network.ip),IPv4Network.mask,IPv4Network.name,VLANIPv4.vlan_id "
                        "FROM IPv4Network,TagStorage,VLANIPv4 "
                        "WHERE IPv4Network.id=TagStorage.entity_id AND TagStorage.entity_realm='ipv4net' AND TagStorage.tag_id in ( "
                        "(SELECT CT.id FROM TagTree PT, TagTree CT WHERE CT.parent_id=PT.id AND PT.tag='Location' AND CT.tag='{}'), "
                        "(SELECT CT.id FROM TagTree PT, TagTree CT WHERE CT.parent_id=PT.id AND PT.tag='ipam_zone' AND CT.tag='{}'), "
                        "(SELECT CT.id FROM TagTree PT, TagTree CT WHERE CT.parent_id=PT.id AND PT.tag='ipam_purpose' AND CT.tag='{}')) "
                        "AND VLANIPv4.ipv4net_id = IPv4Network.id "
                        "GROUP BY TagStorage.entity_id HAVING count(entity_id)>2").format(rtnet_region,rtnet_ipamzone,rtnet_ipampurpose)
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
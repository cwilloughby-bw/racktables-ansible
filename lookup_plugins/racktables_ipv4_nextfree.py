from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = """
    lookup: racktables_ipv4_nextfree
    author: Chandler Willoughby
    version_added: "0.0"
    short_description: Lookup the next free ipv4 address that matches the provided tags
    requirements:
      - PyMySql (python3 library)
    description:
      - Returns a new IPv4 address/gateway/netmask that matches the provided tags
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
  debug: msg="{{ lookup('racktables_ipv4_nextfree', rt_host='rackhost.local', rt_username='rackuser', rt_password='sup3r$3cur3', rt_database='rackdb', tags=('LAB1-RDU','trust','application')) }}"
"""

RETURN = """
  _ipaddress:
    description:
      - Dictionary containing the candidate IP address
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
            raise AnsibleError("Can't LOOKUP(racktables_ipv4_nextfree): module PyMySQL is not installed")
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
            if not rtNetworks:
                raise AnsibleError("No networks were returned, please check your provided tags")
            for network in rtNetworks:
                ipnetwork = ipaddress.ip_network("{}/{}".format(network[0],network[1]))
                for address in ipnetwork.hosts():
                    if address == ipnetwork[1] or address == ipnetwork[2]:
                        # In or scheme, this represents the gateway addresses, so we ignore them in the event that they weren't entered into racktables
                        continue
                    cursor.execute("SELECT INET_NTOA(ip) FROM IPv4Allocation WHERE ip=INET_ATON(%s) UNION SELECT INET_NTOA(ip) FROM IPv4Address WHERE ip=INET_ATON(%s)",(str(address),str(address)))
                    # Check if the IP is registered anywhere in Racktables
                    if not cursor.fetchall():
                        # Check if the IP responds to pings
                        pingtest = os.system("ping -c 1 -W 2 " + str(address) + ">/dev/null")
                        if pingtest == 0:
                            raise AnsibleError("The address {} wasn't in Racktables, but responded to a ping. Please investigate!".format(str(address)))
                        else:
                            addressObject={"address":"","netmask":"","gateway":"","netname":"","vlan":""}
                            addressObject['address'] = str(address)
                            addressObject['netmask'] = str(ipnetwork.netmask)
                            addressObject['gateway'] = str(ipnetwork[1])
                            addressObject['netname'] = network[2]
                            addressObject['vlan'] = network[3]
                            result.append(addressObject)
                            return result
        raise AnsibleError("Unable to find a free address with the provided tags. Please ask IPEng to create a new network with the following parameters: {}".format(self.get_option('tags')))
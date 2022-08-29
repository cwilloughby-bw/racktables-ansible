from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = """
    lookup: racktables_vlans
    author: Chandler Willoughby
    version_added: "0.0"
    short_description: Lookup vlans in Racktables with the provided domain
    requirements:
      - PyMySql (python3 library)
    description:
      - Returns a list of vlans provisioned in the provided domain
    options:
        domain:
            description: The domain we should fetch VLANs from
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
  debug: msg="{{ lookup('racktables_networks', rt_host='rackhost.local', rt_username='rackuser', rt_password='sup3r$3cur3', rt_database='rackdb', domain=MainDC) }}"
"""

RETURN = """
  _list:
    description:
      - List of VLANs in the specified domain
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
        rt_vlan_sql = "SELECT vdesc.vlan_id, vdesc.vlan_descr  FROM VLANDomain vdom, VLANDescription vdesc WHERE vdom.description = {} and vdesc.domain_id = vdom.id "
        with connection.cursor() as cursor:
            cursor.execute(rt_vlan_sql.format(self.get_option('domain')))
            rtVlans = cursor.fetchall()
            for vlan in rtVlans:
                vlanObject={"tag":"","name":""}
                vlanObject['tag']=vlan[0]
                vlanObject['name']=vlan[1]
                result.append(vlanObject)
        return result
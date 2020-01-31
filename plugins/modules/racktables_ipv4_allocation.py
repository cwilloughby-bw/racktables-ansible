#!/usr/bin/python

# Copyright: (c) 2020, Chandler Willoughby <cwilloughby@bandwidth.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: racktables_ipv4_allocation

short_description: Manages IPv4 address allocations in Racktables

version_added: "2.4"

description:
    - "Create, update, and delete IPv4 allocations in Racktables"

options:
    object:
        description:
            - This is the name of the device that this address is assigned to
        required: true
    interface:
        description:
            - This is the interface name that the address is assigned to on the object
        required: false
    ip:
        description:
            - This is the IP address that will be assigned
        required: true
    type:
        description:
            - The type of IP/Interface (regular,shared,virtual,router,point2point)) (Default: regular)
        required: false
    rt_host:
        description:
            - Hostname of the database server backing Racktables
        required: true
    rt_port:
        description:
            - Port for the database connection, defaults to 3306
        required: false
    rt_username:
        description:
            - Username that has administrative access to the racktables database
        required: true
    rt_password:
        description:
            - Password for the administrative user
        required: true
    rt_database:
        description:
            - Name of the database which backs Racktables
        required: true

author:
    - Chandler Willoughby (@cwilloughby-bw)
'''

EXAMPLES = '''
# Assign an IP address to an object
- name: Assign an IP address to an object
  racktables_ipv4_allocation:
    name: "test.lab1"
    interface: "eth0"
    ip: "192.0.2.1"
    type: "regular"
'''

RETURN = '''
original_message:
    description: The original name param that was passed in
    type: str
    returned: always
message:
    description: The output message that the test module generates
    type: str
    returned: always
'''
HAVE_PYMYSQL = False
try:
    import pymysql.cursors
    import ipaddress
    import os
    HAVE_PYMYSQL = True
except ImportError:
    pass

from ansible.errors import AnsibleError
from ansible.module_utils.basic import AnsibleModule

def run_module():
    if HAVE_PYMYSQL is False:
        raise AnsibleError("Can't run module racktables_object: module PyMySQL is not installed")
    module_args = dict(
        object=dict(type='str', required=True),
        interface=dict(type='str', required=True),
        ip=dict(type='str', required=False),
        type=dict(type='str', required=False, default="regular"),
        rt_host=dict(type='str',required=True),
        rt_port=dict(type='int',required=False,default=3306),
        rt_username=dict(type='str',required=True),
        rt_password=dict(type='str',required=True,no_log=True),
        rt_database=dict(type='str',required=True)
    )

    result = dict(
        changed=False,
        original_object='',
        original_interface='',
        original_ip='',
        original_type='',
        object='',
        interface='',
        ip='',
        type='',
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    try:
        connection = pymysql.connect(host=module.params['rt_host'],port=module.params['rt_port'],user=module.params['rt_username'],password=module.params['rt_password'],db=module.params['rt_database'])
    except:
        raise AnsibleError("An error occured while connecting to your Racktables database, please check your connection info and try again")

    rt_allocation_sql="SELECT RTO.name,INET_NTOA(RTIP.ip),RTIP.name,RTIP.type FROM IPv4Allocation RTIP, Object RTO WHERE RTIP.object_id=RTO.id AND RTO.name=%s AND RTIP.name=%s"
    rt_allocation={}
    with connection.cursor() as cursor:
        cursor.execute(rt_allocation_sql,(module.params['object'],module.params['interface']))
        rt_allocation = cursor.fetchone()
        print(rt_allocation)
        if rt_allocation:
            result['original_object']=rt_allocation[0]
            result['original_interface']=rt_allocation[2]
            result['original_ip']=rt_allocation[1]
            result['original_type']=rt_allocation[3]

    if module.check_mode:
        module.exit_json(**result)

    props_match = False
    if rt_allocation:
        if module.params['object'] == rt_allocation[0] and module.params['interface'] == rt_allocation[2] and module.params['ip'] == rt_allocation[1] and module.params['type'] == rt_allocation[3]:
            props_match = True
    
    if not props_match and not module.check_mode:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM Object WHERE name=%s",module.params['object'])
            try:
                object_id = cursor.fetchone()[0]
            except:
                module.fail_json(msg="Provided object doesn't exist, please check spelling or create object", **result)
            if rt_allocation:
                cursor.execute("UPDATE IPv4Allocation SET ip=INET_ATON(%s), type=%s WHERE object_id=%s AND name=%s;",(module.params['ip'],module.params['type'],object_id,module.params['interface']))
            if not rt_allocation:
                cursor.execute("INSERT INTO IPv4Allocation (object_id, ip, name, `type`) VALUES(%s, INET_ATON(%s), %s, %s);",(object_id,module.params['ip'],module.params['interface'],module.params['type']))
        connection.commit()
        result['changed'] = True
        result['object'] = module.params['object']
        result['interface'] = module.params['interface']
        result['ip'] = module.params['ip']
        result['type'] = module.params['type']

    module.exit_json(**result)

def main():
    run_module()

if __name__ == '__main__':
    main()
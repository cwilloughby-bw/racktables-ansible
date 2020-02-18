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
module: racktables_object_port

short_description: Manages object ports in Racktables

version_added: "2.4"

description:
    - "Create, update, and delete object ports in Racktables"

options:
    object:
        description:
            - The name of the object
        required: true
    name:
        description:
            - The name of the port
        required: true
    innerinterface:
        description:
            - The type of inner interface of the port. Expects one of (CFP, CFP2, CPAK, GBIC, hardwired, QSFP+, SFP-100, SFP-1000, SFP+, X2, XENPAK, XFP, XPAK)
        required: false
        default: hardwired
    type:
        description:
            - The type of outer interface of the port
        required: false
        default: 1000Base-T
    l2address:
        description:
            - Optional L2 address of the port
        required: false
    reservation:
        description:
            - An optional reservation comment
        required: false
    label:
        description:
            - An optional label for the port
        required: false
    state:
        description:
            - Specify wether the port should be present or absent
        required: false
        default: present
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
# Create a port on an object in Racktables
- name: Create a new port
  racktables_object_port:
    object: "test.lab1"
    name: "eth0"
    innerinterface: "SFP+"
    type: "10G Twinax"
    l2address: "DE:AD:BE:EF:12:34"
    reservation: "Firewall Upgrade"
    label: "WAN link"
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
        name=dict(type='str', required=True),
        innerinterface=dict(type='str', required=False, default="hardwired", choices=['CFP', 'CFP2', 'CPAK', 'GBIC', 'hardwired', 'QSFP+', 'SFP-100', 'SFP-1000', 'SFP+', 'X2', 'XENPAK', 'XFP', 'XPAK']),
        type=dict(type='str', required=False, default="1000Base-T"),
        l2address=dict(type='str', required=False),
        reservation=dict(type='str', required=False),
        label=dict(type='str', required=False, default=""),
        state=dict(type='str', default='present', choices=['present', 'absent']),
        rt_host=dict(type='str',required=True),
        rt_port=dict(type='int',required=False,default=3306),
        rt_username=dict(type='str',required=True),
        rt_password=dict(type='str',required=True,no_log=True),
        rt_database=dict(type='str',required=True)
    )

    result = dict(
        changed=False,
        original_object='',
        original_name='',
        original_innerinterface='',
        original_type='',
        original_l2address='',
        original_reservation='',
        original_label='',
        object='',
        name='',
        innerinterface='',
        type='',
        l2address='',
        reservation='',
        label='',
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )


    try:
        connection = pymysql.connect(host=module.params['rt_host'],port=module.params['rt_port'],user=module.params['rt_username'],password=module.params['rt_password'],db=module.params['rt_database'])
    except:
        raise AnsibleError("An error occured while connecting to your Racktables database, please check your connection info and try again")

    def validatePortCompatibility(iif, oif):
        with connection.cursor() as cursor:
            try:
                cursor.execute("SELECT id FROM PortInnerInterface WHERE iif_name=%s",iif)
                iif_id = cursor.fetchone()[0]
            except:
                iif_id = 0
            try:
                cursor.execute("SELECT id FROM PortOuterInterface WHERE oif_name=%s",oif)
                oif_id = cursor.fetchone()[0]
            except:
                oif_id = 0
            cursor.execute("SELECT iif_id, oif_id FROM PortInterfaceCompat WHERE iif_id=%s AND oif_id=%s",(iif_id, oif_id))
            compat = cursor.fetchone()
            if compat:
                return True
            else:
                return False
    
    def validateObjectExists(object_name):
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM `Object` WHERE name=%s",object_name)
            rtObject = cursor.fetchone()
            if rtObject:
                return True
            else:
                return False

    rt_port_sql="SELECT RTP.name,RTPI.iif_name,RTPO.oif_name,RTP.l2address,RTP.reservation_comment,RTP.label FROM Object RTO, Port RTP, PortInnerInterface RTPI, PortOuterInterface RTPO WHERE RTPI.id=RTP.iif_id AND RTPO.id=RTP.`type` AND RTP.object_id=RTO.id AND RTO.name=%s AND RTP.name=%s"
    rt_port={}
    with connection.cursor() as cursor:
        cursor.execute(rt_port_sql,(module.params['object'],module.params['name']))
        rt_port = cursor.fetchone()
        if rt_port:
            result['original_object']=module.params['object']
            result['original_name']=rt_port[0]
            result['original_innerinterface']=rt_port[1]
            result['original_type']=rt_port[2]
            result['original_l2address']=rt_port[3]
            result['original_reservation']=rt_port[4]
            result['original_label']=rt_port[4]

    if module.check_mode:
        module.exit_json(**result)

    props_match = False
    if rt_port:
        if module.params['innerinterface'] == rt_port[1] and module.params['type'] == rt_port[2] and module.params['l2address'] == rt_port[3] and module.params['reservation'] == rt_port[4] and module.params['label'] == rt_port[5]:
            props_match = True
    
    if not props_match and not module.check_mode and module.params['state'] == "present":
        with connection.cursor() as cursor:
            if not validatePortCompatibility(module.params['innerinterface'],module.params['type']):
                module.fail_json(msg="The specified inner and outer port types are not compatible", **result)
            if not validateObjectExists(module.params['object']):
                module.fail_json(msg="The specified object does not exist, please check your spelling", **result)
            cursor.execute("SELECT id FROM PortInnerInterface WHERE iif_name=%s",module.params['innerinterface'])
            iif_id = cursor.fetchone()[0]
            cursor.execute("SELECT id FROM PortOuterInterface WHERE oif_name=%s",module.params['type'])
            oif_id = cursor.fetchone()[0]
            cursor.execute("SELECT id FROM `Object` WHERE name=%s",module.params['object'])
            rtObjectId = cursor.fetchone()[0]
            if rt_port:
                cursor.execute("UPDATE Port SET iif_id=%s, `type`=%s, l2address=%s, reservation_comment=%s, label=%s WHERE name=%s;",(iif_id,oif_id,module.params['l2address'],module.params['reservation'],module.params['label'],module.params['name']))
            if not rt_port:
                cursor.execute("INSERT INTO Port (object_id, name, iif_id, `type`, l2address, reservation_comment, label) VALUES(%s, %s, %s, %s, %s, %s, %s);",(rtObjectId,module.params['name'],iif_id,oif_id,module.params['l2address'],module.params['reservation'],module.params['label']))
        connection.commit()
        result['changed'] = True
        result['object']=module.params['object']
        result['name']=module.params['name']
        result['innerinterface']=module.params['innerinterface']
        result['type']=module.params['type']
        result['l2address']=module.params['l2address']
        result['reservation']=module.params['reservation']
        result['label']=module.params['label']
    elif not module.check_mode and module.params['state'] == "absent":
        with connection.cursor() as cursor:
            cursor.execute("SELECT RTP.object_id, RTP.name FROM Port RTP, `Object` RTO WHERE RTP.object_id=RTO.id AND RTO.name=%s AND RTP.name=%s",(module.params['object'],module.params['name']))
            port = cursor.fetchone()
            if port:
                cursor.execute("DELETE FROM Port WHERE object_id=%s AND name=%s",(port[0],module.params['name']))
                connection.commit()
                result['changed'] = True
            else:
                result['changed'] = False

    module.exit_json(**result)

def main():
    run_module()

if __name__ == '__main__':
    main()
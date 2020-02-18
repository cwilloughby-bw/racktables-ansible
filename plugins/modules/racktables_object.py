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
module: racktables_object

short_description: Manages objects in Racktables

version_added: "2.4"

description:
    - "Create, update, and delete objects in Racktables"

options:
    name:
        description:
            - This is the message to send to the test module
        required: true
    label:
        description:
            - Optional text label for the object
        required: false
    type:
        description:
            - Object type
        required: false
        default: VM
    assetnumber:
        description:
            - Optional asset tag for the object
        required: false
    comment:
        description:
            - Optional comment for the object
        required: false
    state:
        description:
            - Specify whether the object should be present or absent
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
# Make a new object in Racktables
- name: Create a new Racktables object
  racktables_object:
    name: "test.lab1"
    label: "testingonly"
    type: "Server"
    assetnumber: "123abc"
    comment: "This is a test server"
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
        name=dict(type='str', required=True),
        label=dict(type='str', required=False, default=""),
        type=dict(type='str', required=False, default="VM"),
        assetnumber=dict(type='str', required=False),
        comment=dict(type='str', required=False, default=""),
        state=dict(type='str', default='present', choices=['present', 'absent']),
        rt_host=dict(type='str',required=True),
        rt_port=dict(type='int',required=False,default=3306),
        rt_username=dict(type='str',required=True),
        rt_password=dict(type='str',required=True,no_log=True),
        rt_database=dict(type='str',required=True)
    )

    result = dict(
        changed=False,
        original_name='',
        original_label='',
        original_type='',
        original_assetnumber='',
        original_comment='',
        name='',
        label='',
        type='',
        assetnumber='',
        comment='',
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    try:
        connection = pymysql.connect(host=module.params['rt_host'],port=module.params['rt_port'],user=module.params['rt_username'],password=module.params['rt_password'],db=module.params['rt_database'])
    except:
        raise AnsibleError("An error occured while connecting to your Racktables database, please check your connection info and try again")

    rt_object_sql="SELECT RTO.name,RTO.label,RTO.asset_no,RTO.comment,RTD.dict_value FROM Object RTO, Dictionary RTD WHERE RTD.dict_key=RTO.objtype_id AND RTO.name=%s"
    rt_object={}
    with connection.cursor() as cursor:
        cursor.execute(rt_object_sql,module.params['name'])
        rt_object = cursor.fetchone()
        if rt_object:
            result['original_name']=rt_object[0]
            result['original_label']=rt_object[1]
            result['original_assetnumber']=rt_object[2]
            result['original_comment']=rt_object[3]
            result['original_type']=rt_object[4]

    if module.check_mode:
        module.exit_json(**result)

    props_match = False
    if rt_object:
        if module.params['label'] == rt_object[1] and module.params['assetnumber'] == rt_object[2] and module.params['comment'] == rt_object[3] and module.params['type'] == rt_object[4]:
            props_match = True
    
    if not props_match and not module.check_mode and module.params['state'] == "present":
        with connection.cursor() as cursor:
            cursor.execute("SELECT dict_key FROM Dictionary WHERE dict_value=%s",module.params['type'])
            try:
                objtype_id = cursor.fetchone()[0]
            except:
                module.fail_json(msg="Object type doesn't exist or isn't spelled properly", **result)
            if rt_object:
                cursor.execute("UPDATE Object SET name=%s, label=%s, objtype_id=%s, asset_no=%s, has_problems='no', comment=%s WHERE name=%s;",(module.params['name'],module.params['label'],objtype_id,module.params['assetnumber'],module.params['comment'],module.params['name']))
            if not rt_object:
                cursor.execute("INSERT INTO `Object` (name, label, objtype_id, asset_no, has_problems, comment) VALUES(%s, %s, %s, %s, 'no', %s);",(module.params['name'],module.params['label'],objtype_id,module.params['assetnumber'],module.params['comment']))
        connection.commit()
        result['changed'] = True
        result['name'] = module.params['name']
        result['label'] = module.params['label']
        result['assetnumber'] = module.params['assetnumber']
        result['comment'] = module.params['comment']
        result['type'] = module.params['type']
    elif not module.check_mode and module.params['state'] == "absent":
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM `Object` WHERE name=%s",module.params['name'])
            objectId = cursor.fetchone()
            if objectId:
                cursor.execute("DELETE FROM `Object` WHERE name=%s",module.params['name'])
                connection.commit()
                result['changed'] = True
            else:
                result['changed'] = False

    module.exit_json(**result)

def main():
    run_module()

if __name__ == '__main__':
    main()
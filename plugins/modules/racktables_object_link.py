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
module: racktables_object_link

short_description: Manages parent/child object relationships in Racktables

version_added: "2.4"

description:
    - "Create, update, and delete objects in Racktables"

options:
    parent:
        description:
            - The name of the parent object
        required: true
    child:
        description:
            - The name of the child object
        required: true
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
    parent: "test.lab1",
    child: "test-child.lab1"
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
        parent=dict(type='str', required=True),
        child=dict(type='str', required=True),
        state=dict(type='str', default='present', choices=['present', 'absent']),
        rt_host=dict(type='str',required=True),
        rt_port=dict(type='int',required=False,default=3306),
        rt_username=dict(type='str',required=True),
        rt_password=dict(type='str',required=True,no_log=True),
        rt_database=dict(type='str',required=True)
    )

    result = dict(
        changed=False,
        original_parent='',
        original_child='',
        parent='',
        child='',
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    try:
        connection = pymysql.connect(host=module.params['rt_host'],port=module.params['rt_port'],user=module.params['rt_username'],password=module.params['rt_password'],db=module.params['rt_database'])
    except:
        raise AnsibleError("An error occured while connecting to your Racktables database, please check your connection info and try again")

    def validateParentCompat(parent,child):
        with connection.cursor() as cursor:
            cursor.execute("SELECT OPC.parent_objtype_id, OPC.child_objtype_id FROM ObjectParentCompat OPC, `Object` RTOP, `Object` RTOC WHERE OPC.parent_objtype_id=RTOP.objtype_id AND OPC.child_objtype_id=RTOC.objtype_id AND RTOP.name=%s AND RTOC.name=%s;",(parent,child))
            compat = cursor.fetchone()
            if compat:
                return True
            else:
                return False
    
    def getEntityLink(parent,child):
        with connection.cursor() as cursor:
            cursor.execute("SELECT RTE.id, RTE.parent_entity_type, RTE.parent_entity_id, RTOP.name, RTE.child_entity_type, RTE.child_entity_id, RTOC.name FROM EntityLink RTE, `Object` RTOP, `Object` RTOC WHERE RTE.parent_entity_id=RTOP.id AND RTE.child_entity_id=RTOC.id AND RTE.parent_entity_type='object' AND RTE.child_entity_type='object' AND RTOP.name=%s AND RTOC.name=%s;",(parent,child))
            entityLink= cursor.fetchone()
            if entityLink:
                return entityLink
            else:
                return None

    existingEntity = getEntityLink(module.params['parent'], module.params['child'])
    if existingEntity:
        result['original_parent'] = existingEntity[0]
        result['original_child'] = existingEntity[1]
        props_match = True

    if module.check_mode:
        module.exit_json(**result)

    props_match = False
    
    if not props_match and not module.check_mode and module.params['state'] == "present":
        with connection.cursor() as cursor:
            if not validateParentCompat(module.params['parent'], module.params['child']):
                module.fail_json(msg="The specified parent and child objects are not compatible")
            cursor.execute("SELECT id FROM `Object` WHERE name=%s",module.params['parent'])
            parentId = cursor.fetchone()[0]
            cursor.execute("SELECT id FROM `Object` WHERE name=%s",module.params['child'])
            childId = cursor.fetchone()[0]
            cursor.execute("INSERT INTO EntityLink (parent_entity_type, parent_entity_id, child_entity_type, child_entity_id) VALUES('object', %s, 'object', %s);",(parentId, childId))
        connection.commit()
        result['changed'] = True
        result['parent'] = module.params['parent']
        result['child'] = module.params['child']
    elif not module.check_mode and module.params['state'] == "absent":
        with connection.cursor() as cursor:
            entityLink = getEntityLink(module.params['parent'], module.params['child'])
            print(entityLink)
            if entityLink:
                cursor.execute('DELETE FROM EntityLink WHERE id=%s',entityLink[0])
                connection.commit()
                result['changed'] = True
            else:
                result['changed'] = False

    module.exit_json(**result)

def main():
    run_module()

if __name__ == '__main__':
    main()
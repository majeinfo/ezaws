# ezaws 
# 

This Python application has 2 purposes:

1.This is a simple Django Web Application that allows you to display
the main information about your AWS Customers.

Each Customer is described in a MySQL Database and you must precise
the ID that allows the Application to make AWS API calls to retrieve information.

On the left side, a list is displayed with the Customer Names. Once you have
selected one, you can get the list of EC2 Instances with their main attributes
and their currently estimated costs.

You can also check if EC2 Instances are snapshotted and you can get a direct link
to their AWS Console.

The list of your ELB (Classic or Application) is also available with the attached Instances and Costs.

The connection to the MySQL Server can be configured with the following environment variables :
    DB_NAME, DB_USER, DB_PASSWORD, DB_HOST

Default value for DB_HOST is "localhost". In that case, you should add a volume definition to mount /var/run/mysqld/mysqld.sock inside the Container.

You can also define DEBUG environment variable to set the DEBUG mode to True (default is False).

2.It also offers in the ezaws/management/commands a set of Python script that can be reused "as-is" to manage your infrastructure.

For example:

- change_instance_type.py : changes the instance type by stopping and restarting it if necessary
- target_group_deregister.py : deregisters an instance from the Target Groups it belongs to
- target_group_register.py : registers an instance in the specified Target Groups

(for DR)
- tag_volumes.py : adds semantic tags to EBS volumes to make a DR easier
- copy_snapshots.py : copies snapshots from an Account to another one to prepare a DR
- copy_security_groups.py : copies Security Groups (and Inbound Rules) from an Account to another one
- recreate_instances.py : recreates an instance from snapshots (for a DR)



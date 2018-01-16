# ezaws

This is a simple Django Web Application that allows you to display
the main information about your AWS Customers.

Each Customer is described in a MySQL Database and you must precise
the ID that allows the Application to make AWS API calls to retrieve information.

On the left side, a list is displayed with the Customer Names. Once you have
selected one, you can get the list of EC2 Instances with their main attributes
and their currently estimated costs.

You can also check if EC2 Instances are snapshotted and you can get a direct link
to their AWS Console.

The list of your ELB (Classic or Application) is also available with the attached Instances and Costs.



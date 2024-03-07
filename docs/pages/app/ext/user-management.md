`ktem` provides user management as an extension. To enable user management, in
your `flowsettings.py`, set the following variables:

- `KH_FEATURE_USER_MANAGEMENT`: True to enable.
- `KH_FEATURE_USER_MANAGEMENT_ADMIN`: the admin username. This user will be
  created when the app 1st start.
- `KH_FEATURE_USER_MANAGEMENT_PASSWORD`: the admin password. This value
  accompanies the admin username.

Once enabled, you have access to the following features:

- User login/logout (located in Settings Tab)
- User changing password (located in Settings Tab)
- Create / List / Edit / Delete user (located in Admin > User Management Tab)

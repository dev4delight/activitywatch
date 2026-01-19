WebUI Enterprise Patches
========================

These files add the Employee Selector dropdown to the ActivityWatch web interface.

Files:
------
- employee-selector.js  : JavaScript that adds employee dropdown to Activity view
- index.html           : Modified index.html that loads the employee-selector.js
- apply-patches.bat    : Script to apply patches to any aw-webui installation

How to Apply:
-------------
Run: apply-patches.bat [path-to-webui-dist]

Examples:
  apply-patches.bat C:\activitywatch\aw-server-rust\static
  apply-patches.bat ..\aw-webui\dist

What it does:
-------------
- Adds an "Employee" dropdown next to the date selector in Activity view
- Allows admin to switch between viewing different employees' data
- Stores selection in localStorage
- Fetches employee list from /api/0/admin/employees

Requirements:
-------------
- Enterprise MySQL server running (mysql_server.py)
- At least one employee registered with a device

# Setup environment

## Configure devcontainer

When you opened the project in Visual Studio Code it most likely already prompts you with starting it inside a devcontainer.
However you first need to configure it correctly before starting it.
In the [devcontainer.json](.devcontainer/devcontainer.json) file you will want to configure the following parameters

| Parameter         | Description                                       | Comments                              |
| -------------     |:-------------:                                    | -----:                                |
| DEVICE_ID         | the ID (MQTT clientId) your devcontainer will use |                                       |
| THIN_EDGE_VERSION | The to be installed thin-edge version             |                                       |
| C8Y_URL           | The Cumulocity IoT instance to connect to         |                                       |
| C8Y_TENANT        | The tenantId of your Cumulocity IoT tenant        | This is only used to upload the cert  |
| C8Y_USER          | The username of your Cumulocity IoT user          | This is only used to upload the cert  |

## Starting the devcontainer

You can click the devcontainer icon in the bottom left of Visual Studio Code and select `Open Folder in Container...`.
When you start it the first time it will prompt you with a password. You will need to enter the password for the user that you provided for `C8Y_TENANT` and `C8Y_USER`. This will upload the just generated self-signed certificate to the tenant.
The password prompt will not appear if you restart the container (only if you completely delete and recreate it).

# Build module

## Create debian package

From the level of your setup.py run the following commands

1. Run ```python3 setup.py sdist```
2. Extract the tar.gz file inside the dist folder ```tar xvzf```
2. Copy the "debian" and "etc" dir into the dist/{module name}/debian dir
3. From the project folder inside dist dir run ```dpkg-buildpackage -rfakeroot -uc -us```
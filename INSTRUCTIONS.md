## Installation of the plugin

```sudo apt install ./thin-edge-file-management-python3_1.0-1_all.deb```

## Configuration of the plugin

The configuration is located under ```/etc/thin-edge-filemanagement/file-management.yml```.
If you have no special configuration of the thin-edge itself the standard configuration of this plugin should work.
The plugin will also automatically create a service entry for systemd and start.

Note: If you change the configuration on file system level you need to manually restart the plugin

## Working with configurations through Cumulocity

The plugin allows essentially to add any file system path as a configuration to the plugin. You will afterwards be able to read and replace the file through Cumulocity configuration UI.
When you change the configuration file of the plugin itself via Cumulocity the plugin will restart automatically and the new configuration will be used.
If you are changing other files it depends on the respective software if it can dynamically use the new configuration.

## Working with logfiles

Same as with the configuration you can essentially add any file system path as a logfile. Afterwards you can read it through the Cumulocity logfile UI.
Currently the filters in the UI for logfiles are not supported and simply ignored by the plugin. It will always upload the whole file.

## Writing other plugins with manageable configuration files

Whenever this plugin writes a configuration file it will announce that on the MQTT of thin-edge. On the topic ```filemanagement/changes``` it will send a JSOn structure like this:
```
{
    "changedFile": "path/to/file"
}
```

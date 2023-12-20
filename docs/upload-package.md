Devpi server endpoint (subjected to change): https://ian_devpi.promptui.dm.cinnamon.is/root/packages

Install devpi-client

```bash
pip install devpi-client
```

Login to the server

```bash
devpi use <server endpoint> # set server endpoint provided above
devpi login <user name> --password=<your password> # login
```

If you don't yet have an account, please contact Ian or John.

Upload your package

```bash
devpi use <package name>\dev # choose the index to upload your package
cd <your package directory which must contain a pyproject.toml/setup.py>
devpi upload
```

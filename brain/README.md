# Layer Robot Brain

To start the Brain:

* For production; create a virtual environment (or skip it when you are running in a container like environment) and
  install the package: `pip install .`
* Alter the bot.config.template and remove* *.template
* Run `start-robot`  (see the console_scripts in [setup.py](/setup.py) on what is called exactly)

# change root directory

The software by default is expecting to work in a folder named `/home/pi/brain`.

If you want to change the root directory to another one please run the command:

`ROOT=/Users/.../growx-robot-elevator-software python3 src/command/bot.py`

## Setup dev env:

Create a virtual environment & install dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
```

Make sure you set the correct environment in your favorite IDE!

### Before you create a pull request make sure flake8 succeeds without errors:

```bash
flake8 src/
```

TODO: Update production install instructions!

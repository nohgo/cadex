"""Private-socket launcher for the pinned upstream SkillBridge server."""
import json
import os
from pathlib import Path
import runpy

if __name__ == '__main__':
    config = json.loads((Path(__file__).parent / 'config.json').read_text())
    os.umask(0o077)
    os.environ['SKILLBRIDGE_LOG_DIRECTORY'] = config['log_dir']
    runpy.run_module('skillbridge.server.python_server', run_name='__main__')

#!/usr/bin/env python3
import subprocess
import sys
import papermill
from shutil import which


def main():
    positional_arguments = []
    parameters = {}
    for arg in sys.argv[1:]:
        if '=' in arg:
            name, value = arg.split('=', maxsplit=1)
            parameters[name] = value
        else:
            positional_arguments.append(arg)

    if len(positional_arguments) != 2 and len(positional_arguments) != 3:
        raise ValueError(
            'Got {} positional arguments (expected 2 or 3): {}'.format(len(positional_arguments), positional_arguments)
        )

    if len(positional_arguments) == 3:
        download_requirements(positional_arguments[2])

    try:
        papermill.execute_notebook(
            positional_arguments[0],
            positional_arguments[1],
            parameters=parameters,
            progress_bar=False
        )
    except papermill.PapermillExecutionError as e:
        print(e, file=sys.stderr)
        return 1
    return 0


def download_requirements(requirements_file):
    pip_command = None
    for command in ['pip3', 'pip']:
        if which(command) is not None:
            pip_command = command
    if pip_command is None:
        raise EnvironmentError('Cannot find pip executable. Neither "pip3" nor "pip" is available')

    result = subprocess.run([pip_command, 'install', '-r', requirements_file], capture_output=True)
    if result.returncode != 0:
        raise EnvironmentError('Failed to install python requirements.\n{}'.format(result.stderr))


if __name__ == '__main__':
    sys.exit(main())

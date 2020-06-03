#!/usr/bin/env python3

import sys
import papermill


def main():
    notebooks = []
    parameters = {}
    for arg in sys.argv[1:]:
        if '=' in arg:
            name, value = arg.split('=', maxsplit=1)
            parameters[name] = value
        else:
            notebooks.append(arg)

    if len(notebooks) != 2:
        raise ValueError('Got {} notebook parameters (expected 2): {}'.format(len(notebooks), notebooks))

    try:
        papermill.execute_notebook(
            notebooks[0],
            notebooks[1],
            parameters=parameters,
            progress_bar=False
        )
    except papermill.PapermillExecutionError as e:
        print(e)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

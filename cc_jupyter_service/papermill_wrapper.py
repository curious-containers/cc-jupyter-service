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

    papermill.execute_notebook(
        notebooks[0],
        notebooks[1],
        parameters=parameters
    )


if __name__ == '__main__':
    main()

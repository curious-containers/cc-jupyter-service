RED_FILE_TEMPLATE = {
    "redVersion": "9",
    "cli": {
        "cwlVersion": "v1.0",
        "class": "CommandLineTool",
        "baseCommand": ["papermill"],
        "doc": "Executes a jupyter notebook",
        "inputs": {
            "inputNotebook": {
                "type": "File",
                "inputBinding": {"position": 1}
            },
            "outputNotebookFilename": {
                "type": "string",
                "inputBinding": {"position": 2}
            }
        },
        "outputs": {
            "outputNotebook": {
                "type": "File",
                "outputBinding": {
                    "glob": "$(inputs.outputNotebookFilename)"
                }
            }
        }
    },
    "inputs": {
        "inputNotebook": {
            "class": "File",
            "connector": {
                "command": "red-connector-http-json",
                "access": {
                    "url": None,  # replaced with the url of this jupyter service
                    "method": "GET",
                    "auth": {
                        "username": None,  # replaced with the username of the request
                        "password": None,  # replaced with the generated token
                    }
                }
            },
            "basename": "inputNotebook.ipynb"
        },
        "outputNotebookFilename": "output.ipynb"
    },
    "outputs": {
        "outputNotebook": {
            "class": "File",
            "connector": {
                "command": "red-connector-http",
                "access": {
                    "url": None,  # replaced with the url of this jupyter service
                    "auth": {
                        "username": None,  # replaced with the username of the request
                        "password": None,  # replaced with the generated token
                    }
                }
            }
        }
    },
    "container": {
        "engine": "docker",
        "settings": {
            "image": {
                "url": "bruno1996/argprinter_image"  # TODO: change image
            },
            "ram": 4096
        }
    },
    "execution": {
        "engine": "ccagency",
        "settings": {
            "access": {
                "url": None,  # replaced with the agency url of the request
                "auth": {
                    "username": None,  # replaced with the agency username of the request
                    "password": None,  # replaced with the agency password of the request
                }
            }
        }
    }
}

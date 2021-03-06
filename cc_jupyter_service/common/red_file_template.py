RED_FILE_TEMPLATE = {
    "redVersion": "9",
    "cli": {
        "cwlVersion": "v1.0",
        "class": "CommandLineTool",
        "baseCommand": ["papermill_wrapper.py"],
        "doc": "Executes a jupyter notebook",
        "inputs": {
            "inputNotebook": {
                "type": "File",
                "inputBinding": {"position": 1}
            },
            "outputNotebookFilename": {
                "type": "string",
                "inputBinding": {"position": 2}
            },
            "pythonRequirements": {
                "type": "File?",
                "inputBinding": {"position": 3}
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
        "outputNotebookFilename": "output.ipynb",
        "pythonRequirements": {
            "class": "File",
            "connector": {
                "command": "red-connector-http",
                "access": {
                    "url": None,
                    "method": "GET",
                    "auth": {
                        "username": None,
                        "password": None
                    }
                }
            },
            "basename": "requirements.txt"
        }
    },
    "outputs": {
        "outputNotebook": {
            "class": "File",
            "connector": {
                "command": "red-connector-http-json",
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
                "url": None  # replaced with the image selected by the user
            },
            "ram": 4096*8  # 32 GB
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

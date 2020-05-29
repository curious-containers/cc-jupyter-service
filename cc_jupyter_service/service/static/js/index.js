$(document).ready(function() {
    const DEFAULT_GPU_VRAM = 2048;
    class NotebookEntry {
        data;
        filename;

        constructor(data, filename) {
            this.data = data;
            this.filename = filename;
        }
    }

    class ExternalDataEntry {
        inputName;
        inputType;
        connectorType;
        host;
        path;
        username;
        password;
        mount;

        constructor(inputName=null, inputType=null, connectorType=null, host=null, path=null, username=null, password=null, mount=null) {
            this.inputName = inputName;
            this.inputType = inputType;
            this.connectorType = connectorType;
            this.host = host;
            this.path = path;
            this.username = username;
            this.password = password;
            this.mount = mount;
        }
    }

    let jupyterNotebookEntries = [];
    const dependenciesSelection = {
        custom: false,
        predefinedImage: 'Base Image',
        customImage: ''
    }
    let globalPredefinedImages = [];
    let gpuRequirements = [];
    let externalDataInfo = [];

    /**
     * Fetches the predefined docker images from the server
     */
    function updatePredefinedDockerImages() {
        let url = getUrl('predefined_docker_images');

        // noinspection JSIgnoredPromiseFromCall
        $.ajax({
            url,
            method: 'GET',
            dataType: 'json',
        }).fail(function (e, statusText, errorMessage) {
            console.error('failed to fetch predefined docker images info:', errorMessage, e.responseText);
            addAlert('danger', 'Failed to fetch predefined docker images!');
        }).done(function (d) {
            globalPredefinedImages = d;
            setupDependencies($('#dependenciesPredefined'), $('#predefinedImages'), $('#dependenciesCustom'), $('#customDockerImage'));
        });
    }

    updatePredefinedDockerImages();

    function setupAlertSection(main) {
        main.append('<div id="alertSection"></div>');
    }

    /**
     * Setup the click events for the navigation bar
     */
    function setupNavbar(main, mode) {
        main.append(
            '<nav class="navbar navbar-expand-sm bg-dark navbar-dark sticky-top">' +
            '<ul class="navbar-nav">' +
            '<li class="nav-item"><a id="ExecutionNavbar" class="nav-link">Execution</a></li>' +
            '<li class="nav-item"><a id="ResultNavbar" class="nav-link">Results</a></li>' +
            '</ul>' +
            '<ul class="navbar-nav ml-auto">' +
            '<li class="nav-item"><a id="LogoutNavbar" class="nav-link">Logout</a></li>' +
            '</ul>' +
            '</nav>'
        );
        if (mode === 'execution') {
            main.find('#ExecutionNavbar').addClass('active');
        } else {
            main.find('#ResultNavbar').addClass('active');
        }
        $('#ExecutionNavbar').click(showExecutionView);
        $('#ResultNavbar').click(showResultView);
        $('#LogoutNavbar').click(function() {
            window.location = getUrl('auth/logout');
        });
    }

    /**
     * Removes all elements from the main view
     */
    function clearView(main) {
        main.empty();
    }

    /**
     * Returns the url for the given endpoint
     *
     * @param endpoint The endpoint as string
     */
    function getUrl(endpoint) {
        let url = window.location.href;
        if (!url.endsWith('/')) {
            url = url + '/'
        }
        return new URL(endpoint, url).href;
    }

    /**
     * Adds the right elements to the image selection by inspecting the dependenciesSelection Variable.
     *
     * @param predefinedImagesRadio The radio selection for predefined images
     * @param predefinedImages The html select element that stores the predefined images
     * @param customImagesRadio The html radio selection for custom images
     * @param customImages The html input element that stores the custom image name
     */
    function setupDependencies(predefinedImagesRadio, predefinedImages, customImagesRadio, customImages) {
        predefinedImagesRadio.prop('checked', !dependenciesSelection.custom);
        customImagesRadio.prop('checked', dependenciesSelection.custom);
        predefinedImages.prop('disabled', dependenciesSelection.custom);
        customImages.prop('disabled', !dependenciesSelection.custom);

        predefinedImages.empty();
        for (const predefinedImageId of globalPredefinedImages) {
            const option = $('<option value="' + predefinedImageId.name + '">' + predefinedImageId.name + '</option>')
            predefinedImages.append(option);
            option.prop('selected', predefinedImageId.name === dependenciesSelection.predefinedImage);
        }

        customImages.val(dependenciesSelection.customImage);

        // setup callbacks
        predefinedImagesRadio.click(function() {
            dependenciesSelection.custom = false;
            predefinedImages.prop('disabled', false);
            customImages.prop('disabled', true);
        })
        predefinedImages.on('input', function() {
            dependenciesSelection.predefinedImage = predefinedImages.val();
        })
        customImagesRadio.click(function() {
            dependenciesSelection.custom = true;
            predefinedImages.prop('disabled', true);
            customImages.prop('disabled', false);
        })
        customImages.on('input', function() {
            dependenciesSelection.customImage = customImages.val();
            console.log(customImages.val());
        })
    }

    function refreshGpuList(gpuList) {
        gpuList.empty();
        let index = 0;
        for (const gpuRequirement of gpuRequirements) {
            const tmpIndex = index;
            const gpuVram = $('<input id="gpuVram' + tmpIndex + '" type="number" value="' + gpuRequirement + '" step="1024">');
            gpuVram.on('input', function() {
                gpuRequirements[tmpIndex] = parseInt(gpuVram.val().toString());
            })
            const li = $('<li class="list-group-item"><label for="gpuVram' + tmpIndex + '" class="label">VRAM in MB</label></li>');
            li.append(gpuVram);

            const removeBtn = $('<button id="gpuRemove' + tmpIndex + '" type="button" class="close fixPadding"><i class="fa fa-times-circle"></i></button>');
            removeBtn.click(function() {
                gpuRequirements.splice(tmpIndex, 1);
                refreshGpuList($('#gpuList'));
            })
            li.append(removeBtn);
            gpuList.append(li);
            index += 1;
        }
        if (gpuRequirements.length === 0) {
            gpuList.append('<li class="list-group-item border-0 text-muted">No GPUs requested</li>');
        }
    }

    function addAlert(alertType, text) {
        const alertSection = $('#alertSection');
        const alert = $('<div class="alert alert-' + alertType + ' alert-dismissible"></div>');
        alert.append('<button type="button" class="close" data-dismiss="alert">&times</button>');
        alert.append(text);
        alertSection.append(alert);
    }

    function refreshExternalDataList(externalDataList) {
        externalDataList.empty();
        let index = 0;

        function refreshExternalDataSubSection(externalDataSubSection, externalDataEntry, elemIndex) {
            externalDataSubSection.empty();
            externalDataSubSection.append('<label for="externalDataInputName' + elemIndex + '">Input Name: </label>');
            const inputNameInput = $('<input type="text" id="externalDataInputName' + elemIndex + '" class="form-control no-break">');
            inputNameInput.on('input', function() {
                externalDataEntry.inputName = inputNameInput.val();
            })
            inputNameInput.val(externalDataEntry.inputName);
            externalDataSubSection.append(inputNameInput);
            const typeSelect = $('<select id="externalDataTypeSelect' + elemIndex + '">')

            for (const opt of [null, 'File', 'Directory']) {
                let text = opt;
                if (opt == null) text = '-';
                const option = $('<option value="' + opt + '">' + text + '</option>');
                option.prop('selected', externalDataEntry.inputType === opt);
                typeSelect.append(option);
            }

            typeSelect.on('input', function () {
                let val = typeSelect.val();
                if (val === 'null') {
                    val = null;
                }
                externalDataInfo[elemIndex].inputType = val;
                refreshExternalDataSubSection(externalDataSubSection, externalDataEntry, elemIndex);
            });
            externalDataSubSection.append(typeSelect);

            const removeExternalDataEntryButton = $('<button id="externalDataRemove' + elemIndex + '" type="button" class="close fixPadding"><i class="fa fa-times-circle"></i></button>');
            removeExternalDataEntryButton.click(function() {
                externalDataInfo.splice(elemIndex, 1);
                refreshExternalDataList($('#externalDataList'))
            })
            externalDataSubSection.append(removeExternalDataEntryButton);

            if (externalDataEntry.inputType === null) {
            } else if (externalDataEntry.inputType === 'File') {
                const connectorTypeSelect = $('<select id="externalDataConnectorTypeSelect' + elemIndex + '">');
                for (const opt of [null, 'SSH']) {
                    let text = opt;
                    if (opt == null) text = '-';
                    const option = $('<option value="' + opt + '">' + text + '</option>');
                    option.prop('selected', externalDataEntry.connectorType === opt);
                    connectorTypeSelect.append(option);
                }
                connectorTypeSelect.on('input', function() {
                    let val = connectorTypeSelect.val();
                    if (val === 'null') {
                        val = null;
                    }
                    externalDataEntry.connectorType = val;
                    refreshExternalDataSubSection(externalDataSubSection, externalDataEntry, elemIndex);
                });
                externalDataSubSection.append(connectorTypeSelect);

                if (externalDataEntry.connectorType === 'SSH') {
                    externalDataSubSection.append('<br>');
                    externalDataSubSection.append('<label for="externalDataHost' + elemIndex + '">Host: </label>');
                    const hostInput = $('<input type="text" id="externalDataHost' + elemIndex + '" class="form-control no-break">');
                    hostInput.on('input', function() {
                        externalDataEntry.host = hostInput.val();
                    })
                    hostInput.val(externalDataEntry.host);
                    externalDataSubSection.append(hostInput);

                    externalDataSubSection.append('<br>');
                    externalDataSubSection.append('<label for="externalDataFilePath' + elemIndex + '">Filepath: </label>');
                    const filePathInput = $('<input type="text" id="externalDataFilePath' + elemIndex + '" class="form-control no-break">');
                    filePathInput.on('input', function() {
                        externalDataEntry.path = filePathInput.val();
                    })
                    filePathInput.val(externalDataEntry.path);
                    externalDataSubSection.append(filePathInput);

                    externalDataSubSection.append('<br>');
                    externalDataSubSection.append('<label for="externalDataUsername' + elemIndex + '">Username: </label>');
                    const usernameInput = $('<input type="text" id="externalDataUsername' + elemIndex + '" class="form-control no-break">');
                    usernameInput.on('input', function() {
                        externalDataEntry.username = usernameInput.val();
                    })
                    usernameInput.val(externalDataEntry.username);
                    externalDataSubSection.append(usernameInput);

                    externalDataSubSection.append('<br>');
                    externalDataSubSection.append('<label for="externalDataPassword' + elemIndex + '">Password: </label>');
                    const passwordInput = $('<input type="password" id="externalDataPassword' + elemIndex + '" class="form-control no-break">');
                    passwordInput.on('input', function() {
                        externalDataEntry.password = passwordInput.val();
                    })
                    passwordInput.val(externalDataEntry.password);
                    externalDataSubSection.append(passwordInput);
                }
            } else if (externalDataEntry.inputType === 'Directory') {
                const connectorTypeSelect = $('<select id="externalDataConnectorTypeSelect' + elemIndex + '">');
                for (const opt of [null, 'SSH']) {
                    let text = opt;
                    if (opt == null) text = '-';
                    const option = $('<option value="' + opt + '">' + text + '</option>');
                    option.prop('selected', externalDataEntry.connectorType === opt);
                    connectorTypeSelect.append(option);
                }
                connectorTypeSelect.on('input', function() {
                    let val = connectorTypeSelect.val();
                    if (val === 'null') {
                        val = null;
                    }
                    externalDataEntry.connectorType = val;
                    refreshExternalDataSubSection(externalDataSubSection, externalDataEntry, elemIndex);
                });
                externalDataSubSection.append(connectorTypeSelect);

                if (externalDataEntry.connectorType === 'SSH') {
                    externalDataSubSection.append('<br>');
                    externalDataSubSection.append('<label for="externalDataHost' + elemIndex + '">Host: </label>');
                    const hostInput = $('<input type="text" id="externalDataHost' + elemIndex + '" class="form-control no-break">');
                    hostInput.on('input', function() {
                        externalDataEntry.host = hostInput.val();
                    });
                    hostInput.val(externalDataEntry.host);
                    externalDataSubSection.append(hostInput);

                    externalDataSubSection.append('<br>');
                    externalDataSubSection.append('<label for="externalDataDirPath' + elemIndex + '">Directory path: </label>');
                    const dirPathInput = $('<input type="text" id="externalDataDirPath' + elemIndex + '" class="form-control no-break">');
                    dirPathInput.on('input', function() {
                        externalDataEntry.path = dirPathInput.val();
                    });
                    dirPathInput.val(externalDataEntry.path);
                    externalDataSubSection.append(dirPathInput);

                    externalDataSubSection.append('<br>');
                    externalDataSubSection.append('<label for="externalDataUsername' + elemIndex + '">Username: </label>');
                    const usernameInput = $('<input type="text" id="externalDataUsername' + elemIndex + '" class="form-control no-break">');
                    usernameInput.on('input', function() {
                        externalDataEntry.username = usernameInput.val();
                    });
                    usernameInput.val(externalDataEntry.username);
                    externalDataSubSection.append(usernameInput);

                    externalDataSubSection.append('<br>');
                    externalDataSubSection.append('<label for="externalDataPassword' + elemIndex + '">Password: </label>');
                    const passwordInput = $('<input type="password" id="externalDataPassword' + elemIndex + '" class="form-control no-break">');
                    passwordInput.on('input', function() {
                        externalDataEntry.password = passwordInput.val();
                    });
                    passwordInput.val(externalDataEntry.password);
                    externalDataSubSection.append(passwordInput);

                    externalDataSubSection.append('<br>');
                    const mountLabel = $('<label for="externalDataMount' + elemIndex + '"></label>');
                    externalDataSubSection.append(mountLabel);
                    const mountInput = $('<input type="checkbox" id="externalDataMount' + elemIndex + '" value="">');
                    mountInput.on('input', function() {
                        externalDataEntry.mount = mountInput.prop('checked');
                    });
                    mountInput.prop('checked', externalDataEntry.mount);
                    mountLabel.append(mountInput);
                    mountLabel.append('Mount')
                }
            }
        }

        for (const externalDataEntry of externalDataInfo) {
            const tmpIndex = index;
            const externalDataSubSection = $('<li class="list-group-item" id="externalDataSubSection' + tmpIndex + '">');
            refreshExternalDataSubSection(externalDataSubSection, externalDataEntry, tmpIndex);
            externalDataList.append(externalDataSubSection);
            index += 1;
        }

        if (externalDataInfo.length === 0) {
            externalDataList.append('<li class="list-group-item border-0 text-muted">No external data stated</li>');
        }
    }

    /**
     * Creates the html elements for the execution view and inserts them into the main div.
     */
    function showExecutionView() {
        const main = $('#main');

        clearView(main);
        setupAlertSection(main);
        setupNavbar(main, 'execution');

        // drop zone
        const dropZoneSection = $('<div id="dropZoneSection">');
        dropZoneSection.append('<h3>Jupyter Notebook</h3>');
        dropZoneSection.append('Drop notebook file here:');
        const dropZone = $('<div id="dropZone" style="width: 100px; height: 100px; background-color: lightgray"></div>');
        dropZoneSection.append(dropZone);

        const notebookList = $('<ul id="notebookList" class="list-group"> </ul>');
        refreshNotebookList(notebookList);
        dropZoneSection.append(notebookList);

        dropZone.on("dragover", function(event) {
            event.preventDefault();
            event.stopPropagation();
        });

        dropZone.on("dragleave", function(event) {
            event.preventDefault();
            event.stopPropagation();
        });

        dropZone.on('drop', ondropNotebookHandler, undefined, undefined);

        // dependencies
        const dependenciesSection = $('<div id="dependenciesSection">');
        dependenciesSection.append('<header> <h3>Dependencies</h3> </header>');

        const predefinedImagesRadio = $('<input type="radio" id="dependenciesPredefined" name="dependenciesRadio" value="predefined" class="form-check-input">')
        dependenciesSection.append(predefinedImagesRadio);
        dependenciesSection.append('<label for="dependenciesPredefined">Predefined Docker Images</label><br>');

        const predefinedImages = $('<select id="predefinedImages" class="form-control">');
        dependenciesSection.append(predefinedImages);

        const customImagesRadio = $('<input type="radio" id="dependenciesCustom" name="dependenciesRadio" value="custom" class="form-check-input">');
        dependenciesSection.append('<br>');
        dependenciesSection.append(customImagesRadio);
        dependenciesSection.append('<label for="dependenciesCustom">Custom Docker Image</label><br>');

        dependenciesSection.append('<label for="customDockerImage">Docker Image Tag:</label>');
        const customImage = $('<input type="text" id="customDockerImage" name="customDockerImage" class="form-control">');
        dependenciesSection.append(customImage);

        setupDependencies(predefinedImagesRadio, predefinedImages, customImagesRadio, customImage);

        // Hardware requirements
        const hardwareSection = $('<div id="hardwareSection">');

        hardwareSection.append('<h3>GPUs</h3>');
        const gpuList = $('<ul id="gpuList" class="list-group"></ul>');
        refreshGpuList(gpuList);
        hardwareSection.append(gpuList);
        const addGpuButton = $('<button id="addGpu" type="button" class="btn"><i class="fa fa-plus-square" style="transform: scale(1.6);"></i></button>');
        addGpuButton.click(function () {
            gpuRequirements.push(DEFAULT_GPU_VRAM);
            refreshGpuList($('#gpuList'));
        })
        hardwareSection.append(addGpuButton);

        // external data
        const externalDataSection = $('<div id="externalDataSection">');
        externalDataSection.append('<h3>External Data');
        const externalDataList = $('<ul id="externalDataList" class="list-group">');
        refreshExternalDataList(externalDataList);
        externalDataSection.append(externalDataList);
        const addExternalDataButton = $('<button id="addExternalData" type="button" class="btn"><i class="fa fa-plus-square" style="transform: scale(1.6);"></i></button>');
        addExternalDataButton.click(function() {
            externalDataInfo.push(new ExternalDataEntry());
            refreshExternalDataList($('#externalDataList'));
        })
        externalDataSection.append(addExternalDataButton);

        // submit button
        const submitButton = $('<button type="button" name="submitButton" id="submitButton" class="btn btn-outline-primary active">Execute</button>');

        submitButton.click(function() {
            if (jupyterNotebookEntries.length === 0) {
                addAlert('info', 'You have to upload at least one jupyter notebook to execute.');
                return;
            }

            let url = getUrl('executeNotebook');

            // noinspection JSIgnoredPromiseFromCall
            $.ajax({
                url,
                method: 'POST',
                dataType: 'json',
                contentType: 'application/json',
                data: JSON.stringify({
                    jupyterNotebooks: jupyterNotebookEntries,
                    dependencies: dependenciesSelection,
                    gpuRequirements,
                    externalData: externalDataInfo
                })
            }).fail(function (e, statusText, errorMessage) {
                addAlert('danger', 'Failed to execute the given notebook!');
                console.error(errorMessage, e.responseText);
            }).done(function(data, _statusText, _jqXHR) {
                showResultView();
            })

            jupyterNotebookEntries = [];
            refreshNotebookList($('#notebookList'))
        });

        const submain = $('<div id="submain" class="container-fluid-sm">');

        submain.append(dropZoneSection);
        submain.append(dependenciesSection);
        submain.append(hardwareSection);
        submain.append(externalDataSection);
        submain.append('<br>');
        submain.append(submitButton);
        main.append(submain);
    }

    function padZero(i) {
        const s = '' + i;
        if (s.length === 1) {
            return '0' + s;
        }
        return s;
    }

    function formatTimestamp(timestamp) {
        const date = new Date(timestamp * 1000);
        const now = new Date(Date.now());
        let timeStr = '' + padZero(date.getHours()) + ':' + padZero(date.getMinutes()) + ':' + padZero(date.getSeconds());
        if (date.getFullYear() !== now.getFullYear() || date.getMonth() !== now.getMonth() || date.getDate() !== now.getDate()) {
            timeStr = timeStr + '&nbsp;&nbsp;&nbsp;' + padZero(date.getDate()) + '-' + padZero((date.getMonth()+1)) + '-' + date.getFullYear();
        }
        return timeStr;
    }

    function addResultEntry(resultTable, notebookId, processStatus, notebookFilename, executionTime) {
        const row = $('<tr><td>' + notebookFilename + '</td><td>' + processStatus + '</td><td>' + formatTimestamp(executionTime) + '</td></tr>');

        // download button
        const downloadButton = $('<button class="btn btn-sm btn-outline-secondary"><i class="fa fa-download"></i></button>');
        downloadButton.click(function (_a) {
            window.open(getUrl('result/' + notebookId), '_blank');
        })
        downloadButton.prop('disabled', processStatus !== 'success');

        // cancel button
        const cancelButton = $('<button class="btn btn-sm btn-outline-secondary"><i class="fa fa-times-circle"></i></button>')
        cancelButton.click(function() {
            const url = getUrl('cancel_notebook')
            // noinspection JSIgnoredPromiseFromCall
            $.ajax({
                url,
                method: 'DELETE',
                dataType: 'json',
                contentType: 'application/json',
                data: JSON.stringify({'notebookId': notebookId})
            }).done(function (_data, _statusText, _jqXHR) {
                refreshResults();
            }).fail(function (_a, _b, e) {
                addAlert('danger', 'Failed to cancel the notebook execution');
                console.error('Failed to cancel notebook ', notebookId, '\nerror: ', e);
            });
        });
        cancelButton.prop('disabled', processStatus !== 'processing');
        const td = $('<td>');
        td.append(cancelButton);
        td.append(downloadButton);
        row.append(td);

        resultTable.append(row);
    }

    /**
     * Creates the html elements for the result view and inserts them into the main div.
     */
    function showResultView() {
        const main = $('#main');
        clearView(main);
        setupAlertSection(main);
        setupNavbar(main, 'results');

        // result section
        const resultSection = $('<div id="resultSection" class="text-center">')
        const resultTable = $('<table id="resultTable" class="table table-bordered table-hover table-sm">');
        clearResultTable(resultTable);
        resultSection.append(resultTable);

        main.append(resultSection);

        refreshResults();
    }

    function clearResultTable(resultTable) {
        resultTable.empty();
        resultTable.append('<tr><th>Name</th><th>Status</th><th>Time</th><th>Actions</th></tr>')
    }

    /**
     * Updates the result table entries by fetching the results
     */
    function refreshResults() {
        const resultTable = $('#resultTable');
        clearResultTable(resultTable);
        $('#resultSection').append('<div id="resultSpinner" class="spinner-border text-muted"></div>');
        let url = getUrl('list_results')
        // noinspection JSIgnoredPromiseFromCall
        $.ajax({
            url,
            method: 'GET',
            dataType: 'json',
        }).done(function (data, _statusText, _jqXHR) {
            const resultTable = $('#resultTable')
            clearResultTable(resultTable);
            for (let entry of data) {
                addResultEntry(resultTable, entry['notebook_id'], entry['process_status'], entry['notebook_filename'], entry['execution_time']);
            }
            $('#resultSpinner').remove();
        }).fail(function (_a, _b, e) {
            const resultTable = $('#resultTable')
            clearResultTable(resultTable);
            console.error('Failed to refresh job list: ', e);
            addAlert('danger', 'Failed to refresh the job list!');
            $('#resultSpinner').remove();
        });
    }

    /**
     * Creates the necessary elements in notebook list by the items of jupyterNotebookEntries.
     *
     * @param notebookList The jquery ul element that stores the notebook entries
     */
    function refreshNotebookList(notebookList) {
        notebookList.empty();
        let index = 0;
        for (const entry of jupyterNotebookEntries) {
            const tmpIndex = index;
            const li = $('<li class="list-group-item border-0">' + entry.filename + '</li>');
            const removeBtn = $('<button id="notebookRemove' + tmpIndex + '" type="button" class="close"><i class="fa fa-times-circle"></i></button>')
            removeBtn.click(function() {
                jupyterNotebookEntries.splice(tmpIndex, 1);
                refreshNotebookList($('#notebookList'));
            })
            li.append(removeBtn);

            notebookList.append(li);
        }
    }

    /**
     * Callback for Notebook drop. This function loads all dropped jupyter notebooks and
     * appends it to the notebookList.
     *
     * @param event The drop event
     */
    function ondropNotebookHandler(event) {
        event.stopPropagation();
        event.preventDefault();
        const notebookList = $('#notebookList');

        for (const file of event.originalEvent.dataTransfer.files) {
            const reader = new FileReader();
            reader.onload = function(ev) {
                let json = null;
                try {
                    // noinspection JSIgnoredPromiseFromCall
                    const res = ev.target.result.toString();
                    json = JSON.parse(res);
                } catch (error) {
                    addAlert('danger', 'Failed to decode the notebook!');
                    console.error('Error while decoding notebook.' + error + '\ncontent was: ' + ev.target.result);
                    return;
                }
                jupyterNotebookEntries.push(new NotebookEntry(json, file.name));
                refreshNotebookList(notebookList);
            };
            reader.readAsText(file);
        }
    }

    showExecutionView();
});

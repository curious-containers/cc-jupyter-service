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

    let jupyterNotebookEntries = [];
    const dependenciesSelection = {
        custom: false,
        predefinedImage: 'Base Image',
        customImage: ''
    }
    let globalPredefinedImages = [];
    let gpuRequirements = [];

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
        predefinedImages.append()

        customImages.val(dependenciesSelection.customImage);

        // setup callbacks
        predefinedImagesRadio.click(function() {
            dependenciesSelection.custom = false;
            predefinedImages.prop('disabled', false);
            customImages.prop('disabled', true);
        })
        predefinedImages.change(function() {
            dependenciesSelection.predefinedImage = predefinedImages.val();
        })
        customImagesRadio.click(function() {
            dependenciesSelection.custom = true;
            predefinedImages.prop('disabled', true);
            customImages.prop('disabled', false);
        })
        customImages.keyup(function() {
            dependenciesSelection.customImage = customImages.val();
        })
    }

    function refreshGpuList(gpuList) {
        gpuList.empty();
        let index = 0;
        for (const gpuRequirement of gpuRequirements) {
            const tmpIndex = index;
            const gpuVram = $('<input id="gpuVram' + tmpIndex + '" type="number" value="' + gpuRequirement + '" step="1024">');
            gpuVram.change(function() {
                gpuRequirements[tmpIndex] = parseInt(gpuVram.val().toString());
            })
            const li = $('<li class="list-group-item"><label for="gpuVram' + tmpIndex + '" class="label">VRAM</label></li>');
            li.append(gpuVram);

            const removeBtn = $('<button id="gpuRemove' + tmpIndex + '" type="button" class="close closeGpu">&times</button>');
            removeBtn.click(function() {
                gpuRequirements.splice(tmpIndex, 1);
                refreshGpuList($('#gpuList'));
            })
            li.append(removeBtn);
            gpuList.append(li);
            index += 1;
        }
    }

    function addAlert(alertType, text) {
        const alertSection = $('#alertSection');
        const alert = $('<div class="alert alert-' + alertType + ' alert-dismissible"></div>');
        alert.append('<button type="button" class="close" data-dismiss="alert">&times</button>');
        alert.append(text);
        alertSection.append(alert);
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
        // hardwareSection.append('<header> <h3>Hardware</h3></header>');

        hardwareSection.append('<h4>GPUs</h4>');
        const gpuList = $('<ul id="gpuList" class="list-group"></ul>');
        refreshGpuList(gpuList);
        hardwareSection.append(gpuList);
        const addGpuButton = $('<button id="addGpu" type="button" class="btn btn-outline-secondary btn-sm">+</button>');
        addGpuButton.click(function () {
            gpuRequirements.push(DEFAULT_GPU_VRAM);
            refreshGpuList($('#gpuList'));
        })
        hardwareSection.append(addGpuButton);

        // submit button
        const submitButton = $('<button type="button" name="submitButton" id="submitButton" class="btn btn-outline-primary">Execute</button>');

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
                    gpuRequirements
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
        submain.append('<br>');
        submain.append(submitButton);
        main.append(submain);
    }

    function formatTimestamp(timestamp) {
        const date = new Date(timestamp * 1000);
        const now = new Date(Date.now());
        let timeStr = '' + date.getHours() + ':' + date.getMinutes() + ':' + date.getSeconds();
        if (date.getFullYear() !== now.getFullYear() || date.getMonth() !== now.getMonth() || date.getDate() !== now.getDate()) {
            timeStr = '' + date.getFullYear() + '-' + (date.getMonth()+1) + '-' + date.getDate() + ' ' + timeStr;
        }
        return timeStr;
    }

    function addResultEntry(resultTable, notebookId, processStatus, notebookFilename, executionTime) {
        const row = $('<tr><td>' + notebookFilename + '</td><td>' + processStatus + '</td><td>' + formatTimestamp(executionTime) + '</td></tr>');
        const downloadButton = $('<button class="btn btn-sm btn-outline-secondary">download</button>');
        downloadButton.click(function (_a) {
            window.open(getUrl('result/' + notebookId), '_blank');
        })
        downloadButton.prop('disabled', processStatus !== 'success');
        const td = $('<td>');
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
        resultTable.append('<tr><th>Name</th><th>Status</th><th>Time</th><th>Result</th></tr>')
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
            const removeBtn = $('<button id="notebookRemove' + tmpIndex + '" type="button" class="close">&times</button>')
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

$(document).ready(function() {
    class NotebookEntry {
        data;
        filename;

        constructor(data, filename) {
            this.data = data;
            this.filename = filename;
        }
    }

    const jupyterNotebookEntries = [];
    const dependenciesSelection = {
        custom: false,
        predefinedImage: 'Base Image',
        customImage: ''
    }
    let globalPredefinedImages = [];

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
            showError(e.responseText)
        }).done(function (d) {
            globalPredefinedImages = d;
            setupDependencies($('#dependenciesPredefined'), $('#predefinedImages'), $('#dependenciesCustom'), $('#customDockerImage'));
        });
    }

    updatePredefinedDockerImages();

    /**
     * Setup the click events for the navigation bar
     */
    function setupNavbar() {
        $('#ExecutionNavbar').click(showExecutionView);
        $('#ResultNavbar').click(showResultView);
    }

    /**
     * Removes all elements from the main view
     */
    function clearView() {
        let main = $('#main');
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

    /**
     * Creates the html elements for the execution view and inserts them into the main div.
     */
    function showExecutionView() {
        clearView();

        // drop zone
        const dropZone = $('<div id="dropZone">');
        dropZone.append('<header> <h1>Jupyter Notebook</h1> </header>');
        dropZone.append('<div id="dropZone" style="width: 100px; height: 100px; background-color: lightgray"></div>');

        const notebookList = $('<ul id="notebookList"> </ul>');
        refreshNotebookList(notebookList);
        dropZone.append(notebookList);

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
        dependenciesSection.append('<header> <h1>Dependencies</h1> </header>');

        const predefinedImagesRadio = $('<input type="radio" id="dependenciesPredefined" name="dependenciesRadio" value="predefined">')
        dependenciesSection.append(predefinedImagesRadio);
        dependenciesSection.append('<label for="dependenciesPredefined">Predefined Docker Images</label><br>');

        const predefinedImages = $('<select id="predefinedImages">');
        dependenciesSection.append(predefinedImages);

        const customImagesRadio = $('<input type="radio" id="dependenciesCustom" name="dependenciesRadio" value="custom">');
        dependenciesSection.append('<br>');
        dependenciesSection.append(customImagesRadio);
        dependenciesSection.append('<label for="dependenciesCustom">Custom Docker Image</label><br>');

        dependenciesSection.append('<label for="customDockerImage">Docker Image Tag:</label>');
        const customImages = $('<input type="text" id="customDockerImage" name="customDockerImage">');
        dependenciesSection.append(customImages);

        setupDependencies(predefinedImagesRadio, predefinedImages, customImagesRadio, customImages);

        // submit button
        const submitButton = $('<input type="button" name="submitButton" id="submitButton" value="Execute">');

        submitButton.click(function() {
            if (jupyterNotebookEntries.length === 0) {
                showError('Upload at least one jupyter notebook');
                return;
            }

            let url = getUrl('executeNotebook');

            const dependencies = {
                dockerImage: $('#dockerImage').val()
            }
            // noinspection JSIgnoredPromiseFromCall
            $.ajax({
                url,
                method: 'POST',
                dataType: 'json',
                contentType: 'application/json',
                data: JSON.stringify({
                    jupyterNotebooks: jupyterNotebookEntries,
                    dependencies
                })
            }).fail(function (e, statusText, errorMessage) {
                console.error(errorMessage, e.responseText);
                showError(e.responseText)
            })
        });

        const main = $('#main');
        main.append(dropZone);
        main.append(dependenciesSection);
        main.append('<br>');
        main.append(submitButton);
    }

    function addResultEntry(notebookId, processStatus) {
        const resultTable = $('#resultTable');
        let row = $('<tr><td>' + notebookId + '</td><td>' + processStatus + '</td><td></td></tr>');
        let downloadButton = $('<button>download</button>');
        downloadButton.click(function (_a) {
            window.open(getUrl('result/' + notebookId), '_blank');
        })
        row.append(downloadButton);

        resultTable.append(row);
    }

    /**
     * Creates the html elements for the result view and inserts them into the main div.
     */
    function showResultView() {
        clearView();

        // result table
        let resultTable = $('<table id="resultTable" style="width:600px">');
        resultTable.append('<tr><th>Notebook ID</th><th>Status</th><th>Result</th></tr>')

        const main = $('#main');
        main.append(resultTable);

        refreshResults();
    }

    /**
     * Updates the result table entries by fetching the results
     */
    function refreshResults() {
        let url = getUrl('list_results')
        // noinspection JSIgnoredPromiseFromCall
        $.ajax({
            url,
            method: 'GET',
            dataType: 'json',
        }).done(function (data, _statusText, _jqXHR) {
            for (let entry of data) {
                addResultEntry(entry['notebook_id'], entry['process_status']);
            }
        }).fail(function (a, b, c) {
            console.error('Failed to refresh job list');
        });
    }

    /**
     * Displays an error message to the user.
     *
     * @param errorMessage The message to show
     */
    function showError(errorMessage) {
        $('#messages').append('<div class="flash">' + errorMessage + '</div>');
    }

    /**
     * Creates the necessary elements in notebook list by the items of jupyterNotebookEntries.
     *
     * @param notebookList The jquery ul element that stores the notebook entries
     */
    function refreshNotebookList(notebookList) {
        notebookList.empty();
        for (const entry of jupyterNotebookEntries) {
            notebookList.append('<li>' + entry.filename + '</li>');
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
                    console.error('Error while decoding notebook.' + error + '\ncontent was: ' + ev.target.result);
                    showError('Error while decoding notebook. ' + error);
                    return;
                }
                jupyterNotebookEntries.push(new NotebookEntry(json, file.name));
                refreshNotebookList(notebookList);
            };
            reader.readAsText(file);
        }
    }

    setupNavbar();

    showExecutionView();
});

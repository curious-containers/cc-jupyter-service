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
     * Creates the html elements for the execution view and inserts them into the main div.
     */
    function showExecutionView() {
        clearView();

        // drop zone
        const dropZone = $('<div id="dropZone">');
        dropZone.append('<header> <h1>Jupyter Notebook</h1> </header>');
        dropZone.append('<div id="dropZone" style="width: 100px; height: 100px; background-color: lightgray"></div>');
        dropZone.append('<ul id="notebookList"> </ul>');

        dropZone.on("dragover", function(event) {
            event.preventDefault();
            event.stopPropagation();
        });

        dropZone.on("dragleave", function(event) {
            event.preventDefault();
            event.stopPropagation();
        });

        dropZone.on('drop', ondropNotebookHandler);

        // dependencies
        const dependenciesSection = $('<div id="dependenciesSection">');
        dependenciesSection.append('<header> <h1>Dependencies</h1> </header>');
        dependenciesSection.append('<input type="checkbox" name="cudaRequired" id="cudaRequired" checked="checked">');
        dependenciesSection.append('<label for="cudaRequired">CUDA</label><br>');
        dependenciesSection.append('<input type="checkbox" name="tensorflowRequired" id="tensorflowRequired" checked="checked">');
        dependenciesSection.append('<label for="tensorflowRequired">Tensorflow</label>');

        // submit button
        const submitButton = $('<input type="button" name="submitButton" id="submitButton" value="Execute">')

        submitButton.click(function() {
            if (jupyterNotebookEntries.length === 0) {
                showError('Upload at least one jupyter notebook');
                return;
            }

            // noinspection JSIgnoredPromiseFromCall
            let url = getUrl('executeNotebook');
            $.ajax({
                url,
                method: 'POST',
                dataType: 'json',
                contentType: 'application/json',
                data: JSON.stringify({
                    jupyterNotebooks: jupyterNotebookEntries,
                    dependencies: []  // TODO: dependencies
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
        downloadButton.click(function (a) {
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
        $.ajax({
            url,
            method: 'GET',
            dataType: 'json',
        }).done(function (data, statusText, jqXHR) {
            for (let entry of data) {
                addResultEntry(entry['notebook_id'], entry['process_status']);
            }
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
                    json = JSON.parse(ev.target.result);
                } catch (error) {
                    console.error('Error while decoding notebook.' + error + '\ncontent was: ' + ev.target.result);
                    showError('Error while decoding notebook. ' + error);
                    return;
                }
                jupyterNotebookEntries.push(new NotebookEntry(json, file.name));
                notebookList.append('<li>' + file.name + '</li>');
            };
            reader.readAsText(file);
        }
    }

    setupNavbar();

    showExecutionView();
    // showResultView();
});

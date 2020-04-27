$(document).ready(function() {
    /**
     * Removes all elements from the main view
     */
    function clearView() {
        let main = $('#main');
        main.empty();
    }

    /**
     * Creates the html elements for the execution view and inserts them into the main div.
     */
    function showExecutionView() {
        clearView();

        const main = $('#main');

        // drop zone
        const dropZoneSection = $('<div id="dropZoneSection">');
        main.append(dropZoneSection);
        dropZoneSection.append('<header> <h1>Jupyter Notebook</h1> </header>');
        dropZoneSection.append('<div id="dropZone" style="width: 100px; height: 100px; background-color: lightgray"></div>');
        dropZoneSection.append('<ul id="notebookList"> </ul>');

        // agency
        const agencySection = $('<div id="agencySection">');
        main.append(agencySection);
        agencySection.append('<header> <h1>Agency Authentication</h1> </header>');
        agencySection.append('<label for="agencyUrl">URL</label><br>');
        agencySection.append('<input name="agencyUrl" id="agencyUrl"><br>');
        agencySection.append('<label for="agencyUsername">Username</label><br>');
        agencySection.append('<input name="agencyUsername" id="agencyUsername"><br>');
        agencySection.append('<label for="agencyPassword">Password</label><br>');
        agencySection.append('<input type="password" name="agencyPassword" id="agencyPassword">');

        // dependencies
        const dependenciesSection = $('<div id="dependenciesSection">');
        main.append(dependenciesSection);
        dependenciesSection.append('<header> <h1>Dependencies</h1> </header>');
        dependenciesSection.append('<input type="checkbox" name="cudaRequired" id="cudaRequired" checked="checked">');
        dependenciesSection.append('<label for="cudaRequired">CUDA</label><br>');
        dependenciesSection.append('<input type="checkbox" name="tensorflowRequired" id="tensorflowRequired" checked="checked">');
        dependenciesSection.append('<label for="tensorflowRequired">Tensorflow</label>');

        // submit button
        main.append('<br>');
        main.append('<input type="button" name="submitButton" id="submitButton" value="Execute">');
    }

    function addResultEntry(notebook_id, process_status) {
        const resultTable = $('#resultTable');
        resultTable.append('<tr><td>' + notebook_id + '</td><td>' + process_status + '</td><td><button>download</button></td></tr>')
    }

    /**
     * Creates the html elements for the result view and inserts them into the main div.
     */
    function showResultView() {
        clearView();

        const main = $('#main');

        // result table
        let resultTable = $('<table id="resultTable" style="width:600px">');
        main.append(resultTable);
        resultTable.append('<tr><th>notebook id</th><th>process status</th><th>download</th></tr>')
    }

    /**
     * Displays an error message to the user.
     *
     * @param errorMessage The message to show
     */
    function showError(errorMessage) {
        $('#messages').append('<div class="flash">' + errorMessage + '</div>');
    }

    const jupyterNotebooks = [];

    /**
     * Creates a new NotebookEntry.
     *
     * @param notebookData The json data of the notebook
     * @param filename The notebook filename
     */
    function createNotebookEntry(notebookData, filename) {
        return {
            'data': notebookData,
            'filename': filename
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
                    json = JSON.parse(ev.target.result);
                } catch (error) {
                    console.error('Error while decoding notebook.' + error + '\ncontent was: ' + ev.target.result);
                    showError('Error while decoding notebook. ' + error);
                    return;
                }
                jupyterNotebooks.push(createNotebookEntry(json, file.name));
                notebookList.append('<li>' + file.name + '</li>');
            };
            reader.readAsText(file);
        }
    }

    const dropZone = $('#dropZone');

    dropZone.on("dragover", function(event) {
        event.preventDefault();
        event.stopPropagation();
    });

    dropZone.on("dragleave", function(event) {
        event.preventDefault();
        event.stopPropagation();
    });

    dropZone.on('drop', ondropNotebookHandler);

    $("#submitButton").click(function() {
        const agencyUrl = $('#agencyUrl').val();
        const agencyUsername = $('#agencyUsername').val();
        const agencyPassword = $('#agencyPassword').val();

        if (agencyUrl === '') {
            showError('Agency URL is required');
            return;
        }
        if (agencyUsername === '') {
            showError('Agency Username is required');
            return;
        }
        if (agencyPassword === '') {
            showError('Agency Password is required');
            return;
        }

        if (jupyterNotebooks.length === 0) {
            showError('Upload at least one jupyter notebook');
            return;
        }

        // noinspection JSIgnoredPromiseFromCall
        let url = window.location.href;
        if (!url.endsWith('/')) {
            url = url + '/'
        }
        url = new URL('executeNotebook', url).href;
        $.ajax({
            url,
            method: 'POST',
            dataType: 'json',
            contentType: 'application/json',
            data: JSON.stringify({
                agencyUrl,
                agencyUsername,
                agencyPassword,
                jupyterNotebooks,
                dependencies: []  // TODO: dependencies
            })
        }).done(function(data) {
            console.log('success');
            console.log(data);
        }).fail(function (e, statusText, errorMessage) {
            console.error(errorMessage, e.responseText);
            showError(e.responseText)
        })
    });

    showExecutionView();
    // showResultView();
});

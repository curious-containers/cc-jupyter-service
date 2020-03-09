$(document).ready(function() {
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
        $.ajax({
            url: '/executeNotebook',
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
});

$(document).ready(function() {
    $("#submit_button").click(function() {
        console.log('button pressed');
    });
});

function allowDrop(ev) {
    ev.preventDefault();
}

/**
 * Callback for Notebook drop. This function loads all dropped jupyter notebooks and
 * appends it to the notebookList.
 *
 * @param event The drop event
 */
function dropNotebook(event) {
    event.stopPropagation();
    event.preventDefault();
    const notebookList = $('#notebookList');
    let reader = new FileReader();

    reader.onload = function(e) {
        const [, content ] = e.target.result.split(',');
        // TODO: assert contentType == json
        // console.log('decoded content: ', JSON.parse(atob(content)));
        notebookList.append('new file');
    };
    for (const file of event.dataTransfer.files) {
        reader.readAsDataURL(file);
    }
}

function onBlockLoad () {

    globalThis.createModal = () => {
        // Create modal for the 1st time if it does not exist
        var modal = document.createElement("div");
        modal.id = "pdf-modal";
        modal.className = "modal";
        modal.innerHTML = `
            <div class="modal-content">
              <div class="modal-header">
                <span class="close">&times;</span>
              </div>
              <div class="modal-body">
                <pdfjs-viewer-element id="pdf-viewer" viewer-path="/file=PDFJS_PREBUILT_DIR" locale="en">
                </pdfjs-viewer-element>
              </div>
            </div>
          `;
        document.body.appendChild(modal);

        modal.querySelector(".close").onclick = function() {
            modal.style.display = "none";
        };
    }

    // Function to open modal and display PDF
    globalThis.openModal = (event) => {
      event.preventDefault();
      var target = event.currentTarget;
      var src = target.getAttribute("data-src");
      var page = target.getAttribute("data-page");
      var search = target.getAttribute("data-search");

      var pdfViewer = document.getElementById("pdf-viewer");
      pdfViewer.setAttribute("src", src);
      pdfViewer.setAttribute("page", page);
      pdfViewer.setAttribute("search", search);

      var modal = document.getElementById("pdf-modal")
      modal.style.display = "block";
    }

    globalThis.assignPdfOnclickEvent = () => {
        // Get all links and attach click event
        var links = document.getElementsByClassName("pdf-link");
        for (var i = 0; i < links.length; i++) {
            links[i].onclick = openModal;
        }
    }

    var created_modal = document.getElementById("pdf-modal");
    if (!created_modal) {
        createModal();
        console.log("Created modal")
    }

}

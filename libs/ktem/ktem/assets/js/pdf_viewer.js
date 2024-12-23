function onBlockLoad () {
    var infor_panel_scroll_pos = 0;
    globalThis.createModal = () => {
        // Create modal for the 1st time if it does not exist
        var modal = document.getElementById("pdf-modal");
        var old_position = null;
        var old_width = null;
        var old_left = null;
        var expanded = false;

        modal.id = "pdf-modal";
        modal.className = "modal";
        modal.innerHTML = `
            <div class="modal-content">
              <div class="modal-header">
                <span class="close" id="modal-close">&times;</span>
                <span class="close" id="modal-expand">&#x26F6;</span>
              </div>
              <div class="modal-body">
                <pdfjs-viewer-element id="pdf-viewer" viewer-path="GR_FILE_ROOT_PATH/file=PDFJS_PREBUILT_DIR" locale="en" phrase="true">
                </pdfjs-viewer-element>
              </div>
            </div>
          `;

        modal.querySelector("#modal-close").onclick = function() {
          modal.style.display = "none";
          var info_panel = document.getElementById("html-info-panel");
          if (info_panel) {
            info_panel.style.display = "block";
          }
          var scrollableDiv = document.getElementById("chat-info-panel");
          scrollableDiv.scrollTop = infor_panel_scroll_pos;
        };

        modal.querySelector("#modal-expand").onclick = function () {
          expanded = !expanded;
          if (expanded) {
            old_position = modal.style.position;
            old_left = modal.style.left;
            old_width = modal.style.width;

            modal.style.position = "fixed";
            modal.style.width = "70%";
            modal.style.left = "15%";
            modal.style.height = "100dvh";
          } else {
            modal.style.position = old_position;
            modal.style.width = old_width;
            modal.style.left = old_left;
            modal.style.height = "85dvh";
          }
        };
    }

    globalThis.compareText = (search_phrase, page_label) => {
      var iframe = document.querySelector("#pdf-viewer").iframe;
      var innerDoc = (iframe.contentDocument) ? iframe.contentDocument : iframe.contentWindow.document;

      var query_selector = (
        "#viewer > div[data-page-number='" +
        page_label +
        "'] > div.textLayer > span"
      );
      var page_spans = innerDoc.querySelectorAll(query_selector);
      for (var i = 0; i < page_spans.length; i++) {
        var span = page_spans[i];
        if (
          span.textContent.length > 4 &&
          (
            search_phrase.includes(span.textContent) ||
            span.textContent.includes(search_phrase)
          )
        ) {
          span.innerHTML = "<span class='highlight selected'>" + span.textContent + "</span>";
        } else {
          // if span is already highlighted, remove it
          if (span.querySelector(".highlight")) {
            span.innerHTML = span.textContent;
          }
        }
      }
    }

    // Sleep function using Promise and setTimeout
    function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // Function to open modal and display PDF
    globalThis.openModal = async (event) => {
      event.preventDefault();
      var target = event.currentTarget;
      var src = target.getAttribute("data-src");
      var page = target.getAttribute("data-page");
      var search = target.getAttribute("data-search");
      var phrase = target.getAttribute("data-phrase");

      var pdfViewer = document.getElementById("pdf-viewer");

      current_src = pdfViewer.getAttribute("src");
      if (current_src != src) {
        pdfViewer.setAttribute("src", src);
      }
      // pdfViewer.setAttribute("phrase", phrase);
      // pdfViewer.setAttribute("search", search);
      pdfViewer.setAttribute("page", page);

      var scrollableDiv = document.getElementById("chat-info-panel");
      infor_panel_scroll_pos = scrollableDiv.scrollTop;

      var modal = document.getElementById("pdf-modal")
      modal.style.display = "block";
      var info_panel = document.getElementById("html-info-panel");
      if (info_panel) {
        info_panel.style.display = "none";
      }
      scrollableDiv.scrollTop = 0;

      /* search for text inside PDF page */
      await sleep(500);
      compareText(search, page);
    }

    globalThis.assignPdfOnclickEvent = () => {
        // Get all links and attach click event
        var links = document.getElementsByClassName("pdf-link");
        for (var i = 0; i < links.length; i++) {
            links[i].onclick = openModal;
        }
    }

    var created_modal = document.getElementById("pdf-viewer");
    if (!created_modal) {
        createModal();
    }

}

function run() {
  let answerPanelObserver = null;
  let previewSrcPoller = null;
  let lastPreviewSrc = null;

  function enforceAnswerPanelScroll() {
    let answerPanel = document.getElementById("answer-panel");
    let answerExpand = document.getElementById("answer-expand");
    if (!answerPanel || !answerExpand) {
      return;
    }

    answerExpand.style.overflow = "hidden";
    answerExpand.style.minHeight = "0";

    let node = answerPanel.parentElement;
    while (node && node !== answerExpand) {
      node.style.minHeight = "0";
      node.style.height = "100%";
      node.style.maxHeight = "100%";
      node.style.overflow = "hidden";
      node = node.parentElement;
    }

    answerPanel.style.minHeight = "0";
    answerPanel.style.height = "100%";
    answerPanel.style.maxHeight = "100%";
    answerPanel.style.overflowX = "hidden";
    answerPanel.style.overflowY = "auto";
  }

  function syncMainPdfPreview() {
    let srcField = document.querySelector("#main-pdf-preview-src textarea, #main-pdf-preview-src input");
    let iframe = document.getElementById("main-pdf-preview-frame");
    let image = document.getElementById("main-pdf-preview-image");
    let empty = document.getElementById("main-pdf-preview-empty");
    if (!srcField || !iframe || !image || !empty) {
      return;
    }

    let nextSrc = (srcField.value || "").trim();
    if (nextSrc === lastPreviewSrc) {
      return;
    }
    lastPreviewSrc = nextSrc;

    if (!nextSrc) {
      iframe.style.display = "none";
      image.style.display = "none";
      empty.style.display = "flex";
      iframe.removeAttribute("src");
      image.removeAttribute("src");
      return;
    }

    const isImage = nextSrc.startsWith("data:image") || /\.(png|jpg|jpeg|gif|webp|svg)(\?|#|$)/i.test(nextSrc);
    if (isImage) {
      iframe.style.display = "none";
      empty.style.display = "none";
      image.style.display = "block";
      image.src = nextSrc;
      return;
    }

    image.style.display = "none";
    empty.style.display = "none";
    iframe.style.display = "block";

    const getViewerDocumentKey = (src) => {
      try {
        let url = new URL(src, window.location.origin);
        url.hash = "";
        url.searchParams.delete("ktempage");
        return `${url.origin}${url.pathname}?${url.searchParams.toString()}`;
      } catch (error) {
        return src.split("#")[0].replace(/([?&])ktempage=\d+(&?)/, "$1").replace(/[?&]$/, "");
      }
    };

    const getTargetPage = (src) => {
      try {
        let url = new URL(src, window.location.origin);
        let queryPage = parseInt(url.searchParams.get("ktempage") || "", 10);
        if (Number.isFinite(queryPage) && queryPage > 0) {
          return queryPage;
        }
        let hashParams = new URLSearchParams(url.hash.replace(/^#/, ""));
        let hashPage = parseInt(hashParams.get("page") || "", 10);
        return Number.isFinite(hashPage) && hashPage > 0 ? hashPage : 1;
      } catch (error) {
        return 1;
      }
    };

    let currentSrc = iframe.getAttribute("src") || "";
    let currentBase = getViewerDocumentKey(currentSrc);
    let nextBase = getViewerDocumentKey(nextSrc);
    if (currentSrc && currentBase === nextBase && iframe.contentWindow) {
      try {
        iframe.contentWindow.postMessage({
          type: "ktem-pdf-page-change",
          page: getTargetPage(nextSrc),
        }, window.location.origin);
        return;
      } catch (error) {
        console.error("Failed to update preview page in place", error);
      }
    }

    iframe.src = nextSrc;
  }

  let main_parent = document.getElementById("chat-tab").parentNode;

  main_parent.childNodes[0].classList.add("header-bar");
  main_parent.style = "padding: 0; margin: 0";
  main_parent.parentNode.style = "gap: 0";
  main_parent.parentNode.parentNode.style = "padding: 0";

  const version_node = document.createElement("p");
  version_node.innerHTML = "version: KH_APP_VERSION";
  version_node.style = "position: fixed; top: 10px; right: 10px;";
  main_parent.appendChild(version_node);

  // add favicon
  const favicon = document.createElement("link");
  // set favicon attributes
  favicon.rel = "icon";
  favicon.type = "image/svg+xml";
  favicon.href = "/favicon.ico";
  document.head.appendChild(favicon);

  // setup conversation dropdown placeholder
  let conv_dropdown = document.querySelector("#conversation-dropdown input");
  conv_dropdown.placeholder = "Browse conversation";

  // move info-expand-button
  let info_expand_button = document.getElementById("info-expand-button");
  let chat_info_panel = document.getElementById("info-expand");
  chat_info_panel.insertBefore(
    info_expand_button,
    chat_info_panel.childNodes[2]
  );

  // move toggle-side-bar button
  let chat_expand_button = document.getElementById("chat-expand-button");
  let chat_column = document.getElementById("chat-area");
  let conv_column = document.getElementById("conv-settings-panel");

  // move setting close button
  let setting_tab_nav_bar = document.querySelector("#settings-tab .tab-nav");
  let setting_close_button = document.getElementById("save-setting-btn");
  if (setting_close_button) {
    setting_tab_nav_bar.appendChild(setting_close_button);
  }

  let default_conv_column_min_width = "min(300px, 100%)";
  conv_column.style.minWidth = default_conv_column_min_width;

  globalThis.toggleChatColumn = () => {
    /* get flex-grow value of chat_column */
    let flex_grow = conv_column.style.flexGrow;
    if (flex_grow == "0") {
      conv_column.style.flexGrow = "1";
      conv_column.style.minWidth = default_conv_column_min_width;
    } else {
      conv_column.style.flexGrow = "0";
      conv_column.style.minWidth = "0px";
    }
  };

  if (chat_column && chat_expand_button) {
    chat_expand_button.style.flexGrow = "0";
    chat_expand_button.style.width = "36px";
    chat_expand_button.style.minWidth = "36px";
    chat_expand_button.style.height = "36px";
    chat_expand_button.style.padding = "0";
    chat_column.insertBefore(chat_expand_button, chat_column.firstChild);
  }

  // move share conv checkbox
  let report_div = document.querySelector(
    "#report-accordion > div:nth-child(3) > div:nth-child(1)"
  );
  let share_conv_checkbox = document.getElementById("is-public-checkbox");
  if (share_conv_checkbox) {
    report_div.insertBefore(share_conv_checkbox, report_div.querySelector("button"));
  }

  // create slider toggle
  const is_public_checkbox = document.getElementById("suggest-chat-checkbox");
  const label_element = is_public_checkbox.getElementsByTagName("label")[0];
  const checkbox_span = is_public_checkbox.getElementsByTagName("span")[0];
  new_div = document.createElement("div");

  label_element.classList.add("switch");
  is_public_checkbox.appendChild(checkbox_span);
  label_element.appendChild(new_div);

  // clpse
  globalThis.clpseFn = (id) => {
    var obj = document.getElementById("clpse-btn-" + id);
    obj.classList.toggle("clpse-active");
    var content = obj.nextElementSibling;
    if (content.style.display === "none") {
      content.style.display = "block";
    } else {
      content.style.display = "none";
    }
  };

  // store info in local storage
  globalThis.setStorage = (key, value) => {
    localStorage.setItem(key, value);
  };
  globalThis.getStorage = (key, value) => {
    item = localStorage.getItem(key);
    return item ? item : value;
  };
  globalThis.removeFromStorage = (key) => {
    localStorage.removeItem(key);
  };

  // Function to scroll to given citation with ID
  // Sleep function using Promise and setTimeout
  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  globalThis.scrollToCitation = async (event) => {
    event.preventDefault(); // Prevent the default link behavior
    var citationId = event.target.getAttribute("id");

    await sleep(100); // Sleep for 100 milliseconds

    // check if modal is open
    var modal = document.getElementById("pdf-modal");
    var citation = document.querySelector('mark[id="' + citationId + '"]');

    if (modal.style.display == "block") {
      // trigger on click event of PDF Preview link
      var detail_elem = citation;
      // traverse up the DOM tree to find the parent element with tag detail
      while (detail_elem.tagName.toLowerCase() != "details") {
        detail_elem = detail_elem.parentElement;
      }
      detail_elem.getElementsByClassName("pdf-link").item(0).click();
    } else {
      if (citation) {
        citation.scrollIntoView({ behavior: "smooth" });
      }
    }
  };

  globalThis.fullTextSearch = () => {
    // Assign text selection event to last bot message
    var bot_messages = document.querySelectorAll(
      "div#main-chat-bot div.message-row.bot-row"
    );
    var last_bot_message = bot_messages[bot_messages.length - 1];

    // check if the last bot message has class "text_selection"
    if (last_bot_message.classList.contains("text_selection")) {
      return;
    }

    // assign new class to last message
    last_bot_message.classList.add("text_selection");

    // Get sentences from evidence div
    var evidences = document.querySelectorAll(
      "#html-info-panel > div:last-child > div > details.evidence div.evidence-content"
    );
    console.log("Indexing evidences", evidences);

    const segmenterEn = new Intl.Segmenter("en", { granularity: "sentence" });
    // Split sentences and save to all_segments list
    var all_segments = [];
    for (var evidence of evidences) {
      // check if <details> tag is open
      if (!evidence.parentElement.open) {
        continue;
      }
      var markmap_div = evidence.querySelector("div.markmap");
      if (markmap_div) {
        continue;
      }

      var evidence_content = evidence.textContent.replace(/[\r\n]+/g, " ");
      sentence_it = segmenterEn.segment(evidence_content)[Symbol.iterator]();
      while ((sentence = sentence_it.next().value)) {
        segment = sentence.segment.trim();
        if (segment) {
          all_segments.push({
            id: all_segments.length,
            text: segment,
          });
        }
      }
    }

    let miniSearch = new MiniSearch({
      fields: ["text"], // fields to index for full-text search
      storeFields: ["text"],
    });

    // Index all documents
    miniSearch.addAll(all_segments);

    last_bot_message.addEventListener("mouseup", () => {
      let selection = window.getSelection().toString();
      let results = miniSearch.search(selection);

      if (results.length == 0) {
        return;
      }
      let matched_text = results[0].text;
      console.log("query\n", selection, "\nmatched text\n", matched_text);

      var evidences = document.querySelectorAll(
        "#html-info-panel > div:last-child > div > details.evidence div.evidence-content"
      );
      // check if modal is open
      var modal = document.getElementById("pdf-modal");

      // convert all <mark> in evidences to normal text
      evidences.forEach((evidence) => {
        evidence.querySelectorAll("mark").forEach((mark) => {
          mark.outerHTML = mark.innerText;
        });
      });

      // highlight matched_text in evidences
      for (var evidence of evidences) {
        var evidence_content = evidence.textContent.replace(/[\r\n]+/g, " ");
        if (evidence_content.includes(matched_text)) {
          // select all p and li elements
          paragraphs = evidence.querySelectorAll("p, li");
          for (var p of paragraphs) {
            var p_content = p.textContent.replace(/[\r\n]+/g, " ");
            if (p_content.includes(matched_text)) {
              p.innerHTML = p_content.replace(
                matched_text,
                "<mark>" + matched_text + "</mark>"
              );
              console.log("highlighted", matched_text, "in", p);
              if (modal.style.display == "block") {
                // trigger on click event of PDF Preview link
                var detail_elem = p;
                // traverse up the DOM tree to find the parent element with tag detail
                while (detail_elem.tagName.toLowerCase() != "details") {
                  detail_elem = detail_elem.parentElement;
                }
                detail_elem.getElementsByClassName("pdf-link").item(0).click();
              } else {
                p.scrollIntoView({ behavior: "smooth", block: "center" });
              }
              break;
            }
          }
        }
      }
    });
  };

  globalThis.spawnDocument = (content, options) => {
    let opt = {
      window: "",
      closeChild: true,
      childId: "_blank",
    };
    Object.assign(opt, options);
    // minimal error checking
    if (
      content &&
      typeof content.toString == "function" &&
      content.toString().length
    ) {
      let child = window.open("", opt.childId, opt.window);
      child.document.write(content.toString());
      if (opt.closeChild) child.document.close();
      return child;
    }
  };

  globalThis.fillChatInput = (event) => {
    let chatInput = document.querySelector("#chat-input textarea");
    // fill the chat input with the clicked div text
    chatInput.value = "Explain " + event.target.textContent;
    var evt = new Event("change");
    chatInput.dispatchEvent(new Event("input", { bubbles: true }));
    chatInput.focus();
  };

  enforceAnswerPanelScroll();
  syncMainPdfPreview();
  if (!answerPanelObserver) {
    answerPanelObserver = new MutationObserver(() => {
      enforceAnswerPanelScroll();
    });

    answerPanelObserver.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: true,
    });
  }

  if (!previewSrcPoller) {
    previewSrcPoller = window.setInterval(syncMainPdfPreview, 120);
  }
}

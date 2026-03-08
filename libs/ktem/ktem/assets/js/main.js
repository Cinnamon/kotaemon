function run() {
  let answerPanelObserver = globalThis._ktemAnswerPanelObserver || null;
  let previewSrcPoller = globalThis._ktemPreviewSrcPoller || null;
  let lastPreviewSrc = globalThis._ktemLastPreviewSrc || null;
  let selectionPromptBox = null;
  let selectionPromptInput = null;
  let selectionPromptAsk = null;
  let selectionPromptClose = null;
  let currentSelectedPageText = "";
  let officeZoomControl = null;
  let officeZoomSlider = null;
  let officeZoomLabel = null;
  let isOfficePreview = false;
  let lastNonEmptySelectionTs = 0;
  let previewDebugLast = "";
  let lastDocKey = "";
  let lastAssignedPreviewSrc = globalThis._ktemLastAssignedPreviewSrc || "";
  let lastStablePreviewSrc = globalThis._ktemLastStablePreviewSrc || "";
  let lastPostedPageDocKey = globalThis._ktemLastPostedPageDocKey || "";
  let lastPostedPageNumber = globalThis._ktemLastPostedPageNumber || 0;

  function parsePreviewFitMode(src) {
    try {
      let url = new URL(src, window.location.origin);
      return (url.searchParams.get("ktemfit") || "pdf").toLowerCase();
    } catch (error) {
      return "pdf";
    }
  }

  function previewDebug(payload) {
    try {
      const text = JSON.stringify(payload);
      if (text === previewDebugLast) {
        return;
      }
      previewDebugLast = text;
      console.log("[preview-sync]", payload);
    } catch (error) {
      console.log("[preview-sync]", payload);
    }
  }

  function ensureOfficeZoomControl() {
    if (officeZoomControl) {
      return;
    }
    const shell = document.querySelector("#main-pdf-preview .pdf-preview-shell");
    if (!shell) {
      return;
    }

    officeZoomControl = document.createElement("div");
    officeZoomControl.id = "ktem-office-zoom-control";
    officeZoomControl.style.position = "absolute";
    officeZoomControl.style.right = "10px";
    officeZoomControl.style.bottom = "10px";
    officeZoomControl.style.zIndex = "10";
    officeZoomControl.style.display = "none";
    officeZoomControl.style.alignItems = "center";
    officeZoomControl.style.gap = "8px";
    officeZoomControl.style.padding = "6px 8px";
    officeZoomControl.style.borderRadius = "10px";
    officeZoomControl.style.background = "rgba(255,255,255,0.95)";
    officeZoomControl.style.border = "1px solid var(--border-color-primary,#d4d4d8)";
    officeZoomControl.style.boxShadow = "0 4px 12px rgba(0,0,0,0.1)";
    officeZoomControl.innerHTML = `
      <span style="font-size:12px;color:#111827;white-space:nowrap;">Zoom</span>
      <input id="ktem-office-zoom-slider" type="range" min="35" max="250" step="5" value="100" style="width:140px;accent-color:#2563eb;" />
      <span id="ktem-office-zoom-label" style="font-size:12px;min-width:42px;text-align:right;color:#111827;">100%</span>
    `;
    shell.appendChild(officeZoomControl);

    officeZoomSlider = officeZoomControl.querySelector("#ktem-office-zoom-slider");
    officeZoomLabel = officeZoomControl.querySelector("#ktem-office-zoom-label");
    if (officeZoomSlider) {
      officeZoomSlider.addEventListener("input", () => {
        const iframe = document.getElementById("main-pdf-preview-frame");
        if (!iframe || !iframe.contentWindow || !isOfficePreview) {
          return;
        }
        const zoomValue = parseInt(officeZoomSlider.value || "100", 10);
        if (officeZoomLabel) {
          officeZoomLabel.textContent = `${zoomValue}%`;
        }
        iframe.contentWindow.postMessage(
          { type: "ktem-pdf-zoom-set", zoom: zoomValue / 100 },
          window.location.origin
        );
      });
    }
  }

  function setOfficeZoomControlVisible(visible) {
    ensureOfficeZoomControl();
    if (!officeZoomControl) {
      return;
    }
    officeZoomControl.style.display = visible ? "inline-flex" : "none";
  }

  function updateOfficeZoomControl(scaleValue) {
    if (!officeZoomSlider || !officeZoomLabel) {
      return;
    }
    const percent = Math.max(35, Math.min(250, Math.round((scaleValue || 1) * 100)));
    officeZoomSlider.value = String(percent);
    officeZoomLabel.textContent = `${percent}%`;
  }

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
    const currentPage = getCurrentPageNumber();
    const srcFields = document.querySelectorAll(
      "#main-pdf-preview-src textarea, #main-pdf-preview-src input"
    );
    let srcField = null;
    if (srcFields && srcFields.length > 0) {
      for (let i = srcFields.length - 1; i >= 0; i--) {
        const candidate = srcFields[i];
        const value = (candidate && candidate.value ? candidate.value : "").trim();
        if (value) {
          srcField = candidate;
          break;
        }
      }
      if (!srcField) {
        srcField = srcFields[srcFields.length - 1] || null;
      }
    }
    const srcCandidates = [];
    if (srcFields && srcFields.length > 0) {
      for (let i = 0; i < srcFields.length; i++) {
        const value = (srcFields[i] && srcFields[i].value ? srcFields[i].value : "").trim();
        if (value) {
          srcCandidates.push(value.slice(0, 160));
        }
      }
    }
    let iframe = document.getElementById("main-pdf-preview-frame");
    let image = document.getElementById("main-pdf-preview-image");
    let empty = document.getElementById("main-pdf-preview-empty");
    if (!srcField || !iframe || !image || !empty) {
      return;
    }

    let nextSrc = (srcField?.value || "").trim();
    const currentIframeSrc = (iframe.getAttribute("src") || "").trim();
    const getPageFromSrc = (src) => {
      try {
        const u = new URL(src, window.location.origin);
        const q = parseInt(u.searchParams.get("ktempage") || "", 10);
        if (Number.isFinite(q) && q > 0) return q;
        const h = new URLSearchParams((u.hash || "").replace(/^#/, ""));
        const hp = parseInt(h.get("page") || "", 10);
        return Number.isFinite(hp) && hp > 0 ? hp : null;
      } catch (error) {
        return null;
      }
    };
    const withPageHash = (src, page) => {
      try {
        const u = new URL(src, window.location.origin);
        if (Number.isFinite(page) && page > 0) {
          u.searchParams.set("ktempage", String(page));
          u.hash = `page=${page}`;
        }
        return u.toString();
      } catch (error) {
        return src;
      }
    };
    const toAbsolute = (src) => {
      try {
        return new URL(src, window.location.origin).toString();
      } catch (error) {
        return src || "";
      }
    };
    const getDocKey = (src) => {
      try {
        const u = new URL(src, window.location.origin);
        const f = u.searchParams.get("file") || "";
        return `${u.pathname}|${f}`;
      } catch (error) {
        return (src || "").split("#")[0];
      }
    };
    const postPageChangeIfNeeded = (targetIframe, targetPage, docKey, force = false) => {
      if (
        !targetIframe ||
        !targetIframe.contentWindow ||
        !Number.isFinite(targetPage) ||
        targetPage <= 0
      ) {
        return false;
      }
      const normalizedDocKey = docKey || "";
      if (
        !force &&
        normalizedDocKey &&
        normalizedDocKey === lastPostedPageDocKey &&
        targetPage === lastPostedPageNumber
      ) {
        return false;
      }
      try {
        targetIframe.contentWindow.postMessage(
          { type: "ktem-pdf-page-change", page: targetPage },
          window.location.origin
        );
        lastPostedPageDocKey = normalizedDocKey;
        lastPostedPageNumber = targetPage;
        globalThis._ktemLastPostedPageDocKey = lastPostedPageDocKey;
        globalThis._ktemLastPostedPageNumber = lastPostedPageNumber;
        return true;
      } catch (error) {
        return false;
      }
    };
    const nextDocKey = getDocKey(nextSrc);
    const currentDocKey = getDocKey(currentIframeSrc);
    const chosenPage = getPageFromSrc(nextSrc);
    const desiredPage = Number.isFinite(currentPage) && currentPage > 0 ? currentPage : chosenPage;
    previewDebug({
      page: currentPage,
      candidates: srcCandidates,
      chosen: nextSrc.slice(0, 160),
      current: currentIframeSrc.slice(0, 160),
      chosenPage: chosenPage,
      desiredPage: Number.isFinite(desiredPage) && desiredPage > 0 ? desiredPage : null,
      currentSrcPage: getPageFromSrc(currentIframeSrc),
      lastStable: (lastStablePreviewSrc || "").slice(0, 160),
      postedDocKey: (lastPostedPageDocKey || "").slice(0, 80),
      postedPage: lastPostedPageNumber || null,
    });
    const normalizedNextSrc = toAbsolute(withPageHash(nextSrc, desiredPage));
    const normalizedCurrentSrc = toAbsolute(currentIframeSrc);
    const sameDoc =
      !!nextDocKey &&
      !!currentDocKey &&
      nextDocKey === currentDocKey;

    if (
      (nextSrc === lastPreviewSrc || normalizedNextSrc === lastAssignedPreviewSrc) &&
      normalizedCurrentSrc === normalizedNextSrc
    ) {
      return;
    }
    lastPreviewSrc = nextSrc;
    globalThis._ktemLastPreviewSrc = nextSrc;

    if (!nextSrc) {
      // Gradio can transiently clear hidden field values during rerenders.
      // Keep rendering the last stable preview source instead of blanking UI.
      if (lastStablePreviewSrc) {
        nextSrc = lastStablePreviewSrc;
      } else if (currentIframeSrc) {
        nextSrc = currentIframeSrc;
      } else {
        isOfficePreview = false;
        setOfficeZoomControlVisible(false);
        iframe.style.display = "none";
        image.style.display = "none";
        empty.style.display = "flex";
        iframe.removeAttribute("src");
        image.removeAttribute("src");
        return;
      }
    }

    const isImage = nextSrc.startsWith("data:image") || /\.(png|jpg|jpeg|gif|webp|svg)(\?|#|$)/i.test(nextSrc);
    if (isImage) {
      isOfficePreview = false;
      setOfficeZoomControlVisible(false);
      iframe.style.display = "none";
      empty.style.display = "none";
      image.style.display = "block";
      image.src = nextSrc;
      return;
    }

    image.style.display = "none";
    empty.style.display = "none";
    iframe.style.display = "block";
    const fitMode = parsePreviewFitMode(nextSrc);
    isOfficePreview = fitMode === "office";
    setOfficeZoomControlVisible(isOfficePreview);

    iframe.onload = () => {
      bindIframeSelectionFallback(iframe);
      if (!iframe.contentWindow) {
        return;
      }
      postPageChangeIfNeeded(iframe, desiredPage, nextDocKey, true);
      if (isOfficePreview) {
        iframe.contentWindow.postMessage(
          { type: "ktem-pdf-zoom-request" },
          window.location.origin
        );
      }
    };
    iframe.style.display = "block";
    iframe.style.width = "100%";
    iframe.style.height = "100%";

    // Avoid iframe reload flicker when switching pages within the same document.
    if (sameDoc && iframe.contentWindow) {
      postPageChangeIfNeeded(iframe, desiredPage, nextDocKey, false);
      if (normalizedNextSrc) {
        lastAssignedPreviewSrc = normalizedNextSrc;
        globalThis._ktemLastAssignedPreviewSrc = lastAssignedPreviewSrc;
        lastStablePreviewSrc = normalizedNextSrc;
        globalThis._ktemLastStablePreviewSrc = lastStablePreviewSrc;
      }
      return;
    }

    nextSrc = normalizedNextSrc;
    if (normalizedCurrentSrc === normalizedNextSrc) {
      if (normalizedNextSrc) {
        lastStablePreviewSrc = normalizedNextSrc;
        globalThis._ktemLastStablePreviewSrc = lastStablePreviewSrc;
      }
      return;
    }
    lastDocKey = nextDocKey || lastDocKey;
    lastPostedPageDocKey = "";
    lastPostedPageNumber = 0;
    globalThis._ktemLastPostedPageDocKey = lastPostedPageDocKey;
    globalThis._ktemLastPostedPageNumber = lastPostedPageNumber;
    iframe.src = nextSrc;
    lastAssignedPreviewSrc = nextSrc;
    globalThis._ktemLastAssignedPreviewSrc = lastAssignedPreviewSrc;
    if (nextSrc) {
      lastStablePreviewSrc = nextSrc;
      globalThis._ktemLastStablePreviewSrc = lastStablePreviewSrc;
    }
  }

  function bindIframeSelectionFallback(iframe) {
    if (!iframe || iframe._ktemSelectionFallbackBound) {
      return;
    }
    iframe._ktemSelectionFallbackBound = true;

    const attach = () => {
      try {
        const doc = iframe.contentDocument || iframe.contentWindow?.document;
        if (!doc || doc._ktemSelectionFallbackAttached) {
          return;
        }
        doc._ktemSelectionFallbackAttached = true;
        doc.addEventListener("mouseup", () => {
          try {
            const sel = iframe.contentWindow?.getSelection?.();
            const text = (sel && sel.toString ? sel.toString() : "").trim();
            if (!text) {
              if (Date.now() - lastNonEmptySelectionTs >= 200) {
                hideSelectionPrompt();
              }
              return;
            }
            let rect = { left: 0, top: 0, width: 0, height: 0 };
            const range = sel.rangeCount > 0 ? sel.getRangeAt(0) : null;
            if (range) {
              const r = range.getBoundingClientRect();
              rect = {
                left: Number.isFinite(r.left) ? r.left : 0,
                top: Number.isFinite(r.top) ? r.top : 0,
                width: Number.isFinite(r.width) ? r.width : 0,
                height: Number.isFinite(r.height) ? r.height : 0,
              };
            }
            currentSelectedPageText = text.slice(0, 2000);
            setSelectedPageText(currentSelectedPageText);
            lastNonEmptySelectionTs = Date.now();
            showSelectionPromptNearRect(rect);
          } catch (error) {
            // ignore fallback selection errors
          }
        });
      } catch (error) {
        // ignore iframe access errors
      }
    };

    iframe.addEventListener("load", attach);
    attach();
  }

  function setSelectedPageText(value) {
    let selectionField = document.querySelector(
      "#selected-page-text textarea, #selected-page-text input"
    );
    if (!selectionField) {
      return;
    }

    selectionField.value = value || "";
    selectionField.dispatchEvent(new Event("input", { bubbles: true }));
    selectionField.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function getChatInputField() {
    return document.querySelector("#chat-input textarea");
  }

  function submitChatInput() {
    const chatInput = getChatInputField();
    if (!chatInput) {
      return;
    }

    const candidates = Array.from(
      document.querySelectorAll("#chat-input-row button")
    ).filter((btn) => {
      if (!btn || btn.disabled) return false;
      const style = window.getComputedStyle(btn);
      if (style.display === "none" || style.visibility === "hidden") return false;
      return true;
    });

    const semanticButton = candidates.find((btn) => {
      const text = (btn.innerText || "").toLowerCase();
      const aria = (btn.getAttribute("aria-label") || "").toLowerCase();
      const title = (btn.getAttribute("title") || "").toLowerCase();
      const cls = (btn.className || "").toLowerCase();
      return (
        text.includes("send") ||
        text.includes("submit") ||
        aria.includes("send") ||
        aria.includes("submit") ||
        title.includes("send") ||
        title.includes("submit") ||
        cls.includes("submit")
      );
    });

    const submitButton =
      semanticButton || (candidates.length ? candidates[candidates.length - 1] : null);

    if (submitButton) {
      submitButton.click();
      window.setTimeout(() => submitButton.click(), 120);
      return;
    }

    const form = chatInput.closest("form");
    if (form && typeof form.requestSubmit === "function") {
      form.requestSubmit();
      return;
    }

    chatInput.focus();
    ["keydown", "keypress", "keyup"].forEach((eventName) => {
      chatInput.dispatchEvent(
        new KeyboardEvent(eventName, {
          key: "Enter",
          code: "Enter",
          bubbles: true,
        })
      );
    });
  }

  function ensureSelectionPrompt() {
    if (selectionPromptBox) {
      return;
    }

    selectionPromptBox = document.createElement("div");
    selectionPromptBox.id = "ktem-selection-prompt";
    selectionPromptBox.style.position = "fixed";
    selectionPromptBox.style.zIndex = "9999";
    selectionPromptBox.style.display = "none";
    selectionPromptBox.style.width = "420px";
    selectionPromptBox.style.maxWidth = "min(420px, calc(100vw - 24px))";
    selectionPromptBox.style.background = "var(--input-background-fill, var(--background-fill-primary, #fff))";
    selectionPromptBox.style.border = "1px solid var(--border-color-primary, #d4d4d8)";
    selectionPromptBox.style.borderRadius = "10px";
    selectionPromptBox.style.boxShadow = "0 8px 20px rgba(0,0,0,0.12)";
    selectionPromptBox.style.padding = "8px";
    selectionPromptBox.style.backdropFilter = "blur(4px)";
    selectionPromptBox.style.boxSizing = "border-box";
    selectionPromptBox.innerHTML = `
      <div style="display:flex; align-items:center; justify-content:space-between; gap:8px; margin-bottom:6px;">
        <strong style="font-size:12px; color: var(--body-text-color, inherit);">Ask About Selection</strong>
        <button id="ktem-selection-close" type="button" style="border:none;background:transparent;cursor:pointer;font-size:14px;line-height:1;color:var(--body-text-color-subdued,inherit);">x</button>
      </div>
      <div style="display:flex;align-items:center;gap:8px;">
        <input id="ktem-selection-question" type="text" placeholder="Ask a question about this selected text" style="flex:1 1 auto;min-width:0;height:34px;box-sizing:border-box;border:1px solid var(--border-color-primary,#d4d4d8);border-radius:8px;padding:0 10px;font-size:13px;background:var(--input-background-fill,#fff);color:var(--body-text-color,inherit);" />
        <button id="ktem-selection-ask" type="button" style="height:34px;padding:0 12px;border-radius:8px;border:1px solid var(--border-color-primary,#d4d4d8);cursor:pointer;background:var(--button-primary-background-fill,var(--background-fill-secondary,#f4f4f5));color:var(--button-primary-text-color,var(--body-text-color,inherit));white-space:nowrap;">Ask</button>
      </div>
    `;
    document.body.appendChild(selectionPromptBox);

    selectionPromptInput = selectionPromptBox.querySelector("#ktem-selection-question");
    selectionPromptAsk = selectionPromptBox.querySelector("#ktem-selection-ask");
    selectionPromptClose = selectionPromptBox.querySelector("#ktem-selection-close");

    selectionPromptClose.onclick = () => {
      hideSelectionPrompt();
      setSelectedPageText("");
      currentSelectedPageText = "";
    };
    selectionPromptAsk.onclick = () => {
      const question = (selectionPromptInput?.value || "").trim();
      const chatInput = getChatInputField();
      if (!chatInput) {
        return;
      }

      const baseQuestion = question || "Please explain this selected text.";
      const selectedBlock = (currentSelectedPageText || "").trim();
      if (selectedBlock) {
        chatInput.value =
          `${baseQuestion}\n\n[Selected text from current page]\n${selectedBlock}`;
      } else {
        chatInput.value = baseQuestion;
      }
      chatInput.dispatchEvent(new Event("input", { bubbles: true }));
      chatInput.dispatchEvent(new Event("change", { bubbles: true }));
      window.setTimeout(() => submitChatInput(), 0);
      hideSelectionPrompt();
    };
  }

  function hideSelectionPrompt() {
    if (!selectionPromptBox) {
      return;
    }
    selectionPromptBox.style.display = "none";
    if (selectionPromptInput) {
      selectionPromptInput.value = "";
    }
  }

  function showSelectionPromptNearRect(rectInIframe) {
    ensureSelectionPrompt();
    const iframe = document.getElementById("main-pdf-preview-frame");
    if (!selectionPromptBox || !iframe) {
      return;
    }

    const iframeRect = iframe.getBoundingClientRect();
    const rect = rectInIframe || { left: 0, top: 0, width: 0, height: 0 };
    const baseLeft = iframeRect.left + (rect.left || 0);
    const baseTop = iframeRect.top + (rect.top || 0) + (rect.height || 0) + 8;

    let left = Math.max(12, baseLeft);
    let top = Math.max(12, baseTop);
    const boxWidth = 420;
    const boxHeight = 96;
    const viewportWidth = window.innerWidth || document.documentElement.clientWidth || 0;
    const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 0;

    if (left + boxWidth > viewportWidth - 12) {
      left = Math.max(12, viewportWidth - boxWidth - 12);
    }
    if (top + boxHeight > viewportHeight - 12) {
      top = Math.max(12, iframeRect.top + (rect.top || 0) - boxHeight - 8);
    }

    selectionPromptBox.style.left = `${left}px`;
    selectionPromptBox.style.top = `${top}px`;
    selectionPromptBox.style.display = "block";
    if (selectionPromptInput) {
      selectionPromptInput.focus();
    }
  }

  function isSelectionPromptVisible() {
    return !!selectionPromptBox && selectionPromptBox.style.display !== "none";
  }

  function getCurrentPageNumber() {
    const pageFields = document.querySelectorAll(
      "#pdf-page-number input, #pdf-page-number textarea"
    );
    if (!pageFields || pageFields.length === 0) {
      return null;
    }
    for (let i = pageFields.length - 1; i >= 0; i--) {
      const value = (pageFields[i]?.value || "").trim();
      const page = parseInt(value, 10);
      if (Number.isFinite(page) && page > 0) {
        return page;
      }
    }
    return null;
  }

  syncMainPdfPreview();

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
    try {
      if (typeof MiniSearch === "undefined") {
        return;
      }

    // Assign text selection event to last bot message
    var bot_messages = document.querySelectorAll(
      "div#main-chat-bot div.message-row.bot-row"
    );
    if (!bot_messages || bot_messages.length === 0) {
      return;
    }
    var last_bot_message = bot_messages[bot_messages.length - 1];
    if (!last_bot_message || !last_bot_message.classList) {
      return;
    }

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
      if (!selection || !selection.trim()) {
        return;
      }
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
    } catch (error) {
      console.warn("fullTextSearch init skipped:", error);
    }
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
  if (!globalThis._ktemSelectionBridgeRegistered) {
    window.addEventListener("message", (event) => {
      if (event.origin !== window.location.origin) {
        return;
      }

      if (event.data?.type === "ktem-office-diagnostics") {
        console.log("[office-preview-diag][parent]", event.data.payload || null);
        return;
      }

      if (event.data?.type === "ktem-pdf-zoom-updated") {
        if (isOfficePreview) {
          const zoom = parseFloat(event.data.zoom || "");
          if (Number.isFinite(zoom) && zoom > 0) {
            updateOfficeZoomControl(zoom);
          }
        }
        return;
      }

      if (event.data?.type !== "ktem-pdf-text-selection") {
        return;
      }

      let selectedText = (event.data.text || "").trim();
      let selectedPage = parseInt(event.data.page || "", 10);
      let currentPage = getCurrentPageNumber();

      if (
        Number.isFinite(selectedPage) &&
        Number.isFinite(currentPage) &&
        selectedPage !== currentPage
      ) {
        return;
      }

      if (selectedText.length > 2000) {
        selectedText = selectedText.slice(0, 2000);
      }
      currentSelectedPageText = selectedText;
      setSelectedPageText(selectedText);
      if (!selectedText) {
        // Ignore transient empty-selection events right after a valid selection.
        if (Date.now() - lastNonEmptySelectionTs < 350) {
          return;
        }
        hideSelectionPrompt();
      } else {
        lastNonEmptySelectionTs = Date.now();
        showSelectionPromptNearRect(event.data.rect);
      }
    });
    globalThis._ktemSelectionBridgeRegistered = true;
  }

  if (!globalThis._ktemSelectionPromptOutsideCloseRegistered) {
    document.addEventListener("mousedown", (event) => {
      if (!isSelectionPromptVisible()) {
        return;
      }
      const target = event.target;
      if (selectionPromptBox && selectionPromptBox.contains(target)) {
        return;
      }
      hideSelectionPrompt();
    });
    globalThis._ktemSelectionPromptOutsideCloseRegistered = true;
  }

  if (!answerPanelObserver) {
    answerPanelObserver = new MutationObserver(() => {
      enforceAnswerPanelScroll();
    });

    answerPanelObserver.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: true,
    });
    globalThis._ktemAnswerPanelObserver = answerPanelObserver;
  }

  if (!previewSrcPoller) {
    previewSrcPoller = window.setInterval(syncMainPdfPreview, 120);
    globalThis._ktemPreviewSrcPoller = previewSrcPoller;
  }
}

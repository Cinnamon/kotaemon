function run() {
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
  chat_info_panel.insertBefore(info_expand_button, chat_info_panel.childNodes[2]);

  // move toggle-side-bar button
  let chat_expand_button = document.getElementById("chat-expand-button");
  let chat_column = document.getElementById("main-chat-bot");
  let conv_column = document.getElementById("conv-settings-panel");

  // move setting close button
  let setting_tab_nav_bar = document.querySelector("#settings-tab .tab-nav");
  let setting_close_button = document.getElementById("save-setting-btn");
  if (setting_close_button) {
    setting_tab_nav_bar.appendChild(setting_close_button);
  }

  let default_conv_column_min_width = "min(300px, 100%)";
  conv_column.style.minWidth = default_conv_column_min_width

  globalThis.toggleChatColumn = (() => {
    /* get flex-grow value of chat_column */
    let flex_grow = conv_column.style.flexGrow;
    if (flex_grow == '0') {
      conv_column.style.flexGrow = '1';
      conv_column.style.minWidth = default_conv_column_min_width;
    } else {
      conv_column.style.flexGrow = '0';
      conv_column.style.minWidth = "0px";
    }
  });

  chat_column.insertBefore(chat_expand_button, chat_column.firstChild);

  // move use mind-map checkbox
  let mindmap_checkbox = document.getElementById("use-mindmap-checkbox");
  let citation_dropdown = document.getElementById("citation-dropdown");
  let chat_setting_panel = document.getElementById("chat-settings-expand");
  chat_setting_panel.insertBefore(mindmap_checkbox, chat_setting_panel.childNodes[2]);
  chat_setting_panel.insertBefore(citation_dropdown, mindmap_checkbox);

  // create slider toggle
  const is_public_checkbox = document.getElementById("suggest-chat-checkbox");
  const label_element = is_public_checkbox.getElementsByTagName("label")[0];
  const checkbox_span = is_public_checkbox.getElementsByTagName("span")[0];
  new_div = document.createElement("div");

  label_element.classList.add("switch");
  is_public_checkbox.appendChild(checkbox_span);
  label_element.appendChild(new_div)

  // clpse
  globalThis.clpseFn = (id) => {
    var obj = document.getElementById('clpse-btn-' + id);
    obj.classList.toggle("clpse-active");
    var content = obj.nextElementSibling;
    if (content.style.display === "none") {
      content.style.display = "block";
    } else {
      content.style.display = "none";
    }
  }

  // store info in local storage
  globalThis.setStorage = (key, value) => {
      localStorage.setItem(key, value)
  }
  globalThis.getStorage = (key, value) => {
    item = localStorage.getItem(key);
    return item ? item : value;
  }
  globalThis.removeFromStorage = (key) => {
      localStorage.removeItem(key)
  }

  // Function to scroll to given citation with ID
  // Sleep function using Promise and setTimeout
  function sleep(ms) {
      return new Promise(resolve => setTimeout(resolve, ms));
  }

  globalThis.scrollToCitation = async (event) => {
      event.preventDefault(); // Prevent the default link behavior
      var citationId = event.target.getAttribute('id');

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
            citation.scrollIntoView({ behavior: 'smooth' });
        }
      }
  }
}

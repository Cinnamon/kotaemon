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

  // move info-expand-button
  let info_expand_button = document.getElementById("info-expand-button");
  let chat_info_panel = document.getElementById("info-expand");
  chat_info_panel.insertBefore(info_expand_button, chat_info_panel.childNodes[2]);

  // move use mind-map checkbox
  let mindmap_checkbox = document.getElementById("use-mindmap-checkbox");
  let chat_setting_panel = document.getElementById("chat-settings-expand");
  chat_setting_panel.insertBefore(mindmap_checkbox, chat_setting_panel.childNodes[2]);

  // create slider toggle
  const is_public_checkbox = document.getElementById("is-public-checkbox");
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

      await sleep(100); // Sleep for 500 milliseconds
      var citation = document.querySelector('mark[id="' + citationId + '"]');
      if (citation) {
          citation.scrollIntoView({ behavior: 'smooth' });
      }
  }
}

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
}

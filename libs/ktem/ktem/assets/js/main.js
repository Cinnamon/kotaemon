let main_parent = document.getElementById("chat-tab").parentNode;

main_parent.childNodes[0].classList.add("header-bar");
main_parent.style = "padding: 0; margin: 0";
main_parent.parentNode.style = "gap: 0";
main_parent.parentNode.parentNode.style = "padding: 0";


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

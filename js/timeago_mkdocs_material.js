// Script to ensure timeago keeps working when 
// used with mkdocs-material's instant loading feature 

if (typeof document$ !== "undefined") {
    document$.subscribe(function() {
        var nodes = document.querySelectorAll('.timeago');
        if (nodes.length > 0) {
          var locale = nodes[0].getAttribute('locale');
          timeago.render(nodes, locale);
        }
    })
} else {
    var nodes = document.querySelectorAll('.timeago');
    if (nodes.length > 0) {
      var locale = nodes[0].getAttribute('locale');
      timeago.render(nodes, locale);
    }
}

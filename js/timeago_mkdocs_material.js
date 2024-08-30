// Script to ensure timeago keeps working when
// used with mkdocs-material's instant loading feature

function getLocale(element) {
    var raw_locale = element.getAttribute('locale');
    var locale = {
        bn: 'bn_IN',
        en: 'en_US',
        hi: 'hi_IN',
        id: 'id_ID',
        nb: 'nb_NO',
        nn: 'nn_NO',
        pt: 'pt_BR',
        zh: 'zh_CN'
    }[raw_locale];
    return locale ? locale : raw_locale;
}

if (typeof document$ !== "undefined") {
    document$.subscribe(function() {
        var nodes = document.querySelectorAll('.timeago');
        if (nodes.length > 0) {
            var locale = getLocale(nodes[0]);
            timeago.render(nodes, locale);
        }
    })
} else {
    var nodes = document.querySelectorAll('.timeago');
    if (nodes.length > 0) {
        var locale = getLocale(nodes[0]);
        timeago.render(nodes, locale);
    }
}

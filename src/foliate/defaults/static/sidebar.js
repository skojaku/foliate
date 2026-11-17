/* Page index on the left. Built in the browser from search.json, so adding a
   page never needs the other pages to be rebuilt. Text is set with
   textContent, never innerHTML: titles come from the vault. */
(function () {
  var el = document.getElementById("site-sidebar");
  if (!el) return;

  function node(tag, text, cls) {
    var n = document.createElement(tag);
    if (text !== undefined) n.textContent = text;
    if (cls) n.className = cls;
    return n;
  }

  function title(page) {
    if (page.path === "index") return "Home";
    if (page.title && page.title !== page.path) return page.title;
    return label(page.path);
  }

  function link(page, current) {
    var a = node("a", title(page));
    if (typeof page.url === "string" && page.url.charAt(0) === "/") a.href = page.url;
    if (page.url === current) a.setAttribute("aria-current", "page");
    return a;
  }

  function label(path) {
    var last = path.split("/").pop();
    return last.charAt(0).toUpperCase() + last.slice(1).replace(/-/g, " ");
  }

  fetch(el.getAttribute("data-index"))
    .then(function (r) { return r.json(); })
    .then(function (pages) {
      var current = decodeURI(location.pathname).replace(/\/?$/, "/");
      var folders = {};
      var currentFolder = null;
      pages.forEach(function (p) {
        var parts = p.path.split("/");
        parts.pop();
        var key = parts.join("/");
        if (p.url === current) currentFolder = key;
        (folders[key] = folders[key] || []).push(p);
      });

      var byTitle = function (a, b) {
        return title(a).toLowerCase().localeCompare(title(b).toLowerCase());
      };
      var isIndex = function (p) { return p.path.split("/").pop() === "index"; };

      var root = node("ul", undefined, "sidebar-list");
      (folders[""] || []).sort(byTitle).forEach(function (p) {
        var li = node("li");
        li.appendChild(link(p, current));
        root.appendChild(li);
      });
      el.appendChild(root);

      Object.keys(folders).filter(Boolean).sort().forEach(function (key) {
        var list = folders[key];
        var index = list.filter(isIndex)[0];
        var rest = list.filter(function (p) { return !isIndex(p); }).sort(byTitle);
        var folder = node("div", undefined, "sidebar-folder");
        var title = node("div", undefined, "sidebar-folder-title");
        if (index) {
          title.appendChild(link({ title: label(key), url: index.url, path: index.path }, current));
        } else {
          title.textContent = label(key);
        }
        folder.appendChild(title);
        if (key === currentFolder) {
          var ul = node("ul", undefined, "sidebar-list");
          rest.forEach(function (p) {
            var li = node("li");
            li.appendChild(link(p, current));
            ul.appendChild(li);
          });
          folder.appendChild(ul);
        }
        el.appendChild(folder);
      });

    })
    .catch(function () { el.hidden = true; });
})();

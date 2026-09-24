document.addEventListener('DOMContentLoaded', () => {
  // Mobile sidebar toggle
  const toggle = document.querySelector('.menu-toggle');
  const sidebar = document.querySelector('.docs-sidebar');
  if (toggle && sidebar) {
    toggle.addEventListener('click', () => sidebar.classList.toggle('open'));
    document.addEventListener('click', (e) => {
      if (window.innerWidth > 900) return;
      if (!sidebar.contains(e.target) && !toggle.contains(e.target)) {
        sidebar.classList.remove('open');
      }
    });
  }

  // Highlight current page in sidebar
  const links = document.querySelectorAll('.sidebar-link');
  links.forEach(link => {
    if (link.pathname === location.pathname) {
      link.classList.add('active');
    }
  });

  // Simple in-page search (highlight terms)
  const search = document.querySelector('.search-input');
  if (search) {
    search.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const q = search.value.trim().toLowerCase();
        if (!q) return;
        const content = document.querySelector('.docs-content');
        if (!content) return;
        // Clear previous highlights before collecting fresh text nodes.
        content.querySelectorAll('.search-highlight').forEach(el => {
          const parent = el.parentNode;
          parent.replaceChild(document.createTextNode(el.textContent), el);
          parent.normalize();
        });
        const walker = document.createTreeWalker(content, NodeFilter.SHOW_TEXT);
        const nodes = [];
        let node;
        while ((node = walker.nextNode())) {
          if (node.nodeValue.toLowerCase().includes(q)) nodes.push(node);
        }
        let firstMatch;
        nodes.forEach(textNode => {
          const mark = document.createElement('mark');
          mark.className = 'search-highlight';
          const idx = textNode.nodeValue.toLowerCase().indexOf(q);
          const match = textNode.splitText(idx);
          match.splitText(q.length);
          mark.textContent = match.nodeValue;
          match.parentNode.replaceChild(mark, match);
          if (!firstMatch) firstMatch = mark;
        });
        if (firstMatch) firstMatch.scrollIntoView({ behavior: 'auto', block: 'center' });
      }
    });
  }
});

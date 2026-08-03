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
        const walker = document.createTreeWalker(content, NodeFilter.SHOW_TEXT, null, false);
        const nodes = [];
        let node;
        while ((node = walker.nextNode())) {
          if (node.nodeValue.toLowerCase().includes(q)) nodes.push(node);
        }
        if (nodes.length) {
          // Clear old highlights
          document.querySelectorAll('.search-highlight').forEach(el => {
            const parent = el.parentNode;
            parent.replaceChild(document.createTextNode(el.textContent), el);
            parent.normalize();
          });
          nodes.forEach(textNode => {
            const span = document.createElement('span');
            span.className = 'search-highlight';
            span.style.background = '#fff3b0';
            span.style.borderRadius = '3px';
            const idx = textNode.nodeValue.toLowerCase().indexOf(q);
            const before = textNode.nodeValue.slice(0, idx);
            const match = textNode.nodeValue.slice(idx, idx + q.length);
            const after = textNode.nodeValue.slice(idx + q.length);
            const parent = textNode.parentNode;
            parent.insertBefore(document.createTextNode(before), textNode);
            span.textContent = match;
            parent.insertBefore(span, textNode);
            parent.insertBefore(document.createTextNode(after), textNode);
            parent.removeChild(textNode);
            parent.normalize();
          });
          nodes[0].parentNode.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }
    });
  }
});

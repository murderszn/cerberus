// Preserve existing shared scanner/report URLs after moving the tool to agent.html.
(function () {
  function forwardAgentRoute() {
    if (/^#\/(?:scan|report)\//.test(window.location.hash)) {
      window.location.replace('agent.html' + window.location.search + window.location.hash);
    }
  }
  forwardAgentRoute();
  window.addEventListener('hashchange', forwardAgentRoute);
})();

/* Quiet, local UI feedback. Audio is created only during a user gesture. */
(function () {
  'use strict';
  var preferenceKey = 'cerberus:sound-enabled';
  var enabled = true, context = null, lastSound = -Infinity;
  var toggle = document.querySelector('[data-sound-toggle]');
  try { enabled = localStorage.getItem(preferenceKey) !== 'false'; } catch (e) { /* Keep in-memory preference. */ }
  function updateToggle() {
    if (!toggle) return;
    toggle.textContent = enabled ? 'Sound on' : 'Sound off';
    toggle.setAttribute('aria-pressed', String(enabled));
    toggle.setAttribute('aria-label', 'Click sounds');
    toggle.title = enabled ? 'Mute click sounds' : 'Enable click sounds';
  }
  function play() {
    if (!enabled || performance.now() - lastSound < 55) return;
    var Audio = window.AudioContext || window.webkitAudioContext;
    if (!Audio) return;
    try {
      if (!context || context.state === 'closed') context = new Audio();
      lastSound = performance.now();
      function tick() {
        if (!enabled || context.state !== 'running') return;
        var oscillator = context.createOscillator(), gain = context.createGain();
        var now = context.currentTime;
        oscillator.type = 'triangle';
        oscillator.frequency.setValueAtTime(920, now);
        oscillator.frequency.exponentialRampToValueAtTime(420, now + .032);
        gain.gain.setValueAtTime(.0001, now);
        gain.gain.exponentialRampToValueAtTime(.038, now + .003);
        gain.gain.exponentialRampToValueAtTime(.0001, now + .043);
        oscillator.connect(gain); gain.connect(context.destination);
        oscillator.onended = function () { oscillator.disconnect(); gain.disconnect(); };
        oscillator.start(now); oscillator.stop(now + .047);
      }
      if (context.state === 'suspended') context.resume().then(tick).catch(function () {});
      else tick();
    } catch (e) { /* Audio support must never interrupt navigation or scanning. */ }
  }
  function control(event) {
    var target = event.target && event.target.closest && event.target.closest('a[href], button, summary, [role="button"], select, input[type="checkbox"], input[type="radio"]');
    if (!target || target.disabled || target.getAttribute('aria-disabled') === 'true' || target.closest('[inert]') || target.hasAttribute('data-sound-toggle')) return null;
    return target;
  }
  document.addEventListener('pointerdown', function (event) {
    if (event.isTrusted && event.button === 0 && control(event)) play();
  }, { passive: true, capture: true });
  document.addEventListener('click', function (event) {
    if (event.isTrusted && event.detail === 0 && control(event)) play();
  }, true);
  // Custom button roles in the report handle Enter/Space without a native click.
  document.addEventListener('keydown', function (event) {
    var target = control(event);
    if (event.isTrusted && !event.repeat && (event.key === 'Enter' || event.key === ' ') && target && target.getAttribute('role') === 'button' && target.tagName !== 'BUTTON' && target.tagName !== 'A') play();
  }, true);
  if (toggle) toggle.addEventListener('click', function (event) {
    if (!event.isTrusted) return;
    enabled = !enabled;
    try { localStorage.setItem(preferenceKey, String(enabled)); } catch (e) {}
    updateToggle();
    if (enabled) play();
  });
  window.addEventListener('storage', function (event) {
    if (event.key === preferenceKey || event.key === null) {
      enabled = event.key === null || event.newValue !== 'false'; updateToggle();
    }
  });
  updateToggle();
})();

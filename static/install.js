// "Install App" nav item (templates/page_base.jinja). Hidden unless installing
// is actually possible:
//  - Chrome/Edge fire beforeinstallprompt when the site is installable, and the
//    saved event lets the button open the browser's install dialog
//  - iOS has no install API, so in Safari (outside the installed app) the
//    button instead explains Share -> Add to Home Screen
(function () {
  var item = document.getElementById('install-item');
  var button = document.getElementById('install-button');
  var iosDialog = document.getElementById('install-dialog');
  if (!item || !button) {
    return;
  }

  var deferredPrompt = null;
  var isStandalone =
    window.matchMedia('(display-mode: standalone)').matches ||
    navigator.standalone === true;
  // iPadOS reports itself as a Mac, so also check for a touch screen
  var isIos =
    /iphone|ipad|ipod/i.test(navigator.userAgent) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);

  function show() {
    item.style.display = '';
  }
  function hide() {
    item.style.display = 'none';
  }

  window.addEventListener('beforeinstallprompt', function (event) {
    // keep the browser's own mini-infobar from also appearing; the nav button
    // replaces it
    event.preventDefault();
    deferredPrompt = event;
    show();
  });

  window.addEventListener('appinstalled', function () {
    deferredPrompt = null;
    hide();
  });

  if (isIos && !isStandalone && iosDialog) {
    show();
  }

  button.addEventListener('click', async function () {
    if (deferredPrompt) {
      deferredPrompt.prompt();
      await deferredPrompt.userChoice;
      // a prompt event can only be used once
      deferredPrompt = null;
      hide();
    } else if (isIos && iosDialog) {
      iosDialog.showModal();
    }
  });
})();

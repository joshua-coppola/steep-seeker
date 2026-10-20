// Share buttons: any element with a data-share attribute (on the map and
// ranking pages). Installed apps have no address
// bar to copy a link from, so this uses the native share sheet when the
// browser has one and falls back to copying the link to the clipboard.
document.addEventListener('click', async function (event) {
  var button = event.target.closest('[data-share]');
  if (!button) {
    return;
  }

  var data = { title: document.title, url: window.location.href };

  if (navigator.share) {
    try {
      await navigator.share(data);
      return;
    } catch (error) {
      // the user closing the share sheet isn't an error worth falling back on
      if (error.name === 'AbortError') {
        return;
      }
    }
  }

  var label = button.textContent;
  try {
    await navigator.clipboard.writeText(data.url);
    button.textContent = 'Link copied';
  } catch (error) {
    button.textContent = 'Copy failed';
  }
  setTimeout(function () {
    button.textContent = label;
  }, 2000);
});

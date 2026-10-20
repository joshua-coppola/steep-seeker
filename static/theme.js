var currentTheme = 'light';
var root = undefined;

function updateThemeColors() {
  if (!root) {
    console.warn('root element not set in updateThemeColors');
  }
  if (currentTheme == 'dark') {
    root.classList.add('dark');
  } else {
    root.classList.remove('dark');
  }
  // keep the installed app's title bar / mobile browser chrome matching the page
  var themeColor = document.querySelector('meta[name="theme-color"]');
  if (themeColor) {
    themeColor.setAttribute('content', currentTheme == 'dark' ? '#000000' : '#ffffff');
  }
}

function toggleTheme() {
  if (currentTheme == 'light') {
    currentTheme = 'dark';
  } else {
    currentTheme = 'light';
  }
  if (localStorage) {
    localStorage.setItem('theme', currentTheme);
  }
  updateThemeColors();
}

window.addEventListener('load', function() {
  root = document.body;

  if (localStorage) {
    // nothing saved yet (first visit) means the default light theme
    currentTheme = localStorage.getItem('theme') || 'light';
  }

  updateThemeColors();
});

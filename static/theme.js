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
    currentTheme = localStorage.getItem('theme');
  }

  updateThemeColors();
});

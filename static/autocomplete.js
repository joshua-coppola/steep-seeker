// Mountain-name suggestions under a text box, drawn by the page rather than
// left to the browser's <datalist> (which Chrome shows as one long list off
// to the side and Firefox labels with only the state). Used by the search
// box and /compare's picker.
//
// Markup: <input data-autocomplete="ID"> plus a
// <script type="application/json" id="ID"> holding the options, each
// {value, name, detail}: `name` (and `detail`, the state) is what's shown
// and matched against, `value` what picking it puts in the box.
// Styled in autocomplete.css.
(function () {
  var MAX_SUGGESTIONS = 8
  var nextId = 0

  // name-starts-with matches first, then a later word starting with it,
  // then anywhere in "name, detail" -- each group kept in the list's order
  function matches(options, query) {
    var q = query.trim().toLowerCase(),
      groups = [[], [], []]
    if (!q) return []
    options.forEach(function (option) {
      var name = option.name.toLowerCase()
      if (name.indexOf(q) === 0) groups[0].push(option)
      else if (name.indexOf(' ' + q) !== -1) groups[1].push(option)
      else if ((name + ', ' + option.detail.toLowerCase()).indexOf(q) !== -1)
        groups[2].push(option)
    })
    return groups[0].concat(groups[1], groups[2]).slice(0, MAX_SUGGESTIONS)
  }

  function attach(input, options) {
    var list = document.createElement('ul'),
      listId = 'autocomplete-' + nextId++,
      shown = [],
      active = -1

    list.id = listId
    list.className = 'autocomplete-list'
    list.setAttribute('role', 'listbox')
    list.hidden = true
    // on <body>, not beside the input, so it never changes the layout the
    // input sits in (the search bar's children are styled as a row)
    document.body.appendChild(list)

    input.setAttribute('role', 'combobox')
    input.setAttribute('aria-autocomplete', 'list')
    input.setAttribute('aria-controls', listId)
    input.setAttribute('aria-expanded', 'false')
    input.setAttribute('autocomplete', 'off')

    function place() {
      var box = input.getBoundingClientRect()
      list.style.left = box.left + window.scrollX + 'px'
      list.style.top = box.bottom + window.scrollY + 4 + 'px'
      list.style.width = box.width + 'px'
    }

    function close() {
      list.hidden = true
      active = -1
      input.setAttribute('aria-expanded', 'false')
      input.removeAttribute('aria-activedescendant')
    }

    function highlight(index) {
      var items = list.children
      if (active !== -1) items[active].removeAttribute('aria-selected')
      active = index
      if (active === -1) {
        input.removeAttribute('aria-activedescendant')
        return
      }
      items[active].setAttribute('aria-selected', 'true')
      input.setAttribute('aria-activedescendant', items[active].id)
    }

    function choose(index) {
      input.value = shown[index].value
      close()
    }

    function update() {
      shown = matches(options, input.value)
      list.textContent = ''
      active = -1
      if (!shown.length) return close()
      shown.forEach(function (option, index) {
        var item = document.createElement('li'),
          detail = document.createElement('span')
        item.id = listId + '-' + index
        item.setAttribute('role', 'option')
        item.textContent = option.name
        detail.className = 'autocomplete-detail'
        detail.textContent = option.detail
        item.appendChild(detail)
        // mousedown, not click: it lands before the input's blur closes the list
        item.addEventListener('mousedown', function (event) {
          event.preventDefault()
          choose(index)
        })
        list.appendChild(item)
      })
      place()
      list.hidden = false
      input.setAttribute('aria-expanded', 'true')
    }

    input.addEventListener('input', update)
    input.addEventListener('blur', close)
    input.addEventListener('keydown', function (event) {
      if (list.hidden) {
        if (event.key === 'ArrowDown' && input.value) update()
        return
      }
      if (event.key === 'ArrowDown') {
        event.preventDefault()
        highlight((active + 1) % shown.length)
      } else if (event.key === 'ArrowUp') {
        event.preventDefault()
        highlight(active <= 0 ? shown.length - 1 : active - 1)
      } else if (event.key === 'Enter' && active !== -1) {
        // picks the highlighted suggestion instead of submitting the form
        event.preventDefault()
        choose(active)
      } else if (event.key === 'Escape') {
        close()
      }
    })
    window.addEventListener('resize', function () {
      if (!list.hidden) place()
    })
  }

  window.addEventListener('load', function () {
    document.querySelectorAll('[data-autocomplete]').forEach(function (input) {
      var source = document.getElementById(input.dataset.autocomplete)
      attach(input, JSON.parse(source.textContent))
    })
  })
})()

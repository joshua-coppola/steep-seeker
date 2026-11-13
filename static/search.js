// The search box and sort dropdown above the search results; the filters
// sidebar is filters.js. Submitting keeps the URL's filters and goes back to
// the first page.
window.addEventListener('load', function () {
  var form = document.getElementById('search-form'),
    search = document.getElementById('search'),
    sort = document.getElementById('sort'),
    params = new URLSearchParams(location.search)

  params.get('q') && (search.value = params.get('q'))
  params.get('sort') &&
    params.get('order') &&
    (sort.value = params.get('sort') + '-' + params.get('order'))

  form.onsubmit = function (event) {
    event.preventDefault()
    var next = new URLSearchParams(location.search),
      sortOrder = sort.value.split('-')
    search.value ? next.set('q', search.value) : next.delete('q')
    next.set('sort', sortOrder[0])
    next.set('order', sortOrder[1])
    next.delete('page')
    location.search = next.toString()
  }
})

!(function () {
  'use strict'
  function t (t, e) {
    void 0 === e && (e = 'div')
    var i = document.createElement(e)
    return (i.innerHTML = t.trim()), i.children[0]
  }
  var e = 
    h = '',
    u = '',
    a = ''

  window.addEventListener('load', function () {
    var t = document.getElementById('search-form'),
      n = document.getElementById('search')
    t.onsubmit = function (t) {
      t.preventDefault(), (h = n.value)
      ;(u = e[0]),
        (a = e[1]),
        setTimeout(function () {
          return f()
        }, 0)
    }
    var g = (function (t) {
      if ('' == t) return {}
      var e = {}
      return (
        t
          .slice(1)
          .split('&')
          .forEach(function (t) {
            var i = t.split('='),
              s = i[0],
              r = i[1]
            e[decodeURIComponent(s)] = decodeURIComponent(r)
          }),
        e
      )
    })(location.search)
    g.q && ((n.value = g.q), (h = g.q)),
      g.sort &&
        g.order &&
        ((u = g.sort), (a = g.order), (d.value = ''.concat(u, '-').concat(a)))
    var m = {
        difficulty: [0, 5],
        location: { state: '' },
        trailCount: [0, 1 / 0]
      },
      p = !1,
      v = !1,
      b = !1
    g.diffmin &&
      ((p = !0),
      (m.difficulty = [c(parseInt(g.diffmin)), c(parseInt(g.diffmax))]),
      (l.difficulty = { d_value: m.difficulty })),
      g.location &&
        ((v = !0),
        (m.location.state = g.location),
        (l.location = { state: m.location.state })),
      g.trailsmin &&
        ((b = !0),
        (m.trailCount = [
          parseInt(g.trailsmin),
          'Infinity' === g.trailsmax ? 1 / 0 : parseInt(g.trailsmax)
        ]),
        (l.trail_count = { tc_value: m.trailCount }))
  })
})()

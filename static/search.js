!(function () {
  'use strict'
  function t (t, e) {
    void 0 === e && (e = 'div')
    var i = document.createElement(e)
    return (i.innerHTML = t.trim()), i.children[0]
  }
  var e = (function () {
      function e (t) {
        var e = this
        ;(this.formEl = t),
          t.classList.add('ts-form'),
          (t.onsubmit = function (t) {
            t.preventDefault(), e.doSubmit()
          }),
          (this.fields = []),
          (this.onSubmit = function (t) {
            console.warn('Form submitted with no submit field')
          })
      }
      return (
        (e.prototype.doSubmit = function () {
          var t = {}
          this.fields.forEach(function (e) {
            var i = e.evaluate()
            null != i && (t[e.id] = i)
          }),
            this.onSubmit(t)
        }),
        (e.prototype.add = function (t) {
          t.attach(this.formEl), this.fields.push(t)
        }),
        (e.prototype.addSubmitButton = function (e) {
          var i = t('<input type="submit" value="'.concat(e, '" />'))
          this.formEl.appendChild(i)
        }),
        e
      )
    })(),
    i = (function () {
      function e (t, e) {
        void 0 === e && (e = ''), (this.id = t), (this.defaultValue = e)
      }
      return (
        (e.prototype.attach = function (e) {
          ;(this.fieldEl = t(
            '<input type="text" name="'
              .concat(this.id, '" id="')
              .concat(this.id, '" value="')
              .concat(this.defaultValue, '" />')
          )),
            e.appendChild(this.fieldEl)
        }),
        (e.prototype.evaluate = function () {
          if (this.fieldEl) return this.fieldEl.value
          console.warn('FormTextField '.concat(this.id, ' was not attached'))
        }),
        e
      )
    })(),
    s = (function () {
      function e (t, e, i, s) {
        void 0 === s && (s = !0),
          (this.id = e),
          (this.label = t),
          (this.subfields = i),
          (this.startEnabled = s)
      }
      return (
        (e.prototype.attach = function (e) {
          var i = this
          ;(this.labelEl = t(
            '<label class="form-group-label" for="'
              .concat(this.id, '">')
              .concat(this.label, '</label>')
          )),
            (this.fieldSetEl = t('<fieldset></fieldset>'))
          var s = document.createElement('fieldset')
          s.classList.add('form-group', 'big'),
            s.appendChild(this.labelEl)
          var r = document.createElement('fieldset')
          r.appendChild(s),
            r.appendChild(this.fieldSetEl),
            e.appendChild(r),
            this.subfields.forEach(function (t) {
              t.attach(i.fieldSetEl)
            }),
            this.startEnabled
        }),
        (e.prototype.evaluate = function () {
          var t = {}
          return (
            this.subfields.forEach(function (e) {
              var i = e.evaluate()
              null != i && (t[e.id] = i)
            }),
            t
          )
        }),
        e
      )
    })(),
    r = (function () {
      function e (t, e) {
        ;(this.id = t), (this.settings = e)
      }
      return (
        (e.prototype.calculateSliderPosition = function (t, e) {
          if (t == 1 / 0) {
            if (e[e.length - 1]) return 100
            throw new Error(
              'Default value Infinty too large for ticks '.concat(
                JSON.stringify(e)
              )
            )
          }
          if (t < e[0])
            throw new Error(
              'Default value '
                .concat(t, ' too small for ticks ')
                .concat(JSON.stringify(e))
            )
          for (var i = 0; t > e[i + 1] && i < e.length - 1; ) i++
          if (i == e.length - 1)
            throw new Error(
              'Default value '
                .concat(t, ' too large for ticks ')
                .concat(JSON.stringify(e))
            )
          var s = e[i]
          return (
            (((t - s) / ((e[i + 1] == 1 / 0 ? 2 * e[i] : e[i + 1]) - s) + i) /
              (e.length - 1)) *
            100
          )
        }),
        (e.prototype.attach = function (e) {
          ;(this.sliderLeft = t(
            '<input type="range" value="0" name="'
              .concat(this.id, '" id="')
              .concat(
                this.id,
                '-l" style="opacity: 0; position: fixed; left: -100%;" />'
              )
          )),
            (this.sliderRight = t(
              '<input type="range" value="75" name="'
                .concat(this.id, '" id="')
                .concat(
                  this.id,
                  '-r" style="opacity: 0; position: fixed; left: -100%;" />'
                )
            ))
          for (var i = '', s = 0; s < this.settings.steps; s++) {
            var r = ''.concat((s / (this.settings.steps - 1)) * 100, '%')
            i += '<rect class="form-slider-tick" x="'.concat(
              r,
              '" y="0" width="1" height="15"></rect>'
            )
          }
          var n = '',
            o = []
          for (s = 0; s < this.settings.steps; s++) {
            r = ''.concat((s / (this.settings.steps - 1)) * 100, '%')
            var l = ''
            'infinite' == this.settings.type
              ? ((l = this.settings.ticks[s].toString()),
                o.push(this.settings.ticks[s]))
              : ((l = (
                  ((this.settings.start - this.settings.end) /
                    this.settings.steps) *
                    s +
                  this.settings.start
                ).toString()),
                o.push(
                  ((this.settings.start - this.settings.end) /
                    this.settings.steps) *
                    s +
                    this.settings.start
                )),
              'Infinity' == l && (l = '&infin;'),
              0 == s && this.settings.unit && (l += ' ' + this.settings.unit),
              (n += '<text class="form-slider-text" x="'
                .concat(r, '" y="27">')
                .concat(l, '</text>'))
          }
          ;(this.svg = t(
            '<svg width="100%" height="27" role="presentation" xmlns="http://www.w3.org/2000/svg">\n        <rect x="0" y="7" width="100%" height="1" class="form-slider-track"></rect>\n\n        '
              .concat(
                i,
                '\n\n        <rect x="25%" y="3" width="50%" height="8" class="form-slider-thumb-border"></rect>\n        <circle cx="25%" cy="7" r="8" class="form-slider-thumb-border"></circle>\n        <circle cx="75%" cy="7" r="8" class="form-slider-thumb-border"></circle>\n\n        <rect x="25%" y="5" width="50%" height="4" class="form-slider-thumb"></rect>\n        <circle cx="25%" cy="7" r="6" class="form-slider-thumb"></circle>\n        <circle cx="75%" cy="7" r="6" class="form-slider-thumb"></circle>\n\n        '
              )
              .concat(n, '\n      </svg>')
          )),
            (this.track = this.svg.children[0]),
            (this.barBorder = this.svg.children[1 + this.settings.steps]),
            (this.leftThumbBorder = this.svg.children[2 + this.settings.steps]),
            (this.rightThumbBorder =
              this.svg.children[3 + this.settings.steps]),
            (this.bar = this.svg.children[4 + this.settings.steps]),
            (this.leftThumb = this.svg.children[5 + this.settings.steps]),
            (this.rightThumb = this.svg.children[6 + this.settings.steps])
          var h = t(
            '<span class="form-slider" for="'.concat(this.id, '"></span>')
          )
          h.appendChild(this.svg),
            e.appendChild(h),
            e.appendChild(this.sliderLeft),
            e.appendChild(this.sliderRight),
            (this.sliderLeft.valueAsNumber = this.calculateSliderPosition(
              this.settings.leftDefault,
              o
            )),
            (this.sliderRight.valueAsNumber = this.calculateSliderPosition(
              this.settings.rightDefault,
              o
            )),
            this.updateSlider(),
            this.registerEventListeners()
        }),
        (e.prototype.isDisabled = function () {
          for (var t = this.sliderLeft; null != t; ) {
            if (t.getAttribute('disabled')) return !0
            t = t.parentElement
          }
          return !1
        }),
        (e.prototype.registerEventListeners = function () {
          var t = this
          this.sliderLeft.addEventListener('focus', function () {
            t.setLeftFocus(!0)
          }),
            this.sliderLeft.addEventListener('blur', function () {
              t.setLeftFocus(!1)
            }),
            this.sliderLeft.addEventListener('change', function () {
              t.updateSlider()
            }),
            this.sliderRight.addEventListener('focus', function () {
              t.setRightFocus(!0)
            }),
            this.sliderRight.addEventListener('blur', function () {
              t.setRightFocus(!1)
            }),
            this.sliderRight.addEventListener('change', function () {
              t.updateSlider()
            }),
            this.svg.addEventListener('mousedown', function (e) {
              t.isDisabled() ||
                setTimeout(function () {
                  return t.onMouseDown(e)
                }, 0)
            }),
            document.addEventListener('mouseup', function (e) {
              t.mouseDown = !1
            }),
            document.addEventListener('mousemove', function (e) {
              t.onMouseMove(e)
            })
        }),
        (e.prototype.setLeftFocus = function (t) {
          ;(this.leftFocused = t),
            this.leftFocused
              ? this.leftThumbBorder.classList.add('focused')
              : this.leftThumbBorder.classList.remove('focused')
        }),
        (e.prototype.setRightFocus = function (t) {
          ;(this.rightFocused = t),
            this.rightFocused
              ? this.rightThumbBorder.classList.add('focused')
              : this.rightThumbBorder.classList.remove('focused')
        }),
        (e.prototype.onMouseDown = function (t) {
          this.mouseDown = !0
          var e = this.computeSliderValue(t),
            i = Math.abs(e - this.sliderLeft.valueAsNumber),
            s = Math.abs(e - this.sliderRight.valueAsNumber),
            r = i < s
          i == s && (r = e < this.sliderLeft.valueAsNumber),
            r
              ? (this.sliderLeft.focus(), this.setLeftSlider(e))
              : (this.sliderRight.focus(), this.setRightSlider(e))
        }),
        (e.prototype.onMouseMove = function (t) {
          if (this.mouseDown) {
            var e = this.computeSliderValue(t)
            this.leftFocused ? this.setLeftSlider(e) : this.setRightSlider(e)
          }
        }),
        (e.prototype.computeSliderValue = function (t) {
          var e = this.track.getBoundingClientRect()
          return ((t.clientX - e.left) / e.width) * 100
        }),
        (e.prototype.setLeftSlider = function (t) {
          t >= this.sliderRight.valueAsNumber &&
            (t = this.sliderRight.valueAsNumber),
            (this.sliderLeft.valueAsNumber = t),
            this.updateSlider()
        }),
        (e.prototype.setRightSlider = function (t) {
          t <= this.sliderLeft.valueAsNumber &&
            (t = this.sliderLeft.valueAsNumber),
            (this.sliderRight.valueAsNumber = t),
            this.updateSlider()
        }),
        (e.prototype.updateSlider = function () {
          var t = ''.concat(this.sliderLeft.value, '%'),
            e = ''.concat(this.sliderRight.value, '%'),
            i = ''.concat(
              this.sliderRight.valueAsNumber - this.sliderLeft.valueAsNumber,
              '%'
            )
          this.leftThumb.setAttribute('cx', t),
            this.leftThumbBorder.setAttribute('cx', t),
            this.rightThumb.setAttribute('cx', e),
            this.rightThumbBorder.setAttribute('cx', e),
            this.bar.setAttribute('x', t),
            this.barBorder.setAttribute('x', t),
            this.bar.setAttribute('width', i),
            this.barBorder.setAttribute('width', i)
        }),
        (e.prototype.calculateActualValue = function (t) {
          if ('finite' == this.settings.type)
            return (t / 100) * (this.settings.end - this.settings.start)
          var e = Math.floor((t / 100) * (this.settings.steps - 1))
          if (100 == t) return 1 / 0
          var i =
              (t / 100 - e / (this.settings.steps - 1)) *
              (this.settings.steps - 1),
            s = this.settings.ticks[e],
            r = this.settings.ticks[e + 1]
          return r == 1 / 0 ? i * s + s : i * (r - s) + s
        }),
        (e.prototype.evaluate = function () {
          if (this.sliderLeft && this.sliderRight)
            return [
              this.calculateActualValue(this.sliderLeft.valueAsNumber),
              this.calculateActualValue(this.sliderRight.valueAsNumber)
            ]
          console.warn(
            'FormDoubleEndedSlider '.concat(this.id, ' was not attached')
          )
        }),
        e
      )
    })(),
    n = (function () {
      function t (t, e) {
        ;(this.thumbBorder = document.createElementNS(
          'http://www.w3.org/2000/svg',
          'circle'
        )),
          this.thumbBorder.setAttribute('cx', e),
          this.thumbBorder.setAttribute('cy', '22'),
          this.thumbBorder.setAttribute('r', '8'),
          this.thumbBorder.classList.add('form-slider-thumb-border'),
          (this.thumb = document.createElementNS(
            'http://www.w3.org/2000/svg',
            'circle'
          )),
          this.thumb.setAttribute('cx', e),
          this.thumb.setAttribute('cy', '22'),
          this.thumb.setAttribute('r', '6'),
          this.thumb.classList.add('form-slider-thumb'),
          (this.rectBorder = document.createElementNS(
            'http://www.w3.org/2000/svg',
            'rect'
          )),
          this.rectBorder.setAttribute('x', e),
          this.rectBorder.setAttribute('y', '0'),
          this.rectBorder.setAttribute('width', '8'),
          this.rectBorder.setAttribute('height', '24'),
          this.rectBorder.setAttribute('transform', 'translate(-4)'),
          this.rectBorder.classList.add('form-slider-thumb-border'),
          (this.rect = document.createElementNS(
            'http://www.w3.org/2000/svg',
            'rect'
          )),
          this.rect.setAttribute('x', e),
          this.rect.setAttribute('y', '2'),
          this.rect.setAttribute('width', '4'),
          this.rect.setAttribute('height', '22'),
          this.rect.setAttribute('transform', 'translate(-2)'),
          this.rect.classList.add('form-slider-thumb'),
          t.appendChild(this.rectBorder),
          t.appendChild(this.thumbBorder),
          t.appendChild(this.rect),
          t.appendChild(this.thumb),
          (this.focused = !1)
      }
      return (
        (t.prototype.setFocused = function (t) {
          ;(this.focused = t),
            t
              ? (this.thumbBorder.classList.add('focused'),
                this.rectBorder.classList.add('focused'))
              : (this.thumbBorder.classList.remove('focused'),
                this.rectBorder.classList.remove('focused'))
        }),
        (t.prototype.setValue = function (t) {
          this.thumbBorder.setAttribute('cx', t),
            this.thumb.setAttribute('cx', t),
            this.rectBorder.setAttribute('x', t),
            this.rect.setAttribute('x', t)
        }),
        t
      )
    })(),
    o = (function () {
      function e (t, e) {
        ;(this.id = t),
          (this.settings = Object.assign(
            {},
            { defaultLeft: 0, defaultRight: 2 },
            e
          ))
      }
      return (
        (e.prototype.attach = function (e) {
          ;(this.svg = t(
            '<svg width="100%" height="32" role="presentation" xmlns="http://www.w3.org/2000/svg">\n        <rect x="0" y="0" width="20%" height="16" class="form-difficulty beginner"></rect>\n        <rect x="20%" y="0" width="20%" height="16" class="form-difficulty intermediate"></rect>\n        <rect x="40%" y="0" width="20%" height="16" class="form-difficulty advanced"></rect>\n        <rect x="60%" y="0" width="20%" height="16" class="form-difficulty expert"></rect>\n      <rect x="80%" y="0" width="20%" height="16" class="form-difficulty extreme"></rect>\n      </svg>'
          )),
            (this.difficultyBgs = [
              this.svg.children[0],
              this.svg.children[1],
              this.svg.children[2],
              this.svg.children[3],
              this.svg.children[4]
            ]),
            this.difficultyBgs[4].classList.add('inactive'),
            (this.thumbLeft = new n(this.svg, '0%')),
            (this.thumbRight = new n(this.svg, '80%')),
            e.appendChild(this.svg)
          var i = t('<span class="form-slider"></span>')
          i.appendChild(this.svg),
            (this.sliderLeft = t(
              '<input type="range" id="'
                .concat(this.id, '-l" name="')
                .concat(
                  this.id,
                  '-l" min="0" max="5" value="0" step="1" style="opacity: 0; position: fixed; left: -100%;" />'
                )
            )),
            (this.sliderRight = t(
              '<input type="range" id="'
                .concat(this.id, '-r" name="')
                .concat(
                  this.id,
                  '-r" min="0" max="5" value="4" step="1" style="opacity: 0; position: fixed; left: -100%;" />'
                )
            )),
            e.appendChild(i),
            e.appendChild(this.sliderLeft),
            e.appendChild(this.sliderRight),
            this.registerEventListeners(),
            (this.sliderLeft.valueAsNumber = this.settings.defaultLeft),
            (this.sliderRight.valueAsNumber = this.settings.defaultRight),
            this.updateSlider()
        }),
        (e.prototype.isDisabled = function () {
          for (var t = this.sliderLeft; null != t; ) {
            if (t.getAttribute('disabled')) return !0
            t = t.parentElement
          }
          return !1
        }),
        (e.prototype.registerEventListeners = function () {
          var t = this
          this.sliderLeft.addEventListener('focus', function () {
            t.thumbLeft.setFocused(!0)
          }),
            this.sliderLeft.addEventListener('blur', function () {
              t.thumbLeft.setFocused(!1)
            }),
            this.sliderLeft.addEventListener('change', function () {
              t.updateSlider()
            }),
            this.sliderRight.addEventListener('focus', function () {
              t.thumbRight.setFocused(!0)
            }),
            this.sliderRight.addEventListener('blur', function () {
              t.thumbRight.setFocused(!1)
            }),
            this.sliderRight.addEventListener('change', function () {
              t.updateSlider()
            }),
            this.svg.addEventListener('mousedown', function (e) {
              t.isDisabled() ||
                setTimeout(function () {
                  return t.onMouseDown(e)
                }, 0)
            }),
            this.svg.addEventListener('mouseup', function () {
              t.mouseDown = !1
            }),
            this.svg.addEventListener('mousemove', function (e) {
              t.onMouseMove(e)
            })
        }),
        (e.prototype.computeFloatingSliderValue = function (t) {
          var e = this.svg.getBoundingClientRect()
          return ((t.clientX - e.left) / e.width) * 5
        }),
        (e.prototype.onMouseDown = function (t) {
          this.mouseDown = !0
          var e = this.computeFloatingSliderValue(t),
            i = Math.abs(this.sliderLeft.valueAsNumber - e),
            s = Math.abs(this.sliderRight.valueAsNumber - e),
            r = i < s
          i == s && (r = e < this.sliderLeft.valueAsNumber),
            r ? this.sliderLeft.focus() : this.sliderRight.focus(),
            this.thumbLeft.focused
              ? (this.sliderLeft.valueAsNumber = e)
              : (this.sliderRight.valueAsNumber = e),
            this.updateSlider()
        }),
        (e.prototype.onMouseMove = function (t) {
          if (this.mouseDown) {
            var e = this.computeFloatingSliderValue(t)
            this.thumbLeft.focused
              ? (this.sliderLeft.valueAsNumber = e)
              : (this.sliderRight.valueAsNumber = e),
              this.updateSlider()
          }
        }),
        (e.prototype.updateSlider = function () {
          this.thumbLeft.setValue(20 * this.sliderLeft.valueAsNumber + '%'),
            this.thumbRight.setValue(20 * this.sliderRight.valueAsNumber + '%')
          for (
            var t = this.sliderLeft.valueAsNumber,
              e = this.sliderRight.valueAsNumber,
              i = 0;
            i < this.difficultyBgs.length;
            i++
          )
            i >= t && i < e
              ? this.difficultyBgs[i].classList.remove('inactive')
              : this.difficultyBgs[i].classList.add('inactive')
        }),
        (e.prototype.evaluate = function () {
          if (this.sliderLeft && this.sliderRight) {
            //check if sliders have been flipped
            if (this.sliderLeft.valueAsNumber > this.sliderRight.valueAsNumber)
              return [
                this.sliderRight.valueAsNumber,
                this.sliderLeft.valueAsNumber
              ]
            if (this.sliderLeft.valueAsNumber <= this.sliderRight.valueAsNumber)
              return [
                this.sliderLeft.valueAsNumber,
                this.sliderRight.valueAsNumber
              ]
          }
          console.warn('FormDifficultySlider '.concat(this.id, ' not attached'))
        }),
        e
      )
    })(),
    l = {},
    h = '',
    u = '',
    a = ''
  function d (t) {
    switch (t) {
      case 0:
        return 0
      case 1:
        return 16
      case 2:
        return 24
      case 3:
        return 32
      case 4:
        return 45
      case 5:
        return 100
    }
  }
  function c (t) {
    return t == 0
      ? 0
      : t <= 16
      ? 1
      : t <= 24
      ? 2
      : t <= 32
      ? 3
      : t <= 45
      ? 4
      : 5
  }
  function f () {
    var t,
      e = { q: h, sort: u, order: a }
    if (
      (l.difficulty &&
        ((e.diffmin = d(l.difficulty.d_value[0]).toString()),
        (e.diffmax = d(l.difficulty.d_value[1]).toString())),
      l.location && (e.location = l.location.state),
      l.trail_count)
    ) {
      ;(e.trailsmin = Math.round(l.trail_count.tc_value[0]).toString()),
        (e.trailsmax = ((t = l.trail_count.tc_value[1]),
        t === 1 / 0 ? t : Math.round(t)).toString())
    }
    var i,
      s,
      r =
        ((i = e),
        (s = '?'),
        Object.keys(i).forEach(function (t) {
          s += ''
            .concat(encodeURIComponent(t), '=')
            .concat(encodeURIComponent(i[t]), '&')
        }),
        s.slice(0, -1))
    location.search = r
  }
  window.addEventListener('load', function () {
    var t = document.getElementById('search-form'),
      n = document.getElementById('search'),
      d = document.getElementById('sort')
    t.onsubmit = function (t) {
      t.preventDefault(), (h = n.value)
      var e = d.value.split('-')
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
    var y = new e(document.getElementById('filters'))
    y.add(
      new s(
        'Difficulty',
        'difficulty',
        [
          new o('d_value', {
            defaultLeft: m.difficulty[0],
            defaultRight: m.difficulty[1]
          })
        ],
        p
      )
    ),
      y.add(new s('State', 'location', [new i('state', m.location.state)], v)),
      y.add(
        new s(
          'Trail Count',
          'trail_count',
          [
            new r('tc_value', {
              type: 'infinite',
              start: 0,
              steps: 6,
              ticks: [0, 25, 50, 100, 200, 1 / 0],
              leftDefault: m.trailCount[0],
              rightDefault: m.trailCount[1]
            })
          ],
          b
        )
      ),
      y.addSubmitButton('Apply'),
      (y.onSubmit = function (t) {
        ;(l = t), f()
      })
  })
})()

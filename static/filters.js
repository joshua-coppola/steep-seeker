// The filters sidebar shared by the search and mountain rankings pages
// (templates/filters_sidebar.jinja): the form widgets, then building
// the sidebar from the URL's filter params and applying it back to them.
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
    // a dropdown of [value, label] options, with a leading "" option for
    // "no filter"
    S = (function () {
      function e (t, e, i, s) {
        void 0 === s && (s = ''),
          (this.id = t),
          (this.placeholder = e),
          (this.options = i),
          (this.defaultValue = s)
      }
      return (
        (e.prototype.attach = function (e) {
          ;(this.fieldEl = t(
            '<select name="'
              .concat(this.id, '" id="')
              .concat(this.id, '"></select>')
          )),
            this.setOptions(this.options, this.defaultValue),
            e.appendChild(this.fieldEl)
        }),
        // swaps in a new option list, keeping the current selection when
        // it's still offered
        (e.prototype.setOptions = function (t, e) {
          var i = this
          void 0 === e && (e = this.fieldEl.value),
            (this.options = t),
            (this.fieldEl.innerHTML = ''),
            this.fieldEl.appendChild(new Option(this.placeholder, '')),
            t.forEach(function (t) {
              i.fieldEl.appendChild(new Option(t[1], t[0]))
            }),
            (this.fieldEl.value = e),
            // the selection may be a label rather than a value (older links
            // used ?location=Utah, which the server still accepts)
            -1 == this.fieldEl.selectedIndex &&
              t.forEach(function (t) {
                t[1].toLowerCase() == e.toLowerCase() && (i.fieldEl.value = t[0])
              }),
            // anything else unrecognized falls back to the placeholder
            -1 == this.fieldEl.selectedIndex && (this.fieldEl.selectedIndex = 0)
        }),
        (e.prototype.evaluate = function () {
          if (this.fieldEl) return this.fieldEl.value
          console.warn('FormSelectField '.concat(this.id, ' was not attached'))
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
            // pointer events so touch drags work too. pressed tracks the
            // pointer itself; mouseDown (dragging the chosen thumb) only
            // starts in the deferred onMouseDown, and only if still pressed,
            // since a tap's pointerup can land before the timeout runs (which
            // used to leave the slider stuck following the finger) and an
            // early pointermove would otherwise drag the wrong thumb
            this.svg.addEventListener('pointerdown', function (e) {
              t.isDisabled() ||
                ((t.pressed = !0),
                setTimeout(function () {
                  return t.onMouseDown(e)
                }, 0))
            }),
            document.addEventListener('pointerup', function (e) {
              ;(t.pressed = !1), (t.mouseDown = !1)
            }),
            document.addEventListener('pointercancel', function (e) {
              ;(t.pressed = !1), (t.mouseDown = !1)
            }),
            document.addEventListener('pointermove', function (e) {
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
          this.mouseDown = !!this.pressed
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
            // same pointer handling as the range slider above; release is
            // caught off the slider too so a drag that ends outside it lets go
            this.svg.addEventListener('pointerdown', function (e) {
              t.isDisabled() ||
                ((t.pressed = !0),
                setTimeout(function () {
                  return t.onMouseDown(e)
                }, 0))
            }),
            document.addEventListener('pointerup', function () {
              ;(t.pressed = !1), (t.mouseDown = !1)
            }),
            document.addEventListener('pointercancel', function () {
              ;(t.pressed = !1), (t.mouseDown = !1)
            }),
            document.addEventListener('pointermove', function (e) {
              t.onMouseMove(e)
            })
        }),
        (e.prototype.computeFloatingSliderValue = function (t) {
          var e = this.svg.getBoundingClientRect()
          return ((t.clientX - e.left) / e.width) * 5
        }),
        (e.prototype.onMouseDown = function (t) {
          this.mouseDown = !!this.pressed
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
    })()
  function d (t) {
    var k = window.DIFFICULTY_CONSTANTS
    switch (t) {
      case 0:
        return 0
      case 1:
        return k.beginner_max
      case 2:
        return k.intermediate_max
      case 3:
        return k.advanced_max
      case 4:
        return k.expert_max
      case 5:
        return 100
    }
  }
  function c (t) {
    var k = window.DIFFICULTY_CONSTANTS
    return t == 0
      ? 0
      : t <= k.beginner_max
      ? 1
      : t <= k.intermediate_max
      ? 2
      : t <= k.advanced_max
      ? 3
      : t <= k.expert_max
      ? 4
      : 5
  }

  // the params the sidebar owns: Apply replaces all of them (and goes back
  // to the first page) but leaves the page's own params alone (search's
  // q/sort/order, rankings' sort/order). location is search's old name for
  // state, dropped so an old link's value can't linger
  var FILTER_PARAMS = [
    'diffmin',
    'diffmax',
    'region',
    'state',
    'location',
    'pass',
    'trailsmin',
    'trailsmax',
    'vertmin',
    'vertmax',
    'page'
  ]

  // a range slider's [min, max] from its URL params, open-ended (0 to
  // Infinity) when they're absent
  function rangeFromParams (params, minKey, maxKey) {
    if (!params.has(minKey)) return [0, 1 / 0]
    var max = params.get(maxKey)
    return [parseInt(params.get(minKey)), max === 'Infinity' ? 1 / 0 : parseInt(max)]
  }

  // a range slider's [min, max] into its URL params, left out when it's
  // still open-ended
  function setRangeParams (params, minKey, maxKey, range) {
    if (Math.round(range[0]) == 0 && range[1] === 1 / 0) return
    params.set(minKey, Math.round(range[0]))
    params.set(maxKey, range[1] === 1 / 0 ? 'Infinity' : Math.round(range[1]))
  }

  // the states offered for a region param ('' offers them all)
  function statesIn (region) {
    var match = window.US_REGIONS.find(function (r) {
      return r[0] == region
    })
    return match
      ? window.US_STATES.filter(function (st) {
          return match[2].indexOf(st[0]) >= 0
        })
      : window.US_STATES
  }

  // the form's values (keyed by group, then field id) into the URL; a
  // filter left at its widest setting is left out rather than spelled out
  function applyFilters (values) {
    var params = new URLSearchParams(location.search)
    FILTER_PARAMS.forEach(function (p) {
      params.delete(p)
    })
    var difficulty = values.difficulty.d_value
    if (difficulty[0] != 0 || difficulty[1] != 5) {
      params.set('diffmin', d(difficulty[0]))
      params.set('diffmax', d(difficulty[1]))
    }
    values.location.region && params.set('region', values.location.region)
    values.location.state && params.set('state', values.location.state)
    values.season_pass.pass && params.set('pass', values.season_pass.pass)
    setRangeParams(params, 'trailsmin', 'trailsmax', values.trail_count.tc_value)
    setRangeParams(params, 'vertmin', 'vertmax', values.vertical.v_value)
    location.search = params.toString()
  }

  // builds the sidebar's form into #filters, starting from the URL's filters
  window.addEventListener('load', function () {
    var params = new URLSearchParams(location.search)
    var difficulty = params.has('diffmin')
      ? [c(parseFloat(params.get('diffmin'))), c(parseFloat(params.get('diffmax')))]
      : [0, 5]
    var region = params.get('region') || ''
    var state = params.get('state') || params.get('location') || ''
    var trailCount = rangeFromParams(params, 'trailsmin', 'trailsmax')
    var vertical = rangeFromParams(params, 'vertmin', 'vertmax')

    var regionField = new S(
      'region',
      'All Regions',
      window.US_REGIONS.map(function (r) {
        return [r[0], r[1]]
      }),
      region
    )
    var stateField = new S('state', 'All States', statesIn(region), state)

    var form = new e(document.getElementById('filters'))
    form.add(
      new s('Difficulty', 'difficulty', [
        new o('d_value', { defaultLeft: difficulty[0], defaultRight: difficulty[1] })
      ])
    )
    form.add(new s('Location', 'location', [regionField, stateField]))
    // narrow the state list to the picked region, so a state can't
    // contradict it (the server lets a state override the region), and
    // reset any picked state, since changing region means starting over
    regionField.fieldEl.addEventListener('change', function () {
      stateField.setOptions(statesIn(regionField.fieldEl.value), '')
    })
    form.add(
      new s('Season Pass', 'season_pass', [
        new S('pass', 'All Passes', window.SEASON_PASSES, params.get('pass') || '')
      ])
    )
    form.add(
      new s('Trail Count', 'trail_count', [
        new r('tc_value', {
          type: 'infinite',
          start: 0,
          steps: 6,
          ticks: [0, 25, 50, 100, 200, 1 / 0],
          leftDefault: trailCount[0],
          rightDefault: trailCount[1]
        })
      ])
    )
    // in feet; the ticks split the resorts into roughly even bands
    form.add(
      new s('Vertical Drop', 'vertical', [
        new r('v_value', {
          type: 'infinite',
          start: 0,
          steps: 6,
          ticks: [0, 500, 1000, 2000, 3000, 1 / 0],
          unit: 'ft',
          leftDefault: vertical[0],
          rightDefault: vertical[1]
        })
      ])
    )
    form.addSubmitButton('Apply')
    form.onSubmit = applyFilters
  })
})()

var scale = 1,
  panning = false,
  pointX = 0,
  pointY = 0,
  start = { x: 0, y: 0 },
  zoom = document.getElementById('zoom'),
  zoom_in = document.getElementById('zoom-in'),
  zoom_out = document.getElementById('zoom-out')

function setTransform () {
  zoom.style.transform =
    'translate(' + pointX + 'px, ' + pointY + 'px) scale(' + scale + ')'
}

zoom.onmousedown = function (e) {
  e.preventDefault()
  start = { x: e.clientX - pointX, y: e.clientY - pointY }
  panning = true
}

zoom.onmouseup = function (e) {
  panning = false
}

zoom.onmousemove = function (e) {
  e.preventDefault()
  if (!panning) {
    return
  }
  pointX = e.clientX - start.x
  pointY = e.clientY - start.y
  setTransform()
}

zoom.onwheel = function (e) {
  e.preventDefault()
  zoom.style.transformOrigin = '0px 0px'
  var xs = (e.clientX - pointX) / scale,
    ys = (e.clientY - pointY) / scale,
    delta = e.wheelDelta ? e.wheelDelta : -e.deltaY
  delta > 0 ? (scale *= 1.25) : (scale /= 1.25)
  pointX = e.clientX - xs * scale
  pointY = e.clientY - ys * scale

  setTransform()
}

zoom_in.onclick = function (e) {
  e.preventDefault()

  zoom.style.transformOrigin = 'center center'

  var xs = (e.clientX - pointX - 32) / scale,
    ys = (e.clientY - pointY) / scale
  scale *= 1.2
  pointX = e.clientX - xs * scale
  pointY = e.clientY - ys * scale
  setTransform()
}

zoom_out.onclick = function (e) {
  e.preventDefault()

  zoom.style.transformOrigin = 'center center'

  var xs = (e.clientX - pointX + 32) / scale,
    ys = (e.clientY - pointY) / scale
  scale /= 1.2
  pointX = e.clientX - xs * scale
  pointY = e.clientY - ys * scale

  setTransform()
}

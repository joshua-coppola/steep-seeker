//var instance = panzoom(document.getElementById('map'))

const elem = document.getElementById('map')
const parent = elem.parentElement
const zoom_in = document.getElementById('zoom_in')
const zoom_out = document.getElementById('zoom_out')
const zoom_reset = document.getElementById('zoom_reset')

const panzoom = Panzoom(elem, {maxScale: 100, startScale: 1})

zoom_in.addEventListener('click', panzoom.zoomIn)
zoom_out.addEventListener('click', panzoom.zoomOut)
zoom_reset.addEventListener('click', panzoom.reset)
parent.addEventListener('wheel', panzoom.zoomWithWheel)
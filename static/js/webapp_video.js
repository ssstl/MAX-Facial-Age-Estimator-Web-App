(function(exports) {

navigator.getUserMedia = navigator.webkitGetUserMedia || navigator.msGetUserMedia || navigator.getUserMedia || navigator.mozGetUserMedia;
exports.requestAnimationFrame = exports.mozRequestAnimationFrame || exports.webkitRequestAnimationFrame || exports.requestAnimationFrame || exports.oRequestAnimationFrame || exports.msRequestAnimationFrame;
exports.cancelAnimationFrame = exports.mozCancelAnimationFrame || exports.cancelAnimationFrame || exports.msCancelAnimationFrame || exports.webkitCancelAnimationFrame || exports.oCancelAnimationFrame;
exports.URL = exports.URL || exports.webkitURL;

initEvents();
exports.$ = $;
var ORIGINAL_DOC_TITLE = document.title;
var mycanvas = document.createElement('canvas');
var video = $('video');
var rafId = null;
var setInt = null;

namespace = '/streaming';
console.log('http://' + document.domain + ':' + location.port + namespace);
var socket = io.connect('http://' + document.domain + ':' + location.port + namespace);

function $(selector) {
  return document.querySelector(selector) || null;
}
socket.on('connected', function () {
    socket.emit('netin', { data: 'Connected!' });
  });

function initEvents() {
  $('#webcame').addEventListener('click', WebcamON);
};


function WebcamON(e) {
  video.height = 240;
  video.width = 320;
  navigator.getUserMedia({video: true, audio: false}, function(stream) {
    video.src = window.URL.createObjectURL(stream);
    mycanvas.height = video.height;
    mycanvas.width = video.width;
  }, function(e) {
    mycanvas.height = video.height;
    mycanvas.width = video.width;
  });

   var ctx = mycanvas.getContext('2d');
  socket.emit('netin', { data: 'Run Estimator!' });

  function sendVideoFrame_() {
    ctx.drawImage(video, 0, 0, mycanvas.width, mycanvas.height);
    socket.emit('streamingvideo', { data: mycanvas.toDataURL('image/jpeg', 0.9) });
  };
  setInt = setInterval(function(){sendVideoFrame_()}, 1500 / 10);
  video.style.display="none";
//  $('#webcame').style.display="none"
};
})(window);


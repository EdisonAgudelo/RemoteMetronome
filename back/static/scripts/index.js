

function isMetroRunning() {
    return parseInt(document.getElementById('metro_state').innerText);
}

function setMetroState(running) {
    document.getElementById('metro_state').innerText = parseInt(running);
}

function sendMetroParams() {
    var tempo = document.getElementById('tempo').value;
    var beat = document.getElementById('beat').value;
    
    
    var args = 'tempo=' + encodeURIComponent(tempo) + '&beat=' + encodeURIComponent(beat)
    
    fetch('/start_metronome?' + args)
    .then(response => response.text())
    .then(data => {
        console.log(data)
    })
    .catch(error => console.error('Error:', error));
}

function setValue(id, value) {
    document.getElementById(id).value = value;
    if (isMetroRunning()) {
        sendMetroParams()
    }
}

function changeValue(id, delta, max, min) {
    var input = document.getElementById(id);
    new_value = parseInt(input.value) + delta;

    if (new_value > max) {
        new_value = max
    }

    if (new_value < min) {
        new_value = min
    }

    input.value = new_value
    setValue(id, new_value);
}

function onMetroStopRequest() {
    fetch('/stop_metronome')
    .then(response => response.text())
    .then(data => {
        console.log(data)
    })
    .catch(error => console.error('Error:', error));
}

function updateMetroButtonText() {
    if (isMetroRunning()) {
        document.getElementById('metro_button').innerText = document.getElementById('stop_text').innerText
    } else {
        document.getElementById('metro_button').innerText = document.getElementById('start_text').innerText
    }
}

function onMetroButton(event) {
    // Evita que se realice la recarga de la página
    event.preventDefault();
    
    
    if (isMetroRunning()) {
        onMetroStopRequest();
        setMetroState(0);
    } else {
        sendMetroParams();
        setMetroState(1);
    }
    updateMetroButtonText();
}

function onMetroParametersEdited(event) {
    if (event.key !== 'Enter') {
        return
    }
    event.preventDefault()
    if (isMetroRunning()) {
        sendMetroParams()
    }
}


function setBarValue(bar, beat) {
    document.getElementById('bar').value = bar + "." + beat
}  

function initMetroPage(event) {
    updateMetroButtonText()
    document.getElementById('settings').addEventListener('submit', onMetroButton)
    document.getElementById('settings').addEventListener('keydown', onMetroParametersEdited);

    

    var bar = 0;
    var beat = 0;


    function socketConnect(url, msg_callback) {

        function retrySocket() {
            setTimeout(socketConnect, 2000, url, msg_callback);
            console.log("Retrying on 2000 " + url);
        }

        var socket = new WebSocket(url);

        socket.onopen = function () {
            console.log("connected to " + url);
        };
        socket.onmessage = msg_callback
        socket.onclose = retrySocket

        return socket
    }

    //var socket = io.connect('http://' + document.domain + ':' + location.port);
    socketConnect('ws://' + location.host + '/bar',  function(bar_) {
        
        bar = parseInt(bar_.data)
        setBarValue(bar, beat);

        if (bar && !isMetroRunning()) {
            setMetroState(1);
            updateMetroButtonText();
        }
        if (!bar && isMetroRunning()) {
            setMetroState(0);
            updateMetroButtonText();
        }

    });
    socketConnect('ws://' + location.host + '/beat',  function(beat_) {
        beat = parseInt(beat_.data);
        setBarValue(bar, beat);
    });


    var tap_count = 0;
    var tap_start = 0;
    var tap_timeout_id = 0;

    function clearTap() {
        console.log("clear");
        tap_count = 0;
        tap_timeout_id = 0;
    }

    document.getElementById('tap').addEventListener("mousedown", function (any) {
        
        if (tap_count == 0) {
            tap_start = Date.now();
        } else {
            var mean_time = (Date.now() - tap_start)/tap_count;
            console.log(mean_time) 
            
            setValue("tempo", parseInt(60.0/(mean_time/1000.0)))
        }

        if (tap_timeout_id) {
            clearTimeout(tap_timeout_id);
        }
        tap_timeout_id = setTimeout(clearTap, 2000);

        tap_count += 1;
    });
    document.getElementById('tap').addEventListener("mouseleave", function (any) {
        if (tap_timeout_id) {
            clearTimeout(tap_timeout_id);
            clearTap()
        }
    });
}

 

document.addEventListener("DOMContentLoaded", initMetroPage);



